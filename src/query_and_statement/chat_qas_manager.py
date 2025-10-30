from typing import Dict, List, Literal, Optional, Tuple

from sqlalchemy import and_, func, select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert

from connection_module import async_session_maker
from src.models.chat_models import Chat, Message
from src.models.legal_entity_models import LegalEntity
from src.models.order.order_models import Order
from src.utils.reference_mapping_data.user.mapping import PRIVILEGE_MAPPING


class ChatQueryAndStatementManager:
    @staticmethod
    async def create_chat(
        session: AsyncSession,
        
        chat_subject_id: int,
        subject_uuid: str
    ) -> Optional[Tuple[Chat]]:
        new_chat = Chat(
            chat_subject_id=chat_subject_id,
            subject_uuid=subject_uuid,
        )
        session.add(new_chat)
        await session.commit()
        await session.refresh(new_chat)  # Обновляем объект
        return new_chat
    
    @staticmethod
    async def check_access(
        session: Optional[AsyncSession],
        
        requester_user_uuid: str,
        requester_user_privilege: int,
        
        chat_subject: Literal["Поручение", "ЮЛ"],
        subject_uuid: str,
    ) -> Optional[int]:
        async def __do(session: AsyncSession):
            subject_table = LegalEntity if chat_subject == "ЮЛ" else Order
            
            _filters = [subject_table.uuid == subject_uuid]
            
            if requester_user_privilege != PRIVILEGE_MAPPING["Admin"]:
                _filters.append(subject_table.user_uuid == requester_user_uuid)
            
            query = (
                select(Chat.id)
                .outerjoin(
                    subject_table,
                    Chat.subject_uuid == subject_table.uuid
                )
                .filter(
                    and_(
                        *_filters
                    )
                    
                )
            )
            response = await session.execute(query)
            result = response.scalar()
            
            return result
        
        if session:
            return await __do(session=session)
        else:
            async with async_session_maker() as session:
                return await __do(session=session)
    
    @staticmethod
    async def send_message(
        session: Optional[AsyncSession],
        
        requester_user_id: int,
        requester_user_uuid: str,
        requester_user_privilege: int,
        
        chat_id: str,
        message: str,
    ) -> None:
        async def __do(session: AsyncSession):
            stmt = (
                insert(Message)
                .values(
                    user_id=requester_user_id,
                    user_uuid=requester_user_uuid,
                    user_privilege_id=requester_user_privilege,
                    chat_id=chat_id,
                    data=message,
                )
            )
            await session.execute(stmt)
            await session.commit()
        if session:
            return await __do(session=session)
        else:
            async with async_session_maker() as session:
                return await __do(session=session)
    
    @staticmethod
    async def get_messages(
        session: AsyncSession,
        
        chat_id: int,
        
        page: Optional[int] = None,
        page_size: Optional[int] = None,
    ) -> Dict[str, List[Optional[Message]]|Optional[int]]:
        query = (
            select(Message)
            .filter(
                Message.chat_id == chat_id
            )
            .order_by(Message.created_at.desc())
        )
        
        total_records = None
        total_pages = None
        
        if page is None or (page is not None and page < 1):
            page = 1
        if page_size is None or (page is not None and page_size < 1):
            page_size = 50
        
        query = query.limit(page_size).offset((page - 1) * page_size)
        count_query = select(func.count()).select_from(Message).filter(Message.chat_id == chat_id)
        
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
    async def delete_messages(
        session: AsyncSession,
        
        list_ids: List[int],
    ) -> None:
        stmt = (
            delete(Message)
            .filter(Message.id.in_(list_ids))
        )
        await session.execute(stmt)
        await session.commit()
