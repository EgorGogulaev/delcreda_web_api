# TODO Реализовать

from typing import Any, Dict, Optional
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from connection_module import SignalConnector
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
    ) -> None:
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
        data_from_ab_about_document: Dict[int, Any] = data_from_db_about_document_response["data"][list(data_from_db_about_document_response["data"])[0]]
        
        owner_user_id: int = data_from_ab_about_document.get("owner_user_id")
        owner_user_uuid: str = data_from_ab_about_document.get("owner_user_uuid")
        parent_directory_uuid: str = data_from_ab_about_document.get("directory_uuid")
        if owner_user_id is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Не удалось извлечь ID-владельца Документа из БД!")
        if parent_directory_uuid is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Не удалось извлечь UUID-Директории, в которой хранится Документ!")
        
        user_s3_login: str = await UserQueryAndStatementManager.get_user_s3_login(
            session=session,
            
            user_id=owner_user_id,
        )
        
        new_contract_uuid_coro = await SignalConnector.generate_identifiers(target="Договор", count=1)
        new_contract_uuid = new_contract_uuid_coro[0]
        
        # TODO
        await ContractQueryAndStatementManager.create_contract(
            session=session,
            
            new_uuid=uuid,
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
        
    ...  # TODO
