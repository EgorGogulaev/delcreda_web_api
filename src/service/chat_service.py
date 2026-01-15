from typing import Dict, List, Literal, Optional

from fastapi import HTTPException
from fastapi import status
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.chat_models import Chat, Message
from src.query_and_statement.chat_qas_manager import ChatQueryAndStatementManager
from src.utils.reference_mapping_data.chat.mapping import CHAT_SUBJECT_MAPPING
from src.utils.reference_mapping_data.user.mapping import PRIVILEGE_MAPPING


class ChatService:
    @staticmethod
    async def create_chat(
        session: AsyncSession,
        
        chat_subject: Literal["Заявка", "Контрагент", "Заявка на КП", "Договор"],
        subject_uuid: str,
    ) -> Dict[str, str|int]:
        chat_row: Optional[Chat] = await ChatQueryAndStatementManager.create_chat(
            session=session,
            
            chat_subject_id=CHAT_SUBJECT_MAPPING[chat_subject],
            subject_uuid=subject_uuid,
        )
        if chat_row is None:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Что-то пошло не так при создании Чата!")
        
        chat_info = chat_row
        
        return {
            "id": chat_info.id,
            "chat_subject_id": chat_info.chat_subject_id,
            "subject_uuid": chat_info.subject_uuid,
        }
    
    @staticmethod
    async def send_message(
        session: Optional[AsyncSession],
        
        requester_user_id: int, requester_user_uuid: str, requester_user_privilege: int,
        
        chat_subject: Literal["Заявка", "Контрагент", "Заявка на КП", "Договор"],
        subject_uuid: str,
        message: str,
    ) -> None:
        if len(message) >= 1001:
            raise HTTPException(status_code=status.HTTP_411_LENGTH_REQUIRED, detail="Объём Сообщения не должен превышать 1000 символов!")
        
        chat_id: Optional[int] = await ChatQueryAndStatementManager.check_access(
            session=session,
            
            requester_user_uuid=requester_user_uuid,
            requester_user_privilege=requester_user_privilege,
            chat_subject=chat_subject,
            subject_uuid=subject_uuid,
        )
        
        if chat_id is None:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Чат Вам не доступен для отправки сообщения или же не существует!")
        
        await ChatQueryAndStatementManager.send_message(
            session=session,
            
            requester_user_id=requester_user_id,
            requester_user_uuid=requester_user_uuid,
            requester_user_privilege=requester_user_privilege,
            chat_id=chat_id,
            message=message,
        )
    
    @staticmethod
    async def get_messages(
        session: AsyncSession,
        
        requester_user_uuid: str, requester_user_privilege: int,
        
        chat_subject: Literal["Заявка", "Контрагент", "Заявка на КП", "Договор"],
        subject_uuid: str,
        
        page: Optional[int] = 1,
        page_size: Optional[int] = 100,
    ) -> Dict[str, List[Optional[Message]]|Optional[int]]:
        
        chat_id: Optional[int] = await ChatQueryAndStatementManager.check_access(
            session=session,
            
            requester_user_uuid=requester_user_uuid,
            requester_user_privilege=requester_user_privilege,
            chat_subject=chat_subject,
            subject_uuid=subject_uuid,
        )
        
        if chat_id is None:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Чат Вам не доступен или же не существует!")
        
        result: Dict[str, List[Optional[Message]]|Optional[int]] = await ChatQueryAndStatementManager.get_messages(
            session=session,
            
            chat_id=chat_id,
            
            page=page,
            page_size=page_size,
        )
        
        return result
    
    @staticmethod
    async def delete_messages(
        session: AsyncSession,
        
        requester_user_privilege: int,
        
        list_ids: List[int],
    ) -> None:
        if list_ids is None or len(list_ids) == 0:
            raise HTTPException(status_code=status.HTTP_411_LENGTH_REQUIRED, detail="Для удаления сообщений, нужно указать хотя бы 1 ID!")
        
        if requester_user_privilege != PRIVILEGE_MAPPING["Admin"]:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Вы не можете удалять сообщения. Недостаточно прав!")
        
        await ChatQueryAndStatementManager.delete_messages(
            session=session,
            
            list_ids=list_ids,
        )
