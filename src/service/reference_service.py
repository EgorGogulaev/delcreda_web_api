import asyncio
from typing import Dict, List, Literal, Optional

from fastapi import HTTPException
from fastapi import status
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from config import IS_PROD, TG_CHAT_ID
from connection_module import RedisConnector, async_session_maker
from src.schemas.reference_schema import FiltersServiceNote, OrdersServiceNote
from src.models.reference_models import ServiceNote
from src.query_and_statement.reference_qas_manager import ReferenceQueryAndStatementManager
from src.query_and_statement.user_qas_manager import UserQueryAndStatementManager
from src.utils.reference_mapping_data.user.mapping import PRIVILEGE_MAPPING, SERVICE_NOTE_SUBJECT_MAPPING
from src.utils.tg_send_message import send_telegram_message


class ReferenceService:
    @staticmethod
    async def check_uuid(
        session: AsyncSession,
        
        requester_user_uuid: str,
        requester_user_privilege: int,
        
        uuid: str,
        object: Literal["User", "Directory", "Document", "Notification", "Counterparty", "Application", "CommercialProposal"]
    ) -> bool:
        if requester_user_privilege != PRIVILEGE_MAPPING["Admin"]:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Вы не являетесь Администратором!")
        
        match object:
            case "User":
                return await UserQueryAndStatementManager.check_user_account_by_field_value(
                    session=session,
                    
                    value=uuid,
                    field_type="uuid",
                )
            case "Directory":
                return await ReferenceQueryAndStatementManager.check_uuid(
                    session=session,
                    
                    uuid=uuid,
                    object_type="Directory",
                )
            case "Document":
                return await ReferenceQueryAndStatementManager.check_uuid(
                    session=session,
                    
                    uuid=uuid,
                    object_type="Document",
                )
            case "Notification":
                return await ReferenceQueryAndStatementManager.check_uuid(
                    session=session,
                    
                    uuid=uuid,
                    object_type="Notification",
                )
            case "Counterparty":
                return await ReferenceQueryAndStatementManager.check_uuid(
                    session=session,
                    
                    uuid=uuid,
                    object_type="Legal entity",
                )
            case "Application":
                return await ReferenceQueryAndStatementManager.check_uuid(
                    session=session,
                    
                    uuid=uuid,
                    object_type="Application",
                )
            case "CommercialProposal":
                return await ReferenceQueryAndStatementManager.check_uuid(
                    session=session,
                    
                    uuid=uuid,
                    object_type="CommercialProposal"
                )
            case _:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Нужно указать корректный объект для проверки UUID!")
    
    @classmethod
    async def create_service_note(
        cls,
        
        session: AsyncSession,
        
        requester_user_id: int,
        requester_user_uuid: str,
        requester_user_privilege: int,
        
        subject: Literal["Заявка", "Контрагент", "Документ", "Пользователь", "Заявка на КП"],
        subject_uuid: str,
        title: str,
        data: Optional[str]=None,
    ) -> None:
        if requester_user_privilege != PRIVILEGE_MAPPING["Admin"]:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Вы не являетесь Администратором!")
        if not all([subject, subject_uuid, title]):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Для создания служебной заметки обязательными являются: сущность к чему прикрепляется, UUID-сущности и заголовок заметки!")
        if subject == "Заявка":
            is_exist: bool = cls.check_uuid(
                session=session,
                
                requester_user_uuid=requester_user_uuid,
                requester_user_privilege=requester_user_privilege,
                uuid=subject_uuid,
                object="Application",
            )
        elif subject == "Контрагент":
            is_exist: bool = cls.check_uuid(
                session=session,
                
                requester_user_uuid=requester_user_uuid,
                requester_user_privilege=requester_user_privilege,
                uuid=subject_uuid,
                object="Counterparty",
            )
        elif subject == "Документ":
            is_exist: bool = cls.check_uuid(
                session=session,
                
                requester_user_uuid=requester_user_uuid,
                requester_user_privilege=requester_user_privilege,
                uuid=subject_uuid,
                object="Document",
            )
        elif subject == "Пользователь":
            is_exist: bool = cls.check_uuid(
                session=session,
                
                requester_user_uuid=requester_user_uuid,
                requester_user_privilege=requester_user_privilege,
                uuid=subject_uuid,
                object="User",
            )
        elif subject == "Заявка на КП":
            is_exist: bool = cls.check_uuid(
                session=session,
                
                requester_user_uuid=requester_user_uuid,
                requester_user_privilege=requester_user_privilege,
                uuid=subject_uuid,
                object="User",
            )
        if is_exist is False:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"{subject} с таким UUID'ом не существует!")
        
        try:
            await ReferenceQueryAndStatementManager.create_service_note(
                session=session,
                
                service_note_data={
                    "subject_id": SERVICE_NOTE_SUBJECT_MAPPING[subject],
                    "subject_uuid": subject_uuid,
                    "creator_id": requester_user_id,
                    "creator_uuid": requester_user_uuid,
                    "title": title,
                    "data": data,
                }
            )
        except IntegrityError:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Дублирование заголовка служебной заметки!")
    
    @staticmethod
    async def get_service_notes(
        session: AsyncSession,
        
        requester_user_id: int,
        requester_user_uuid: str,
        requester_user_privilege: int,
        
        subject: Optional[Literal["Заявка", "Контрагент", "Документ", "Пользователь", "Заявка на КП"]],
        subject_uuid: Optional[str],
        
        page: Optional[int] = None,
        page_size: Optional[int] = None,
        
        filter: Optional[FiltersServiceNote] = None,
        order: Optional[OrdersServiceNote] = None,
    ) -> Dict[str, List[Optional[ServiceNote]]|Optional[int]]:
        if requester_user_privilege != PRIVILEGE_MAPPING["Admin"]:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Вы не являетесь Администратором!")
        
        if page or page_size:
            if (isinstance(page, int) and page <= 0) or (isinstance(page_size, int) and page_size <= 0):
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Не корректное разделение на страницы, запрошенных данных!")
        
        service_notes: Dict[str, List[Optional[ServiceNote]]|Optional[int]] = await ReferenceQueryAndStatementManager.get_service_notes(
            session=session,
            
            subject_id=SERVICE_NOTE_SUBJECT_MAPPING[subject] if subject else None,
            subject_uuid=subject_uuid,
            
            page=page,
            page_size=page_size,
            
            filter=filter,
            order=order,
        )
        
        return service_notes
    
    @staticmethod
    async def update_service_note(
        session: AsyncSession,
        
        requester_user_id: int,
        requester_user_uuid: str,
        requester_user_privilege: int,
        
        service_note_id: int,
        new_title: str = "~",
        new_data: Optional[str] = "~",
    ) -> None:
        if requester_user_privilege != PRIVILEGE_MAPPING["Admin"]:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Вы не являетесь Администратором!")
        
        if not service_note_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Для обновления слуебной записки необходимо указать её идентификатор!")
        if new_title is None:
            raise HTTPException(status_code=status.HTTP_411_LENGTH_REQUIRED, detail="Заголовок не может быть пустым!")
        
        if new_title == "~" and new_data == "~":
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Нужно указать что будет изменено (заголовок и/или данные) в служебной заметке!")
        
        await ReferenceQueryAndStatementManager.update_service_note(
            session=session,
            
            creator_id=requester_user_id,
            creator_uuid=requester_user_uuid,
            
            service_note_id=service_note_id,
            new_title=new_title,
            new_data=new_data,
        )
    
    @staticmethod
    async def delete_service_notes(
        session: AsyncSession,
        
        requester_user_id: int,
        requester_user_uuid: str,
        requester_user_privilege: int,
        
        service_notes_ids: Optional[List[int]],
        subject_id: Optional[int],
        subject_uuid: Optional[str],
    ) -> None:
        if requester_user_privilege != PRIVILEGE_MAPPING["Admin"]:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Вы не являетесь Администратором!")
        
        if (service_notes_ids is None or len(service_notes_ids) == 0) and not subject_id and not subject_uuid:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Для удаления служебных заметок нужно указать либо субъект, либо конкретный идентификатор служебной заметки!")
        
        await ReferenceQueryAndStatementManager.delete_service_notes(
            session=session,
            
            service_notes_ids=service_notes_ids,
            subject_id=subject_id,
            subject_uuid=subject_uuid,
        )
    
    
    @staticmethod
    async def create_errlog(
        endpoint: str,
        
        params: Optional[Dict],
        msg: Optional[str],
        
        user_uuid: str,
    ) -> int:
        log_id: int = await ReferenceQueryAndStatementManager.create_errlog(
            endpoint=endpoint,
            params=params,
            msg=msg,
            user_uuid=user_uuid,
        )
        if IS_PROD:
            await send_telegram_message(
                chat_id=TG_CHAT_ID,
                message=f"ОШИБКА! #{log_id}\n\n\n{msg}\n_______________________________"
            )
        
        return log_id
    
    @staticmethod
    async def healthcheck() -> Dict[str, bool]:
        healthcheck_result = {}
        
        # Redis
        try:
            async with RedisConnector.get_async_redis_session() as redis_session:
                await asyncio.wait_for(redis_session.ping(), timeout=15)
                healthcheck_result["redis"] = True
        except:
            healthcheck_result["redis"] = False
        
        # PostgreSQL  
        try:
            async with async_session_maker() as postgres_session:
                await asyncio.wait_for(postgres_session.execute(text("SELECT 1")), timeout=15)
                healthcheck_result["postgres"] = True
        except:
            healthcheck_result["postgres"] = False
        
        return healthcheck_result
    
    
    @staticmethod
    async def _test(
        session: AsyncSession,
        
        requester_user_privilege: int
    ):
        if requester_user_privilege != PRIVILEGE_MAPPING["Admin"]:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Вы не являетесь Администратором!")
        await ReferenceQueryAndStatementManager._test(session=session)
        ...
