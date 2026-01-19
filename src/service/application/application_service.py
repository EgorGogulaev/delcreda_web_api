from typing import Dict, List, Literal, Optional, Tuple

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from models.application.application_models import Application
from query_and_statement.counterparty.counterparty_qas_manager import CounterpartyQueryAndStatementManager
from schemas.application.application_schema import FiltersApplications, OrdersApplications
from src.query_and_statement.commercial_proposal_qas_manager import CommercialProposalQueryAndStatementManager
from src.service.file_store_service import FileStoreService
from src.query_and_statement.application.application_qas_manager import ApplicationQueryAndStatementManager
from src.utils.reference_mapping_data.user.mapping import PRIVILEGE_MAPPING
from src.utils.reference_mapping_data.application.mapping import APPLICATION_STATUS_MAPPING, APPLICATION_TYPE_MAPPING




class ApplicationService:
    @staticmethod
    async def get_applications(
        session: AsyncSession,
        
        requester_user_uuid: str,
        requester_user_privilege: int,
        
        user_uuid: Optional[str],
        counterparty_uuid: Optional[str],
        application_type: Optional[Literal[*list(APPLICATION_TYPE_MAPPING)]] = None, # type: ignore
        
        extended_output: bool = False,
        
        user_login_ilike: Optional[str] = None,
        legal_entity_name: Optional[str] = None,
        
        page: Optional[int] = None,
        page_size: Optional[int] = None,
        
        filter: Optional[FiltersApplications] = None,
        order: Optional[OrdersApplications] = None,
    ) -> Dict[str, List[Optional[Application]]|Optional[int]]:
        if requester_user_privilege == PRIVILEGE_MAPPING["Client"]:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Недостаточно прав!")
        
        if page or page_size:
            if (isinstance(page, int) and page <= 0) or (isinstance(page_size, int) and page_size <= 0):
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Не корректное разделение на страницы, запрошенных данных!")
        if extended_output is False and any(
            [
                user_login_ilike,
                legal_entity_name,
            ]
        ):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Параметры поиска по логину/наименованию Контрагента доступны только с extended_output==true!")
        if requester_user_privilege != PRIVILEGE_MAPPING["Admin"]:
            if not counterparty_uuid and not user_uuid:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Вы не можете просмотреть все Заявки не являясь Адмиинистратором!")
            if user_uuid != requester_user_uuid:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Вы не можете просмотреть заказы других пользователей!")
            
            if counterparty_uuid:
                counterparty_check_access_response_object: Optional[Tuple[int, int, int, str]] = await CounterpartyQueryAndStatementManager.check_access(
                    session=session,
                    
                    requester_user_uuid=requester_user_uuid,
                    requester_user_privilege=requester_user_privilege,
                    counterparty_uuid=counterparty_uuid,
                )
                if counterparty_check_access_response_object is None:
                    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Вы не являетесь владельцем данной записи о Контрагенте или её не существует!")
        
        applications: Dict[str, List[Optional[Application]]|Optional[int]] = await ApplicationQueryAndStatementManager.get_applications(
            session=session,
            
            user_uuid=user_uuid,
            counterparty_uuid=counterparty_uuid,
            application_type=application_type,
            
            extended_output=extended_output,
            
            user_login_ilike=user_login_ilike,
            legal_entity_name=legal_entity_name,
            
            page=page,
            page_size=page_size,
            
            filter=filter,
            order=order,
        )
        
        return applications
    
    @staticmethod
    async def change_applications_edit_status(
        session: AsyncSession,
        
        requester_user_uuid: str,
        requester_user_privilege: int,
        
        application_uuids: List[str],
        edit_status: bool,
    ) -> None:
        if requester_user_privilege != PRIVILEGE_MAPPING["Admin"]:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="У Вас недостаточно прав для изменения статуса возможности редактирования информации о Заявке/ах!")
        if not application_uuids:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Должен быть указан UUID, хотя бы одной Заявки!")
        if not isinstance(edit_status, bool):
            raise ValueError("Статус должен быть булевым значением!")
        
        await ApplicationQueryAndStatementManager.change_applications_edit_status(
            session=session,
            
            application_uuids=application_uuids,
            edit_status=edit_status,
        )
    
    @staticmethod
    async def change_applications_status(
        session: AsyncSession,
        
        requester_user_uuid: str,
        requester_user_privilege: int,
        
        status_: Literal[
            "Requested",
            "In_progress",
            "Rejected",
            "Requires_customer_attention",
            "Completed_successfully",
            "Completed_unsuccessfully",
        ],
        application_uuids: List[str],
    ) -> None:
        if requester_user_privilege != PRIVILEGE_MAPPING["Admin"]:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="У Вас недостаточно прав для изменения статуса Заявки/ок!")
        
        if not application_uuids:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Для изменения статуса Заявки, нужно указать хотя бы 1 UUID!")
        
        
        status_dict = {
            "Requested": "Запрошен",
            "In_progress": "В работе",
            "Rejected": "Отклонено",
            "Requires_customer_attention": "Требует внимания заказчика",
            "Completed_successfully": "Завершен успешно",
            "Completed_unsuccessfully": "Завершен неуспешно",
        }
        await ApplicationQueryAndStatementManager.change_applications_status(
            session=session,
            
            application_uuids=application_uuids,
            status=APPLICATION_STATUS_MAPPING[status_dict[status_]],
        )
    
    @staticmethod
    async def delete_applications(
        session: AsyncSession,
        
        requester_user_id: int,
        requester_user_uuid: str,
        requester_user_privilege: int,
        
        applications_uuids: List[str],
    ) -> None:
        if requester_user_privilege == PRIVILEGE_MAPPING["Client"]:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Недостаточно прав!")
        
        if not applications_uuids:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Для удаления Заявки, нужно указать хотя бы 1 UUID!")
        
        application_ids_with_application_data_ids_with_dir_uuid: List[Tuple[int, int, str]] = [] # type: ignore
        for application_uuid in applications_uuids:
            application_check_access_response_object: Optional[Tuple[int, int, str]] = await ApplicationQueryAndStatementManager.check_access(
                session=session,
                
                requester_user_uuid=requester_user_uuid,
                requester_user_privilege=requester_user_privilege,
                application_uuid=application_uuid,
                for_update_or_delete_application=True,
            )
            
            if application_check_access_response_object is None:
                if requester_user_privilege != PRIVILEGE_MAPPING["Admin"]:
                    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Вы не можете удалять информацию о Заявках других Пользователей или же доступ к редактирования данной Заявки ограничен!")
                else:
                    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Информация о Контрагенте не была найдена!")
            
            application_ids_with_application_data_ids_with_dir_uuid.append(application_check_access_response_object)
        
        for _, _, dir_uuid in application_ids_with_application_data_ids_with_dir_uuid:
            await FileStoreService.delete_doc_or_dir(
                session=session,
                
                requester_user_id=requester_user_id,
                requester_user_uuid=requester_user_uuid,
                requester_user_privilege=requester_user_privilege,
                
                uuid=dir_uuid,
                is_document=False,
                for_user=True,
            )
        
        await CommercialProposalQueryAndStatementManager.delete_commercial_proposals(
            session=session,
            
            application_uuid=application_uuid,
        )
        
        await ApplicationQueryAndStatementManager.delete_applications(
            session=session,
            
            application_ids_with_application_data_ids_with_dir_uuid=application_ids_with_application_data_ids_with_dir_uuid,
        )
