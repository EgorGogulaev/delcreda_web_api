from typing import List, Literal, Optional, Tuple

from sqlalchemy.ext.asyncio import AsyncSession

from src.service.file_store_service import FileStoreService
from src.query_and_statement.order.order_qas_manager import OrderQueryAndStatementManager
from src.utils.reference_mapping_data.user.mapping import PRIVILEGE_MAPPING
from src.utils.reference_mapping_data.order.mapping import ORDER_STATUS_MAPPING


class OrderService:
    @staticmethod
    async def change_orders_edit_status(
        session: AsyncSession,
        
        requester_user_uuid: str,
        requester_user_privilege: int,
        
        order_uuids: List[str],
        edit_status: bool,
    ) -> None:
        if requester_user_privilege != PRIVILEGE_MAPPING["Admin"]:
            raise AssertionError("У Вас недостаточно прав для изменения статуса возможности редактирования информации о Поручении/ях!")
        assert order_uuids, "Должен быть указан UUID, хотя бы одного Поручения!"
        assert isinstance(edit_status, bool), "Статус должен быть булевым значением!"
        
        await OrderQueryAndStatementManager.change_orders_edit_status(
            session=session,
            
            order_uuids=order_uuids,
            edit_status=edit_status,
        )
    
    @staticmethod
    async def change_orders_status(
        session: AsyncSession,
        
        requester_user_uuid: str,
        requester_user_privilege: int,
        
        status: Literal[
            "Requested",
            "In_progress",
            "Rejected",
            "Requires_customer_attention",
            "Completed_successfully",
            "Completed_unsuccessfully",
        ],
        order_uuids: List[str],
    ) -> None:
        if requester_user_privilege != PRIVILEGE_MAPPING["Admin"]:
            raise AssertionError("У Вас недостаточно прав для изменения статуса Поручения/ий!")
        assert order_uuids, "Для изменения статуса Поручений, нужно указать хотя бы 1 UUID!"
        
        
        status_dict = {
            "Requested": "Запрошен",
            "In_progress": "В работе",
            "Rejected": "Отклонено",
            "Requires_customer_attention": "Требует внимания заказчика",
            "Completed_successfully": "Завершен успешно",
            "Completed_unsuccessfully": "Завершен не успешно",
        }
        await OrderQueryAndStatementManager.change_orders_status(
            session=session,
            
            order_uuids=order_uuids,
            status=ORDER_STATUS_MAPPING[status_dict[status]],
        )
    
    # FIXME НУЖНО ПЕРЕДЕЛАТЬ ПОД ЛОГИКУ МНОЖЕСТВА ВИДОВ БИЗНЕС-УСЛУГ
    @staticmethod
    async def delete_orders(  # TODO нужно предусмотреть удаление ЧАТОВ и СМС!!!
        session: AsyncSession,
        
        requester_user_id: int,
        requester_user_uuid: str,
        requester_user_privilege: int,
        
        orders_uuids: List[str],
    ) -> None:
        assert orders_uuids, "Для удаления Поручений, нужно указать хотя бы 1 UUID!"
        
        order_ids_with_order_data_ids_with_dir_uuid: List[Tuple[int, int, str]] = [] # type: ignore
        for order_uuid in orders_uuids:
            order_check_access_response_object: Optional[Tuple[int, int, str]] = await OrderQueryAndStatementManager.check_access(
                session=session,
                
                requester_user_uuid=requester_user_uuid,
                requester_user_privilege=requester_user_privilege,
                order_uuid=order_uuid,
                for_update_or_delete_order=True,
            )
            assert order_check_access_response_object, "Вы не можете удалять информацию Поручениях других Пользователей или же доступ к редактирования данного Поручения ограничен!"
            order_ids_with_order_data_ids_with_dir_uuid.append(order_check_access_response_object)
        
        for _, _, dir_uuid in order_ids_with_order_data_ids_with_dir_uuid:
            await FileStoreService.delete_doc_or_dir(
                session=session,
                
                requester_user_id=requester_user_id,
                requester_user_uuid=requester_user_uuid,
                requester_user_privilege=requester_user_privilege,
                
                uuid=dir_uuid,
                is_document=False,
                for_user=True,
            )
        
        await OrderQueryAndStatementManager.delete_orders(
            session=session,
            
            order_ids_with_order_data_ids_with_dir_uuid=order_ids_with_order_data_ids_with_dir_uuid,
        )

