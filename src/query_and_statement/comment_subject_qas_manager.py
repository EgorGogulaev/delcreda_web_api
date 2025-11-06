import datetime
from typing import List, Optional

from sqlalchemy import and_, select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert

from src.models.comment_subject_models import CommentSubject



class CommentSubjectQueryAndStatementManager:
    @staticmethod
    async def check_exist(
        session: AsyncSession,
        
        subject_id: int,
        subject_uuid: str,
    ) -> bool:
        """
        Проверяет наличие Комментария для Субъекта. Возвращает False если запись не найдена и наоборот.
        """
        query = (
            select(CommentSubject)
            .where(
                and_(
                    CommentSubject.subject_id == subject_id,
                    CommentSubject.subject_uuid == subject_uuid,
                )
            )
        )
        
        response = await session.execute(query)
        result = response.one_or_none()
        if result is None:
            return False
        else:
            return True
    
    @staticmethod
    async def create_comment_subject(
        session: AsyncSession,
        
        requester_user_uuid: str,
        
        subject_id: int,
        subject_uuid: str,
        
        data: Optional[str],
    ) -> None:
        stmt = (
            insert(CommentSubject)
            .values(
                subject_id=subject_id,
                subject_uuid=subject_uuid,
                creator_uuid=requester_user_uuid,
                data=data,
            )
        )
        await session.execute(stmt)
        await session.commit()
    
    @staticmethod
    async def get_comment_subject(
        session: AsyncSession,
        
        subject_id: int,
        subject_uuid: str,
    ) -> List[Optional[CommentSubject]]:
        query = (
            select(CommentSubject)
            .where(
                and_(
                    CommentSubject.subject_id == subject_id,
                    CommentSubject.subject_uuid == subject_uuid,
                )
            )
        )
        
        response = await session.execute(query)
        result = [item[0] for item in response.all()]
        
        return result
    
    @staticmethod
    async def update_comment_subject(
        session: AsyncSession,
        
        requester_user_uuid: str,
        
        subject_id: int,
        subject_uuid: str,
        
        new_data: Optional[str],
    ) -> None:
        stmt = (
            update(CommentSubject)
            .where(
                and_(
                    CommentSubject.subject_id == subject_id,
                    CommentSubject.subject_uuid == subject_uuid
                )
            )
            .values(
                last_updater_uuid=requester_user_uuid,
                data=new_data,
                updated_at=datetime.datetime.now(tz=datetime.timezone.utc),
            )
        )
        
        await session.execute(stmt)
        await session.commit()
    
    @staticmethod
    async def delete_comment_subject(  # TODO нужно пробросить удаление, на endpoint'ы с удалением субъектов (ЮЛ/Заявок)
        session: AsyncSession,
        
        subject_id: int,
        subject_uuid: str,
    ) -> None:
        stmt = (
            delete(CommentSubject)
            .where(
                and_(
                    CommentSubject.subject_id == subject_id,
                    CommentSubject.subject_uuid == subject_uuid,
                )
            )
        )
        
        await session.execute(stmt)
        await session.commit()
