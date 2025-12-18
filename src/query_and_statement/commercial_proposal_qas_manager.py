import datetime
from pathlib import Path
from typing import Dict, List, Literal, Optional, Tuple

from fastapi import HTTPException, status
from sqlalchemy import and_, func, insert, select, delete, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.file_store_models import Document
from src.models.chat_models import Chat, Message
from src.schemas.commercial_proposal_schema import FiltersCommercialProposals, OrdersCommercialProposals
from src.models.commercial_proposal_models import CommercialProposal
from src.utils.reference_mapping_data.user.mapping import PRIVILEGE_MAPPING
from src.utils.reference_mapping_data.commercial_proposal.mapping import COMMERCIAL_PROPOSAL_STATUS_MAPPING, COMMERCIAL_PROPOSAL_TYPE_MAPPING
from src.utils.reference_mapping_data.chat.mapping import CHAT_SUBJECT_MAPPING


class CommercialProposalQueryAndStatementManager:
    @staticmethod
    async def create_commercial_proposal(
        session: AsyncSession,
        
        new_commercial_proposal_uuid: str,
        commercial_proposal_name: Optional[str],
        type: Literal[
            "MT",
            # TODO
        ],
        
        user_id,
        target_user_uuid: str,
        
        counterparty_id: int,
        counterparty_uuid: str,
        application_id: Optional[int],
        application_uuid: Optional[str],
        directory_id: int,
        directory_uuid: str,
        
        document_uuid: Optional[str],
        
    ) -> None:
        
        stmt = (
            insert(CommercialProposal)
            .values(
                uuid=new_commercial_proposal_uuid,
                appliaction_name=commercial_proposal_name if commercial_proposal_name else f"{counterparty_id}-{directory_id}-{datetime.datetime.now().year}",
                commercial_proposal_name=commercial_proposal_name,
                type=COMMERCIAL_PROPOSAL_TYPE_MAPPING[type],
                user_id=user_id,
                user_uuid=target_user_uuid,
                counterparty_id=counterparty_id,
                counterparty_uuid=counterparty_uuid,
                application_id=application_id,
                application_uuid=application_uuid,
                directory_id=directory_id,
                directory_uuid=directory_uuid,
                document_uuid=document_uuid,
                status=COMMERCIAL_PROPOSAL_STATUS_MAPPING["На рассмотрении сторон"],
            )
        )
        
        await session.execute(stmt)
        await session.commit()
    
    
    @staticmethod
    async def get_commercial_proposals(
        session: AsyncSession,
        
        user_uuid: Optional[str] = None,
        commercial_proposal_id_list: Optional[List[int]] = None,
        commercial_proposal_uuid_list: Optional[List[str]] = None,
        
        page: Optional[int] = None,
        page_size: Optional[int] = None,
        
        filter: Optional[FiltersCommercialProposals] = None,
        order: Optional[OrdersCommercialProposals] = None,
    ) -> Dict[str, List[Optional[CommercialProposal]]]:
        _filters = []
        
        if user_uuid:
            _filters.append(CommercialProposal.user_uuid == user_uuid)
        
        if commercial_proposal_id_list:
            _filters.append(CommercialProposal.id.in_(commercial_proposal_id_list))
        
        if commercial_proposal_uuid_list:
            _filters.append(CommercialProposal.uuid.in_(commercial_proposal_uuid_list))
        
        if filter is not None and filter.filters:
            for filter_item in filter.filters:
                column = getattr(CommercialProposal, filter_item.field)
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
                column = getattr(CommercialProposal, order_item.field)
                
                # Добавляем условие сортировки в зависимости от направления
                if order_item.direction == "asc":
                    _order_clauses.append(column.asc().nulls_last())
                else:
                    _order_clauses.append(column.desc().nulls_last())
        
        if not _order_clauses:
            _order_clauses.append(CommercialProposal.id.asc())
        # ===== КОНЕЦ блока сортировки =====
        
        query = (
            select(CommercialProposal)
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
        count_query = select(func.count()).select_from(CommercialProposal).filter(and_(*_filters))
        
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
    async def update_commercial_proposals_status(
        session: AsyncSession,
        
        commercial_proposal_uuids: List[str],
        new_status: Literal[
            "На рассмотрении сторон",
            "Согласовано",
            "Отклонено",
            "Закрыто администратором",
        ],
    ) -> None:
        stmt = (
            update(CommercialProposal)
            .where(CommercialProposal.uuid.in_(commercial_proposal_uuids))
            .values(
                status=COMMERCIAL_PROPOSAL_STATUS_MAPPING[new_status],
            )
        )
        
        await session.execute(stmt)
        await session.commit()
    
    @staticmethod
    async def change_commercial_proposal_document_uuid(
        session: AsyncSession,
        
        commercial_proposal_uuid: str,
        document_uuid: str,
    ) -> None:
        query = (
            select(Document.name)
            .filter(Document.uuid == document_uuid)
        )
        response = await session.execute(query)
        file_name = response.scalar()
        
        if file_name is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Документ с указанным UUID не был найден!")
        
        stmt = (
            update(CommercialProposal)
            .filter(CommercialProposal.uuid == commercial_proposal_uuid)
            .values(
                document_uuid=document_uuid,
                commercial_proposal_name=Path(file_name).stem,
            )
        )
        
        await session.execute(stmt)
        await session.commit()
    
    @staticmethod
    async def change_commercial_proposals_edit_status(
        session: AsyncSession,
        
        commercial_proposal_uuids: List[str],
        edit_status: bool,
    ) -> None:
        stmt = (
            update(CommercialProposal)
            .where(CommercialProposal.uuid.in_(commercial_proposal_uuids))
            .values(
                can_be_updated_by_user=edit_status,
            )
        )
        
        await session.execute(stmt)
        await session.commit()
    
    @staticmethod
    async def delete_commercial_proposals(
        session: AsyncSession,
        
        commercial_proposal_uuids: Optional[List[str]] = None,
        commercial_proposal_ids: Optional[List[int]] = None,
        
        counterparty_uuid: Optional[str] = None,
        application_uuid: Optional[str] = None,
    ) -> None:
        if not commercial_proposal_uuids and not commercial_proposal_ids:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Для удаления должны быть указаны либо массив UUID, либо массив ID заявок на КП!")
        
        if not commercial_proposal_uuids:
            query_cp = (select(CommercialProposal.uuid)
                .filter(CommercialProposal.id.in_(commercial_proposal_ids))
            )
            response_cp = await session.execute(query_cp)
            commercial_proposal_uuids = [item[0] for item in response_cp.all()]
        
        query_chat = (
            select(Chat.id)
            .filter(
                and_(
                    Chat.chat_subject_id == CHAT_SUBJECT_MAPPING["Заявка на КП"],
                    Chat.subject_uuid.in_(commercial_proposal_uuids)
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
        
        if commercial_proposal_uuids:
            _filters.append(CommercialProposal.uuid.in_(commercial_proposal_uuids))
        
        if counterparty_uuid:
            _filters.append(CommercialProposal.counterparty_uuid == counterparty_uuid)
        
        if application_uuid:
            _filters.append(CommercialProposal.application_uuid == application_uuid)
        
        stmt_del_cps = (
            delete(CommercialProposal)
            .filter(
                and_(
                    *_filters
                )
            )
        )
        
        await session.execute(stmt_del_msgs)
        await session.execute(stmt_del_chats)
        await session.execute(stmt_del_cps)
        
        await session.commit()
    
    @staticmethod
    async def check_access(
        session: AsyncSession,
        
        requester_user_uuid: str,
        requester_user_privilege: int,
        
        commercial_proposal_uuid: str,
        
        for_update_or_delete_commercial_proposal: bool = False,
    ) -> Optional[Tuple[int, str]]:
        _filters = [CommercialProposal.uuid == commercial_proposal_uuid]
        
        if requester_user_privilege != PRIVILEGE_MAPPING["Admin"]:
            _filters.append(CommercialProposal.user_uuid == requester_user_uuid)
            if for_update_or_delete_commercial_proposal:
                _filters.append(CommercialProposal.can_be_updated_by_user == True)  # noqa: E712
        
        query = (
            select(CommercialProposal.id, CommercialProposal.directory_uuid, )
            .filter(
                and_(
                    *_filters
                )
            )
        )
        response = await session.execute(query)
        result = response.one_or_none()
        
        return result
