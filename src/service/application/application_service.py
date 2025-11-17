from typing import List, Literal, Optional, Tuple

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.service.file_store_service import FileStoreService
from src.query_and_statement.application.application_qas_manager import ApplicationQueryAndStatementManager
from src.utils.reference_mapping_data.user.mapping import PRIVILEGE_MAPPING
from src.utils.reference_mapping_data.application.mapping import APPLICATION_STATUS_MAPPING


class ApplicationService:
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
            "Completed_unsuccessfully": "Завершен не успешно",
        }
        await ApplicationQueryAndStatementManager.change_applications_status(
            session=session,
            
            application_uuids=application_uuids,
            status=APPLICATION_STATUS_MAPPING[status_dict[status_]],
        )
    
    @staticmethod
    async def delete_applications(  # TODO нужно предусмотреть удаление ЧАТОВ и СМС!!!
        session: AsyncSession,
        
        requester_user_id: int,
        requester_user_uuid: str,
        requester_user_privilege: int,
        
        applications_uuids: List[str],
    ) -> None:
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
                    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Информация о ЮЛ не была найдена!")
            
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
        
        await ApplicationQueryAndStatementManager.delete_applications(
            session=session,
            
            application_ids_with_application_data_ids_with_dir_uuid=application_ids_with_application_data_ids_with_dir_uuid,
        )
