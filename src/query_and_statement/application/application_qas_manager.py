from typing import List, Optional, Tuple

from sqlalchemy import and_, delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.chat_models import Chat, Message
from src.models.application.application_models import Application
from src.models.application.mt_models import MTApplicationData
from src.utils.reference_mapping_data.user.mapping import PRIVILEGE_MAPPING
from src.utils.reference_mapping_data.chat.mapping import CHAT_SUBJECT_MAPPING



class ApplicationQueryAndStatementManager:
    @staticmethod
    async def get_user_uuid_by_application_uuid(
        session: AsyncSession,
        
        application_uuid: str
    ) -> Optional[str]:
        query = (
            select(Application.user_uuid)
            .filter(Application.uuid == application_uuid)
        )
        
        response = await session.execute(query)
        result = response.scalar_one_or_none()
        
        return result
    
    @staticmethod
    async def check_access(
        session: AsyncSession,
        
        requester_user_uuid: str,
        requester_user_privilege: int,
        
        application_uuid: str,
        
        for_update_or_delete_application: bool = False,
    ) -> Optional[Tuple[int, int, str]]:
        _filters = [Application.uuid == application_uuid]
        
        if requester_user_privilege != PRIVILEGE_MAPPING["Admin"]:
            _filters.append(Application.user_uuid == requester_user_uuid)
            if for_update_or_delete_application:
                _filters.append(Application.can_be_updated_by_user == True)  # noqa: E712
        
        
        query = (
            select(Application.id, Application.data_id, Application.directory_uuid)
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
    async def change_applications_edit_status(
        session: AsyncSession,
        
        application_uuids: List[str],
        edit_status: bool,
    ) -> None:
        stmt = (
            update(Application)
            .where(Application.uuid.in_(application_uuids))
            .values(
                can_be_updated_by_user=edit_status,
            )
        )
        await session.execute(stmt)
        await session.commit()
    
    @staticmethod
    async def change_applications_status(
        session: AsyncSession,
        
        application_uuids: List[str],
        status: int,
    ) -> None:
        stmt = (
            update(Application)
            .where(Application.uuid.in_(application_uuids))
            .values(
                status=status
            )
        )
        await session.execute(stmt)
        await session.commit()
    
    @staticmethod
    async def delete_applications(
        session: AsyncSession,
        
        application_ids_with_application_data_ids_with_dir_uuid: List[Tuple[int, int]],
    ) -> None:
        application_ids = [application_id for application_id, _, _ in application_ids_with_application_data_ids_with_dir_uuid]
        application_data_ids = [application_data_id for _, application_data_id, _ in application_ids_with_application_data_ids_with_dir_uuid]
        
        query_application = (
            select(Application.uuid)
            .filter(Application.id.in_(application_ids))
        )
        response_application = await session.execute(query_application)
        application_uuids = [item[0] for item in response_application.all()]
        
        query_chat = (
            select(Chat.id)
            .filter(
                and_(
                    Chat.chat_subject_id == CHAT_SUBJECT_MAPPING["Заявка"],
                    Chat.subject_uuid.in_(application_uuids)
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
        
        # FIXME - тут нужно предусмотреть удаление из всех бизнес-направлений
        stmt_delete_application_data = (
            delete(MTApplicationData)
            .where(MTApplicationData.id.in_(application_data_ids))
        )
        
        stmt_delete_application = (
            delete(Application)
            .where(Application.id.in_(application_ids))
        )
        
        await session.execute(stmt_del_msgs)
        await session.execute(stmt_del_chats)
        await session.execute(stmt_delete_application)
        await session.execute(stmt_delete_application_data)
        
        await session.commit()
