from typing import Any, Dict, List, Literal, Optional, Tuple

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from connection_module import SignalConnector
from src.schemas.commercial_proposal_schema import CommercialProposal, FiltersCommercialProposals, OrdersCommercialProposals
from src.service.chat_service import ChatService
from src.query_and_statement.user_qas_manager import UserQueryAndStatementManager
from src.service.file_store_service import FileStoreService
from src.query_and_statement.application.application_qas_manager import ApplicationQueryAndStatementManager
from src.query_and_statement.counterparty.counterparty_qas_manager import CounterpartyQueryAndStatementManager
from src.query_and_statement.commercial_proposal_qas_manager import CommercialProposalQueryAndStatementManager
from src.utils.reference_mapping_data.user.mapping import PRIVILEGE_MAPPING
from src.utils.reference_mapping_data.file_store.mapping import DIRECTORY_TYPE_MAPPING


class CommercialProposalService:
    @staticmethod
    async def create_commercial_proposal(
        session: AsyncSession,
        
        requester_user_uuid: str, requester_user_privilege: int,
        
        type: Literal[
            "MT",
            # TODO
        ],
        
        target_user_uuid: str,
        counterparty_uuid: str,
        application_uuid: Optional[str],
        
        document_uuid: Optional[str],
        
        commercial_proposal_name: Optional[str] = None,
    ) -> str:
        if requester_user_privilege != PRIVILEGE_MAPPING["Admin"]:
            if target_user_uuid != requester_user_uuid:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Вы не можете создать заявку по КП для другого Пользователя!")
        
        counterparty_check_access_response_object: Optional[Tuple[int, int, int, str]] = await CounterpartyQueryAndStatementManager.check_access(
            session=session,
            
            requester_user_uuid=requester_user_uuid,
            requester_user_privilege=requester_user_privilege,
            counterparty_uuid=counterparty_uuid,
        )
        if counterparty_check_access_response_object is None:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Вы не можете создавать заявку по КП, по данному UUID-Контрагента!")
        
        if application_uuid:
            application_check_access_response_object: Optional[Tuple[int, int, str]] = await ApplicationQueryAndStatementManager.check_access(
                session=session,
                
                requester_user_uuid=requester_user_uuid,
                requester_user_privilege=requester_user_privilege,
                application_uuid=application_uuid,
            )
            if application_check_access_response_object is None:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Вы не можете создавать заявку по КП, по данному UUID-Заявки!")
        
        user_id: int = await UserQueryAndStatementManager.get_user_id_by_uuid(
            session=session,
            
            uuid=target_user_uuid,
        )
        user_dirs: Dict[str, Any] = await FileStoreService.get_dir_info_from_db(
            session=session,
            
            requester_user_uuid=requester_user_uuid,
            requester_user_privilege=requester_user_privilege,
            owner_user_uuid=target_user_uuid,
            visible=True,
        )
        if not user_dirs["count"]:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Не найдена ни одна директория по указанным данным Пользователя!")
        parent_directory_uuid = None
        for dir_id in user_dirs["data"]:
            if user_dirs["data"][dir_id]["type"] == DIRECTORY_TYPE_MAPPING["Пользовательская директория"]:
                parent_directory_uuid = user_dirs["data"][dir_id]["uuid"]
        if not parent_directory_uuid:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="У Пользователя нет пользовательской Директории!")
        
        user_s3_login: str = await UserQueryAndStatementManager.get_user_s3_login(
            session=session,
            
            user_id=user_id,
        )
        
        new_commercial_proposal_dir_data: Dict[str, Any] = await FileStoreService.create_directory(
            session=session,
            
            requester_user_uuid=requester_user_uuid,
            requester_user_privilege=requester_user_privilege,
            owner_s3_login=user_s3_login,
            owner_user_uuid=target_user_uuid,
            directory_type=DIRECTORY_TYPE_MAPPING["Директория заявки по КП"],
            new_directory_uuid=None,
            parent_directory_uuid=parent_directory_uuid,
        )
        
        new_commercial_proposal_uuid_coro = await SignalConnector.generate_identifiers(target="Заявка", count=1)
        new_commercial_proposal_uuid = new_commercial_proposal_uuid_coro[0]
        
        await CommercialProposalQueryAndStatementManager.create_commercial_proposal(
            session=session,
            
            new_commercial_proposal_uuid=new_commercial_proposal_uuid,
            commercial_proposal_name=commercial_proposal_name,
            type=type,
            user_id=user_id,
            target_user_uuid=target_user_uuid,
            counterparty_id=counterparty_check_access_response_object[0],
            counterparty_uuid=counterparty_uuid,
            application_id=application_check_access_response_object[0] if application_uuid else None,
            application_uuid=application_uuid if application_uuid else None,
            
            directory_id=new_commercial_proposal_dir_data["id"],
            directory_uuid=new_commercial_proposal_dir_data["uuid"],
            
            document_uuid=document_uuid,
        )
        await ChatService.create_chat(
            session=session,
            
            chat_subject="Заявка на КП",
            subject_uuid=new_commercial_proposal_uuid,
        )
        return new_commercial_proposal_uuid
    
    @staticmethod
    async def get_commercial_proposals(
        session: AsyncSession,
        
        requester_user_uuid: str,
        requester_user_privilege: int,
        
        user_uuid: Optional[str],
        
        page: Optional[int] = None,
        page_size: Optional[int] = None,
        
        filter: Optional[FiltersCommercialProposals] = None,
        order: Optional[OrdersCommercialProposals] = None,
    ) -> Dict[str, List[Optional[CommercialProposal]]]:
        if page or page_size:
            if (isinstance(page, int) and page <= 0) or (isinstance(page_size, int) and page_size <= 0):
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Не корректное разделение на страницы, запрошенных данных!")
        
        if requester_user_privilege != PRIVILEGE_MAPPING["Admin"]:
            if not user_uuid:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Вы не можете просмотреть все заявки на КП - всех пользователей!")
            if user_uuid != requester_user_uuid:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Вы не можете просмотреть заявки на КП других пользователей!")
        
        commercial_proposals: Dict[str, List[Optional[CommercialProposal]]] = await CommercialProposalQueryAndStatementManager.get_commercial_proposals(
            session=session,
            user_uuid=user_uuid,
            page=page,
            page_size=page_size,
            filter=filter,
            order=order,
        )
        
        return commercial_proposals
    
    @staticmethod
    async def update_commercial_proposals_status(
        session: AsyncSession,
        
        requester_user_uuid: str,
        requester_user_privilege: int,
        
        commercial_proposal_uuids: List[str],
        new_status: bool,
    ) -> None:
        if requester_user_privilege != PRIVILEGE_MAPPING["Admin"]:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="У Вас недостаточно прав для изменения статуса возможности редактирования заявки по КП!")
        if not commercial_proposal_uuids:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Должен быть указан UUID, хотя бы одной заявки на КП!")
        if not isinstance(new_status, bool):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Статус должен быть булевым значением!")
        
        await CommercialProposalQueryAndStatementManager.update_commercial_proposals_status(
            session=session,
            
            commercial_proposal_uuids=commercial_proposal_uuids,
            new_status=new_status,
        )
    
    @staticmethod
    async def change_commercial_proposal_document_uuid(
        session: AsyncSession,
        
        requester_user_uuid: str,
        requester_user_privilege: int,
        
        commercial_proposal_uuid: str,
        document_uuid: str,
    ) -> Tuple[str, str, str]:
        if requester_user_privilege != PRIVILEGE_MAPPING["Admin"]:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="У Вас недостаточно прав для изменения документа КП (в заявке на КП)!")
        if not commercial_proposal_uuid:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Должен быть указан UUID заявки на КП!")
        if not document_uuid:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Должен быть указан UUID документа для прикрепление к заявке на КП!")
        
        commercial_proposal: Dict[str, List[Optional[CommercialProposal]]] = await CommercialProposalQueryAndStatementManager.get_commercial_proposals(
            session=session,
            
            commercial_proposal_uuid_list=[commercial_proposal_uuid],
        )
        commercial_proposal_data = commercial_proposal["data"]
        if not commercial_proposal_data:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="По указанному UUID заявки на КП запись не найден!")
        
        user_uuid: str = commercial_proposal_data[0].user_uuid
        counterparty_uuid: str = commercial_proposal_data[0].counterparty_uuid
        application_uuid: str = commercial_proposal_data[0].application_uuid
        
        await CommercialProposalQueryAndStatementManager.change_commercial_proposal_document_uuid(
            session=session,
            commercial_proposal_uuid=commercial_proposal_uuid,
            document_uuid=document_uuid,
        )
        
        return user_uuid, counterparty_uuid, application_uuid
    
    @staticmethod
    async def change_commercial_proposals_edit_status(
        session: AsyncSession,
        
        requester_user_uuid: str,
        requester_user_privilege: int,
        
        commercial_proposal_uuids: List[str],
        edit_status: bool,
    ) -> None:
        if requester_user_privilege != PRIVILEGE_MAPPING["Admin"]:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="У Вас недостаточно прав для изменения статуса возможности редактирования заявки на КП!")
        if not commercial_proposal_uuids:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Должен быть указан UUID, хотя бы одной заявки на КП!")
        if not isinstance(edit_status, bool):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Статус должен быть булевым значением!")
        
        await CommercialProposalQueryAndStatementManager.change_commercial_proposals_edit_status(
            session=session,
            commercial_proposal_uuids=commercial_proposal_uuids,
            edit_status=edit_status,
        )
    
    @staticmethod
    async def delete_commercial_proposals(
        session: AsyncSession,
        
        requester_user_id: int,
        requester_user_uuid: str,
        requester_user_privilege: int,
        
        commercial_proposal_uuids: Optional[List[str]] = None,
        
        counterparty_uuid: Optional[str] = None,
        application_uuid: Optional[str] = None,
    ) -> None:
        if not commercial_proposal_uuids:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Для удаления заявок на КП, нужно указать хотя бы 1 UUID!")
        
        commercial_proposal_id_and_dir_uuid: List[Tuple[int, str]] = []
        for commercial_proposal_uuid in commercial_proposal_uuids:
            commercial_proposal_check_access_response_object: Optional[Tuple[int, str]] = await CommercialProposalQueryAndStatementManager.check_access(
                session=session,
                requester_user_uuid=requester_user_uuid,
                requester_user_privilege=requester_user_privilege,
                commercial_proposal_uuid=commercial_proposal_uuid,
                for_update_or_delete_commercial_proposal=True,
            )
            if commercial_proposal_check_access_response_object is None:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Вы не можете удалять заявки по КП других Пользователей!")
            
            commercial_proposal_id_and_dir_uuid.append(commercial_proposal_check_access_response_object)
        
        for _, dir_uuid in commercial_proposal_id_and_dir_uuid:
            try:
                await FileStoreService.delete_doc_or_dir(
                    session=session,
                    
                    requester_user_id=requester_user_id,
                    requester_user_uuid=requester_user_uuid,
                    requester_user_privilege=requester_user_privilege,
                    
                    uuid=dir_uuid,
                    is_document=False,
                    for_user=True,
                )
            except: ...  # noqa: E722
        
        await CommercialProposalQueryAndStatementManager.delete_commercial_proposals(
            session=session,
            
            commercial_proposal_ids=None,
            commercial_proposal_uuids=commercial_proposal_uuids,
            
            counterparty_uuid=counterparty_uuid,
            application_uuid=application_uuid,
        )
