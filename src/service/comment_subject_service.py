from typing import List, Optional, Tuple

from fastapi import HTTPException
from fastapi import status
from sqlalchemy.ext.asyncio import AsyncSession

from src.query_and_statement.application.application_qas_manager import ApplicationQueryAndStatementManager
from src.models.comment_subject_models import CommentSubject
from src.query_and_statement.comment_subject_qas_manager import CommentSubjectQueryAndStatementManager
from src.query_and_statement.counterparty.counterparty_qas_manager import CounterpartyQueryAndStatementManager
from src.utils.reference_mapping_data.user.mapping import PRIVILEGE_MAPPING
from src.utils.reference_mapping_data.comment_subject.mapping import COMMENT_SUBJECT_MAPPING


class CommentSubjectService:
    @staticmethod
    async def create_comment_subject(
        session: AsyncSession,
        
        requester_user_uuid: str,
        requester_user_privilege: int,
        
        subject_id: int,
        subject_uuid: str,
        
        data: Optional[str],
    ) -> None:
        if requester_user_privilege != PRIVILEGE_MAPPING["Admin"]:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f'Вы не можете создавать Комментарии для {"Заявки" if list(COMMENT_SUBJECT_MAPPING)[list(COMMENT_SUBJECT_MAPPING.values()).index(subject_id)] == "Заявка" else "Контрагент"}!')
        
        is_exists: bool = await CommentSubjectQueryAndStatementManager.check_exist(
            session=session,
            
            subject_id=subject_id,
            subject_uuid=subject_uuid,
        )
        if is_exists:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f'Комментарий для данного/й {"Заявки" if list(COMMENT_SUBJECT_MAPPING)[list(COMMENT_SUBJECT_MAPPING.values()).index(subject_id)] == "Заявка" else "Контрагента"} уже создан, его можно обновить или удалить!')
        
        await CommentSubjectQueryAndStatementManager.create_comment_subject(
            session=session,
            
            requester_user_uuid=requester_user_uuid,
            subject_id=subject_id,
            subject_uuid=subject_uuid,
            data=data,
        )
    
    @staticmethod
    async def get_comment_subject(
        session: AsyncSession,
        
        requester_user_uuid: str,
        requester_user_privilege: int,
        
        subject_id: int,
        subject_uuid: str,
    ) -> List[Optional[CommentSubject]]:
        if requester_user_privilege != PRIVILEGE_MAPPING["Admin"]:
            subject = {v: k for k, v in COMMENT_SUBJECT_MAPPING.items()}[subject_id]
            
            if subject == "Заявка":
                application_check_access_response_object: Optional[Tuple[int, int, str]] = await ApplicationQueryAndStatementManager.check_access(
                    session=session,
                    
                    requester_user_uuid=requester_user_uuid,
                    requester_user_privilege=requester_user_privilege,
                    application_uuid=subject_uuid,
                )
                if application_check_access_response_object is None:
                    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Вы не можете делать Уведомления по данному UUID-Заявки!")
            
            elif subject == "Контрагент":
                counterparty_check_access_response_object: Optional[Tuple[int, int, int, str]] = await CounterpartyQueryAndStatementManager.check_access(
                    session=session,
                    
                    requester_user_uuid=requester_user_uuid,
                    requester_user_privilege=requester_user_privilege,
                    counterparty_uuid=subject_uuid,
                )
                if counterparty_check_access_response_object is None:
                    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Вы не можете делать Уведомления по данному UUID-Контрагента!")
        
        comment: List[Optional[CommentSubject]] = await CommentSubjectQueryAndStatementManager.get_comment_subject(
            session=session,
            
            subject_id=subject_id,
            subject_uuid=subject_uuid,
        )
        
        return comment
    
    @staticmethod
    async def update_comment_subject(
        session: AsyncSession,
        
        requester_user_uuid: str,
        requester_user_privilege: int,
        
        subject_id: int,
        subject_uuid: str,
        
        new_data: Optional[str] = "~",
    ) -> None:
        subject = {v: k for k, v in COMMENT_SUBJECT_MAPPING.items()}[subject_id]
        if requester_user_privilege != PRIVILEGE_MAPPING["Admin"]:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f'Вы не можете обновлять Комментарии для {"Заявки" if subject == "Заявка" else "Контрагента"}!')
        
        if new_data == "~":
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Нужен какой-то контент для изменения Комментария!")
        
        is_exists: bool = await CommentSubjectQueryAndStatementManager.check_exist(
            session=session,
            
            subject_id=subject_id,
            subject_uuid=subject_uuid,
        )
        if is_exists is False:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f'Комментарий для {"Заявки" if subject == "Заявка" else "Контрагента"} еще не создан!')
        
        await CommentSubjectQueryAndStatementManager.update_comment_subject(
            session=session,
            
            requester_user_uuid=requester_user_uuid,
            subject_id=subject_id,
            subject_uuid=subject_uuid,
            new_data=new_data,
        )
    
    @staticmethod
    async def delete_comment_subject(
        session: AsyncSession,
        
        requester_user_uuid: str,
        requester_user_privilege: int,
        
        subject_id: int,
        subject_uuid: str,
    ) -> None:
        subject = {v: k for k, v in COMMENT_SUBJECT_MAPPING.items()}[subject_id]
        
        if requester_user_privilege != PRIVILEGE_MAPPING["Admin"]:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f'Вы не можете обновлять Комментарии для {"Заявки" if subject == "Заявка" else "Контрагента"}!')
        
        is_exists: bool = await CommentSubjectQueryAndStatementManager.check_exist(
            session=session,
            
            subject_id=subject_id,
            subject_uuid=subject_uuid,
        )
        if is_exists is False:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f'Комментарий для {"Заявки" if subject == "Заявка" else "Контрагента"} отсутствует!')
        
        await CommentSubjectQueryAndStatementManager.delete_comment_subject(
            session=session,
            
            subject_id=subject_id,
            subject_uuid=subject_uuid,
        )
