from typing import List, Optional, Tuple

from sqlalchemy import and_, delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.order.order_models import Order
from src.models.order.mt_models import MTOrderData
from src.utils.reference_mapping_data.user.mapping import PRIVILEGE_MAPPING



class OrderQueryAndStatementManager:
    @staticmethod
    async def get_user_uuid_by_order_uuid(
        session: AsyncSession,
        
        order_uuid: str
    ) -> Optional[str]:
        query = (
            select(Order.user_uuid)
            .filter(Order.uuid == order_uuid)
        )
        
        response = await session.execute(query)
        result = response.scalar_one_or_none()
        
        return result
    
    @staticmethod
    async def check_access(
        session: AsyncSession,
        
        requester_user_uuid: str,
        requester_user_privilege: int,
        
        order_uuid: str,
        
        for_update_or_delete_order: bool = False,
    ) -> Optional[Tuple[int, int, str]]:
        _filters = [Order.uuid == order_uuid]
        
        if requester_user_privilege != PRIVILEGE_MAPPING["Admin"]:
            _filters.append(Order.user_uuid == requester_user_uuid)
            if for_update_or_delete_order:
                _filters.append(Order.can_be_updated_by_user == True)  # noqa: E712
        
        
        query = (
            select(Order.id, Order.data_id, Order.directory_uuid)
            .filter(
                and_(
                    *_filters
                )
            )
        )
        
        response = await session.execute(query)
        result = response.one_or_none()
        
        return result
    
    @staticmethod
    async def change_orders_edit_status(
        session: AsyncSession,
        
        order_uuids: List[str],
        edit_status: bool,
    ) -> None:
        stmt = (
            update(Order)
            .where(Order.uuid.in_(order_uuids))
            .values(
                can_be_updated_by_user=edit_status,
            )
        )
        await session.execute(stmt)
        await session.commit()
    
    @staticmethod
    async def change_orders_status(
        session: AsyncSession,
        
        order_uuids: List[str],
        status: int,
    ) -> None:
        stmt = (
            update(Order)
            .where(Order.uuid.in_(order_uuids))
            .values(
                status=status
            )
        )
        await session.execute(stmt)
        await session.commit()
    
    @staticmethod
    async def delete_orders(
        session: AsyncSession,
        
        order_ids_with_order_data_ids_with_dir_uuid: List[Tuple[int, int]],
    ) -> None:
        order_ids = [order_id for order_id, _, _ in order_ids_with_order_data_ids_with_dir_uuid]
        order_data_ids = [order_data_id for _, order_data_id, _ in order_ids_with_order_data_ids_with_dir_uuid]
        
        # FIXME - тут нужно предусмотреть удаление из всех бизнес-направлений
        stmt_delete_order_data = (
            delete(MTOrderData)
            .where(MTOrderData.id.in_(order_data_ids))
        )
        
        stmt_delete_order = (
            delete(Order)
            .where(Order.id.in_(order_ids))
        )
        
        await session.execute(stmt_delete_order)
        await session.execute(stmt_delete_order_data)
        
        await session.commit()
