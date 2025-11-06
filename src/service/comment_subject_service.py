from typing import List, Optional, Tuple

from sqlalchemy.ext.asyncio import AsyncSession

from src.query_and_statement.application.application_qas_manager import ApplicationQueryAndStatementManager
from src.models.comment_subject_models import CommentSubject
from src.query_and_statement.comment_subject_qas_manager import CommentSubjectQueryAndStatementManager
from src.query_and_statement.legal_entity.legal_entity_qas_manager import LegalEntityQueryAndStatementManager
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
            raise AssertionError(f'Вы не можете создавать Комментарии для {"Заявки" if list(COMMENT_SUBJECT_MAPPING)[list(COMMENT_SUBJECT_MAPPING.values()).index(subject_id)] == "Заявка" else "ЮЛ"}!')
        
        is_exists: bool = await CommentSubjectQueryAndStatementManager.check_exist(
            session=session,
            
            subject_id=subject_id,
            subject_uuid=subject_uuid,
        )
        assert not is_exists, f'Комментарий для данного/й {"Заяявки" if list(COMMENT_SUBJECT_MAPPING)[list(COMMENT_SUBJECT_MAPPING.values()).index(subject_id)] == "Заявка" else "ЮЛ"} уже создан, его можно обновить или удалить!'
        
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
            if list(COMMENT_SUBJECT_MAPPING)[list(COMMENT_SUBJECT_MAPPING.values()).index(subject_id)] == "Заявка":
                application_check_access_response_object: Optional[Tuple[int, int, str]] = await ApplicationQueryAndStatementManager.check_access(
                    session=session,
                    
                    requester_user_uuid=requester_user_uuid,
                    requester_user_privilege=requester_user_privilege,
                    application_uuid=subject_uuid,
                )
                assert application_check_access_response_object, "Вы не можете делать Уведомления по данному uuid-Заявки!"
            
            else:
                le_check_access_response_object: Optional[Tuple[int, int, str]] = await LegalEntityQueryAndStatementManager.check_access(
                    session=session,
                    
                    requester_user_uuid=requester_user_uuid,
                    requester_user_privilege=requester_user_privilege,
                    legal_entity_uuid=subject_uuid,
                )
                assert le_check_access_response_object, "Вы не можете делать Уведомления по данному uuid-ЮЛ!"
        
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
        if requester_user_privilege != PRIVILEGE_MAPPING["Admin"]:
            raise AssertionError(f'Вы не можете обновлять Комментарии для {"Заявки" if list(COMMENT_SUBJECT_MAPPING)[list(COMMENT_SUBJECT_MAPPING.values()).index(subject_id)] == "Заявка" else "ЮЛ"}!')
        
        assert new_data != "~", "Нужен какой-то контент для изменения Комментария"
        
        is_exists: bool = await CommentSubjectQueryAndStatementManager.check_exist(
            session=session,
            
            subject_id=subject_id,
            subject_uuid=subject_uuid,
        )
        assert is_exists, f'Комментарий для данного {"Заявки" if list(COMMENT_SUBJECT_MAPPING)[list(COMMENT_SUBJECT_MAPPING.values()).index(subject_id)] == "Заявка" else "ЮЛ"} еще не создан!'
        
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
        if requester_user_privilege != PRIVILEGE_MAPPING["Admin"]:
            raise AssertionError(f'Вы не можете обновлять Комментарии для {"Заявки" if list(COMMENT_SUBJECT_MAPPING)[list(COMMENT_SUBJECT_MAPPING.values()).index(subject_id)] == "Заявка" else "ЮЛ"}!')
        
        is_exists: bool = await CommentSubjectQueryAndStatementManager.check_exist(
            session=session,
            
            subject_id=subject_id,
            subject_uuid=subject_uuid,
        )
        assert is_exists, f'Комментарий для данного {"Заявки" if list(COMMENT_SUBJECT_MAPPING)[list(COMMENT_SUBJECT_MAPPING.values()).index(subject_id)] == "Заявка" else "ЮЛ"} отсутствует!'
        
        await CommentSubjectQueryAndStatementManager.delete_comment_subject(
            session=session,
            
            subject_id=subject_id,
            subject_uuid=subject_uuid,
        )
