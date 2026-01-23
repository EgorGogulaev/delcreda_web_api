# TODO Реализовать
import datetime
from typing import Dict, List, Optional, Tuple
from fastapi import HTTPException, status
from sqlalchemy import and_, delete, func, insert, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from models.chat_models import Chat, Message
from src.schemas.contract_schema import FiltersContracts, OrdersContracts
from src.models.contract_models import Contract
from src.utils.reference_mapping_data.contract.mapping import CONTRACT_TYPE_MAPPING
from src.utils.reference_mapping_data.user.mapping import PRIVILEGE_MAPPING
from utils.reference_mapping_data.chat.mapping import CHAT_SUBJECT_MAPPING


class ContractQueryAndStatementManager:
    @staticmethod
    async def create_contract(
        session: AsyncSession,
        
        uuid: str,
        name: str,
        type: str,
        user_id: int,
        user_uuid: str,
        counterparty_id: int,
        counterparty_uuid: str,
        application_id: Optional[int],
        application_uuid: Optional[str],
        file_uuid: str,
        start_date: Optional[str],
        expiration_date: Optional[str],
    ) -> None:
        stmt = (
            insert(Contract)
            .values(
                uuid=uuid,
                name=name,
                type=CONTRACT_TYPE_MAPPING[type],
                user_id=user_id,
                user_uuid=user_uuid,
                counterparty_id=counterparty_id,
                counterparty_uuid=counterparty_uuid,
                application_id=application_id,
                application_uuid=application_uuid,
                file_uuid=file_uuid,
                start_date=start_date,
                expiration_date=expiration_date,
            )
        )
        
        await session.execute(stmt)
        await session.commit()
    
    @staticmethod
    async def get_contracts(
        session: AsyncSession,
        
        user_uuid: Optional[str] = None,
        contract_id_list: Optional[List[int]] = None,
        contract_uuid_list: Optional[List[str]] = None,
        
        page: Optional[int] = None,
        page_size: Optional[int] = None,
        
        filter: Optional[FiltersContracts] = None,
        order: Optional[OrdersContracts] = None,
    ) -> Dict[str, List[Optional[Contract]]|int]:
        _filters = []
        
        if user_uuid:
            _filters.append(Contract.user_uuid == user_uuid)
        
        if contract_id_list:
            _filters.append(Contract.id.in_(contract_id_list))
        
        if contract_uuid_list:
            _filters.append(Contract.uuid.in_(contract_uuid_list))
        
        if filter is not None and filter.filters:
            for filter_item in filter.filters:
                column = getattr(Contract, filter_item.field)
                if filter_item.operator == "eq":
                    cond = column == filter_item.value
                elif filter_item.operator == "ne":
                    cond = column != filter_item.value
                elif filter_item.operator == "gt":
                    cond = column > filter_item.value
                elif filter_item.operator == "lt":
                    cond = column < filter_item.value
                elif filter_item.operator == "ge":
                    cond = column >= filter_item.value
                elif filter_item.operator == "le":
                    cond = column <= filter_item.value
                elif filter_item.operator == "like":
                    value = f"%{filter_item.value}%"
                    cond = column.ilike(value)
                elif filter_item.operator == "in":
                    if isinstance(filter_item.value, str):
                        values = [v.strip() for v in filter_item.value.split(",")]
                    else:
                        values = filter_item.value
                    cond = column.in_(values)
                else:
                    continue
                
                _filters.append(cond)
        
        # ===== сортировка =====
        _order_clauses = []
        if order is not None and order.orders:
            for order_item in order.orders:
                # Получаем атрибут модели для сортировки
                column = getattr(Contract, order_item.field)
                
                # Добавляем условие сортировки в зависимости от направления
                if order_item.direction == "asc":
                    _order_clauses.append(column.asc().nulls_last())
                else:
                    _order_clauses.append(column.desc().nulls_last())
        
        if not _order_clauses:
            _order_clauses.append(Contract.id.asc())
        # ===== КОНЕЦ блока сортировки =====
        
        query = (
            select(Contract)
            .filter(and_(*_filters))
            .order_by(*_order_clauses)
        )
        
        total_records = None
        total_pages = None
        
        if page is None or (page is not None and page < 1):
            page = 1
        if page_size is None or (page is not None and page_size < 1):
            page_size = 50
        
        query = query.limit(page_size).offset((page - 1) * page_size)
        count_query = select(func.count()).select_from(Contract).filter(and_(*_filters))
        
        total_records = (await session.execute(count_query)).scalar()
        total_pages = (total_records + page_size - 1) // page_size if total_records else 0
        
        response = await session.execute(query)
        
        data = [item[0] for item in response.fetchall()]
        
        return {
            "data": data,
            "total_records": total_records,
            "total_pages": total_pages,
        }
    
    @staticmethod
    async def check_access(
        session: AsyncSession,
        
        requester_user_uuid: str,
        requester_user_privilege: int,
        
        contract_uuid: str,
    ) -> Optional[Tuple[int, str]]:
        _filters = [Contract.uuid == contract_uuid]
        
        if requester_user_privilege != PRIVILEGE_MAPPING["Admin"]:
            _filters.append(Contract.user_uuid == requester_user_uuid)
        
        query = (
            select(Contract.id, Contract.uuid)
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
    async def update_contract_date_range(
        session: AsyncSession,
        
        contract_uuid: str,
        new_start_date: Optional[str] = "~",
        new_expiration_date: Optional[str] = "~",
    ) -> None:
        values_for_update = {
            "startt_date": new_start_date,
            "expiration_date": new_expiration_date,
            
            "updated_at": datetime.datetime.now(tz=datetime.timezone.utc),
        }
        
        new_values = {k: v for k, v in values_for_update.items() if v != "~"}
        stmt = (
            update(Contract)
            .filter(Contract.uuid == contract_uuid)
            .values(**new_values)
        )
        
        await session.execute(stmt)
        await session.commit()
    
    @staticmethod
    async def change_contract_file(
        session: AsyncSession,
        
        contract_uuid: str,
        new_file_uuid: str,
    ) -> None:
        stmt = (
            update(Contract)
            .filter(Contract.uuid == contract_uuid)
            .values({"file_uuid": new_file_uuid})
        )
        
        await session.execute()
        await session.commit()
    
    @staticmethod
    async def delete_contracts(
        session: AsyncSession,
        
        contract_uuids: Optional[List[str]] = None,
        contract_ids: Optional[List[int]] = None,
        
        counterparty_uuid: Optional[str] = None,
        application_uuid: Optional[str] = None,
    ) -> None:
        if not contract_uuids and not contract_ids:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Для удаления должны быть указаны либо массив UUID, либо массив ID заявок на КП!")
        
        if not contract_uuids:
            query_c = (select(Contract.uuid)
                .filter(Contract.id.in_(contract_ids))
            )
            response_c = await session.execute(query_c)
            contract_uuids = [item[0] for item in response_c.all()]
        
        query_chat = (
            select(Chat.id)
            .filter(
                and_(
                    Chat.chat_subject_id == CHAT_SUBJECT_MAPPING["Договор"],
                    Chat.subject_uuid.in_(contract_uuids)
                )
            )
        )
        
        response_chat = await session.execute(query_chat)
        chat_ids = [item[0] for item in response_chat.all()]
        
        query_msg = (
            select(Message.id)
            .filter(Message.chat_id.in_(chat_ids))
        )
        response_msg = await session.execute(query_msg)
        msg_ids = [item[0] for item in response_msg.all()]
        
        stmt_del_msgs = (
            delete(Message)
            .filter(Message.id.in_(msg_ids))
        )
        stmt_del_chats = (
            delete(Chat)
            .filter(Chat.id.in_(chat_ids))
        )
        _filters = []
        
        if contract_uuids:
            _filters.append(Contract.uuid.in_(contract_uuids))
        
        if counterparty_uuid:
            _filters.append(Contract.counterparty_uuid == counterparty_uuid)
        
        if application_uuid:
            _filters.append(Contract.application_uuid == application_uuid)
        
        stmt_del_cs = (
            delete(Contract)
            .filter(
                and_(
                    *_filters
                )
            )
        )
        
        await session.execute(stmt_del_msgs)
        await session.execute(stmt_del_chats)
        await session.execute(stmt_del_cs)
        
        await session.commit()
