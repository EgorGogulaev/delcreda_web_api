# TODO Реализовать

from pathlib import Path
from typing import Any, Dict, Optional, Tuple
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from connection_module import SignalConnector
from query_and_statement.application.application_qas_manager import ApplicationQueryAndStatementManager
from query_and_statement.counterparty.counterparty_qas_manager import CounterpartyQueryAndStatementManager
from src.service.chat_service import ChatService
from src.query_and_statement.contract_qas_manager import ContractQueryAndStatementManager
from src.query_and_statement.user_qas_manager import UserQueryAndStatementManager
from src.service.file_store_service import FileStoreService
from src.utils.reference_mapping_data.user.mapping import PRIVILEGE_MAPPING
from src.utils.reference_mapping_data.file_store.mapping import DIRECTORY_TYPE_MAPPING


class ContractService:
    @staticmethod
    async def create_contract(
        session: AsyncSession,
        
        requester_user_uuid: str, requester_user_privilege: int,
        
        document_uuid: str,
        type: str,
        
        start_date: Optional[str] = None,
        expiration_date: Optional[str] = None,
    ) -> Tuple[str, Optional[str], str, str, str]:
        if requester_user_privilege != PRIVILEGE_MAPPING["Admin"]:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="У Вас недостаточно прав для создания карточки Договора!")
        
        if not all([document_uuid, type]):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Для создания карточки Договора нужно указать как UUID-Документа, так и тип Договора!")
        
        data_from_db_about_document_response: Dict[str, Any] = await FileStoreService.get_doc_info_from_db(
            session=session,
            
            requester_user_uuid=requester_user_uuid,
            requester_user_privilege=requester_user_privilege,
            file_uuids=[document_uuid],
            visible=True,
        )
        data_from_db_about_document: Dict[int, Any] = data_from_db_about_document_response["data"][list(data_from_db_about_document_response["data"])[0]]
        
        owner_user_id: int = data_from_db_about_document.get("owner_user_id")
        owner_user_uuid: str = data_from_db_about_document.get("owner_user_uuid")
        directory_id: int = data_from_db_about_document.get("directory_id")
        name: str = data_from_db_about_document.get("name")
        
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
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f'При поиске принадлежности Документа, не нашлась карточка Контрагента(ID Директории - "{directory_id}")!')
        
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
            document_uuid=document_uuid,
            start_date=start_date,
            expiration_date=expiration_date,
        )
        
        await ChatService.create_chat(
            session=session,
            
            chat_subject="Договор",
            subject_uuid=new_contract_uuid,
        )
        
        return counterparty_uuid, application_uuid, new_contract_uuid, owner_user_uuid, Path(name if name else "-").stem
