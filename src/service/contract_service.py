# TODO Реализовать
import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from connection_module import SignalConnector
from query_and_statement.file_store_qas_manager import FileStoreQueryAndStatementManager
from src.query_and_statement.application.application_qas_manager import ApplicationQueryAndStatementManager
from src.query_and_statement.counterparty.counterparty_qas_manager import CounterpartyQueryAndStatementManager
from src.schemas.contract_schema import Contract, FiltersContracts, OrdersContracts
from src.service.chat_service import ChatService
from src.query_and_statement.contract_qas_manager import ContractQueryAndStatementManager
from src.service.file_store_service import FileStoreService
from src.utils.reference_mapping_data.user.mapping import PRIVILEGE_MAPPING


class ContractService:
    @staticmethod
    async def create_contract(
        session: AsyncSession,
        
        requester_user_uuid: str, requester_user_privilege: int,
        
        file_uuid: str,
        type: str,
        
        start_date: Optional[str] = None,
        expiration_date: Optional[str] = None,
    ) -> Tuple[str, Optional[str], str, str, str]:
        start_date_obj: datetime.date = datetime.datetime.strptime(start_date, "%d.%m.%Y").date() if start_date else None
        expiration_date_obj: datetime.date = datetime.datetime.strptime(expiration_date, "%d.%m.%Y").date() if expiration_date else None
        if start_date_obj and expiration_date_obj:
            if start_date_obj > expiration_date_obj:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Дата начала действия Договора не может превышать дату окончания его действия!")
        
        if requester_user_privilege != PRIVILEGE_MAPPING["Admin"]:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="У Вас недостаточно прав для создания карточки Договора!")
        
        if not all([file_uuid, type]):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Для создания карточки Договора нужно указать как UUID-Документа, так и тип Договора!")
        
        data_from_db_about_file_response: Dict[str, Any] = await FileStoreService.get_doc_info_from_db(
            session=session,
            
            requester_user_uuid=requester_user_uuid,
            requester_user_privilege=requester_user_privilege,
            file_uuids=[file_uuid],
            visible=True,
        )
        data_from_db_about_file: Dict[int, Any] = data_from_db_about_file_response["data"][list(data_from_db_about_file_response["data"])[0]]
        
        owner_user_id: int = data_from_db_about_file.get("owner_user_id")
        owner_user_uuid: str = data_from_db_about_file.get("owner_user_uuid")
        directory_id: int = data_from_db_about_file.get("directory_id")
        name: str = data_from_db_about_file.get("name")
        
        if owner_user_id is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Не удалось извлечь ID-владельца Документа из БД!")
        
        counterparty_id, counterparty_uuid = await CounterpartyQueryAndStatementManager.get_counterparty_identifiers_by_directory_identifier(
            session=session,
            
            directory_id=directory_id,
        )
        
        if counterparty_id is None:
            application_id, application_uuid = await ApplicationQueryAndStatementManager.get_application_identifiers_by_directory_identifier(
                session=session,
                
                directory_id=directory_id,
            )
            
            counterparty_id, counterparty_uuid = await CounterpartyQueryAndStatementManager.get_counterparty_identifiers_by_application_identifier(
                session=session,
                
                application_id=application_id,
                application_uuid=application_uuid,
            )
        
        else:
            application_id, application_uuid = (None, None)
        
        if not counterparty_id or not counterparty_uuid:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f'При поиске принадлежности Документа, не нашлась карточка Контрагента (ID-Директории - "{directory_id}")!')
        
        new_contract_uuid_coro = await SignalConnector.generate_identifiers(target="Договор", count=1)
        new_contract_uuid = new_contract_uuid_coro[0]
        
        await ContractQueryAndStatementManager.create_contract(
            session=session,
            
            new_uuid=new_contract_uuid,
            name=name,
            type=type,
            user_id=owner_user_id,
            user_uuid=owner_user_uuid,
            counterparty_id=counterparty_id,
            counterparty_uuid=counterparty_uuid,
            application_id=application_id,
            application_uuid=application_uuid,
            file_uuid=file_uuid,
            start_date=start_date,
            expiration_date=expiration_date,
        )
        
        await ChatService.create_chat(
            session=session,
            
            chat_subject="Договор",
            subject_uuid=new_contract_uuid,
        )
        
        return counterparty_uuid, application_uuid, new_contract_uuid, owner_user_uuid, Path(name if name else "-").stem
    
    @staticmethod
    async def get_contracts(
        session: AsyncSession,
        
        requester_user_uuid: str,
        requester_user_privilege: int,
        
        user_uuid: Optional[str],
        
        page: Optional[int] = None,
        page_size: Optional[int] = None,
        
        filter: Optional[FiltersContracts] = None,
        order: Optional[OrdersContracts] = None,
    ) -> Dict[str, List[Optional[Contract]]]:
        if page or page_size:
            if (isinstance(page, int) and page <= 0) or (isinstance(page_size, int) and page_size <= 0):
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Не корректное разделение на страницы, запрошенных данных!")
        
        if requester_user_privilege != PRIVILEGE_MAPPING["Admin"]:
            if not user_uuid:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Вы не можете просмотреть все Договоры - всех Пользователей!")
            if user_uuid != requester_user_uuid:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Вы не можете просмотреть Договоры других Пользователей!")
        
        contracts: Dict[str, List[Optional[Contract]]] = await ContractQueryAndStatementManager.get_contracts(
            session=session,
            user_uuid=user_uuid,
            page=page,
            page_size=page_size,
            filter=filter,
            order=order,
        )
        
        return contracts
    
    @staticmethod
    async def update_contract_date_range(
        session: AsyncSession,
        
        requester_user_uuid: str,
        requester_user_privilege: int,
        
        contract_uuid: str,
        new_start_date: Optional[str] = "~",
        new_expiration_date: Optional[str] = "~",
    ) -> None:
        if requester_user_privilege != PRIVILEGE_MAPPING["Admin"]:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="У Вас недостаточно прав для изменения временного диапазона действия Договора!")
        
        contract_check_access_response_object: Optional[Tuple[int, str]] = await ContractQueryAndStatementManager.check_access(
            session=session,
            requester_user_uuid=requester_user_uuid,
            requester_user_privilege=requester_user_privilege,
            contract_uuid_list=contract_uuid,
        )
        if contract_check_access_response_object is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="По указанному UUID-Договора ничего не найдено!")
        
        new_start_date = datetime.datetime.strptime(new_start_date, "%d.%m.%Y").date()
        new_expiration_date = datetime.datetime.strptime(new_expiration_date, "%d.%m.%Y").date()
        
        if all([new_start_date, new_expiration_date]) and all([new_start_date != "~", new_expiration_date != "~"]):
            if new_start_date > new_expiration_date:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Дата старта действия Договора не может быть позже даты истечений!")
        
        await ContractQueryAndStatementManager.update_contract_date_range(
            session=session,
            
            contract_uuid=contract_uuid,
            new_start_date=new_start_date,
            new_expiration_date=new_expiration_date,
        )
    
    @staticmethod
    async def change_contract_file(
        session: AsyncSession,
        
        requester_user_uuid: str,
        requester_user_privilege: int,
        
        contract_uuid: str,
        
        new_file_uuid: str,
    ) -> None:
        if requester_user_privilege != PRIVILEGE_MAPPING["Admin"]:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="У Вас недостаточно прав для изменения Документа Договора!")
        
        contract_data_object = await ContractQueryAndStatementManager.get_contracts(
            session=session,
            contract_uuid_list=[contract_uuid],
        )
        if not contract_data_object.get("data"):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Дата старта действия Договора не может быть позже даты истечений!")
        
        contract_data = contract_data_object["data"][0]
        user_id: int = contract_data.user_id
        
        if await FileStoreQueryAndStatementManager.check_access(
            session=session,
            requester_user_uuid=user_id,
            requester_user_privilege=PRIVILEGE_MAPPING["Сounterparty"],
            file_uuid=new_file_uuid,
        ) is None:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f'У Пользователя-владельца карточки Договора "{contract_uuid}" нет доступа к Файлу с UUID - "{new_file_uuid}"!')
        
        await ContractQueryAndStatementManager.change_contract_file(
            session=session,
            contract_uuid=contract_uuid,
            new_file_uuid=new_file_uuid,
        )
    
    @staticmethod
    async def delete_contracts(
        session: AsyncSession,
        
        requester_user_id: int,
        requester_user_uuid: str,
        requester_user_privilege: int,
        
        contract_uuids: Optional[List[str]] = None,
    ) -> None:
        if not contract_uuids:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Для удаления Договоров, нужно указать хотя бы 1 UUID!")
        
        if requester_user_privilege != PRIVILEGE_MAPPING["Admin"]:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="У Вас недостаточно прав для удаления Договоров!")
        
        await ContractQueryAndStatementManager.delete_contracts(
            session=session,
            contract_uuids=contract_uuids,
        )
