import datetime
from typing import Dict, List, Literal, Optional, Tuple

from fastapi import HTTPException
from fastapi import status
from sqlalchemy.ext.asyncio import AsyncSession

from connection_module import SignalConnector
from src.query_and_statement.application.application_qas_manager import ApplicationQueryAndStatementManager
from src.models.user_models import UserContact
from src.schemas.notification_schema import FiltersNotifications, OrdersNotifications
from src.query_and_statement.counterparty.counterparty_qas_manager import CounterpartyQueryAndStatementManager
from src.models.notification_models import Notification
from src.query_and_statement.notification_qas_manager import NotificationQueryAndStatementManager
from src.query_and_statement.user_qas_manager import UserQueryAndStatementManager
from src.utils.reference_mapping_data.user.mapping import PRIVILEGE_MAPPING
from src.utils.reference_mapping_data.notification.mapping import NOTIFICATION_SUBJECT_MAPPING


class NotificationService:
    @staticmethod
    async def notify(
        session: AsyncSession,
        
        requester_user_id: int, requester_user_uuid: str, requester_user_privilege: int,
        
        subject: Literal["Заявка", "Контрагент", "Прочее", "Предварительный расчет"],
        subject_uuid: Optional[str],
        for_admin: bool,
        data: str,
        recipient_user_uuid: Optional[str],
        request_options: Dict[str, str] = {},
        
        is_important: bool = False,
        time_importance_change: Optional[datetime.datetime] = None,
    ) -> None:
        if for_admin is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Не указано для кого это создано: для Пользователей или Админа!")
        
        if not data:
            raise HTTPException(status_code=status.HTTP_411_LENGTH_REQUIRED, detail="Нет тела Уведомления!")
        
        if requester_user_privilege != PRIVILEGE_MAPPING["Admin"]:
            if recipient_user_uuid:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Вы не можете делать Уведомления конкретному Пользователю!")
            
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
        
        recipient_user_id = None
        if recipient_user_uuid:
            recipient_user_id: Optional[int] = await UserQueryAndStatementManager.get_user_id_by_uuid(
                session=session,
                
                uuid=recipient_user_uuid
            )
            if recipient_user_id is None:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Пользователь с указанным UUID не существует!")
        
        user_contact_data = None
        if recipient_user_id:
            user_contact_data: Optional[UserContact] = await UserQueryAndStatementManager.get_user_contact_data(
                session=session,
                
                user_id=recipient_user_id,
                user_uuid=recipient_user_uuid,
            )
            if user_contact_data is None:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Контактные данные пользователя по заданному идентификатору не найдены, обратитесь к администратору!")
        
        new_notification_uuid_coro = await SignalConnector.generate_identifiers(target="Уведомление", count=1)
        new_notification_uuid = new_notification_uuid_coro[0]
        
        notification_options = {
            "uuid": new_notification_uuid,
            "for_admin": for_admin,
            "subject_id": NOTIFICATION_SUBJECT_MAPPING[subject],
            "subject_uuid": subject_uuid,
            "initiator_user_id": requester_user_id,
            "initiator_user_uuid": requester_user_uuid,
            "recipient_user_id": recipient_user_id,
            "recipient_user_uuid": recipient_user_uuid,
            
            "is_important": is_important,
            "time_importance_change": time_importance_change,
            
            "user_contact_data": user_contact_data,
        }
        
        await NotificationQueryAndStatementManager.notify(
            session=session,
            
            data=data,
            notification_options=notification_options,
            request_options=request_options,
        )
    
    @staticmethod
    async def check_user_notification_access(
        session: AsyncSession,
        
        notification_list_uuid: list[str],
        user_uuid: str,
    ) -> bool:
        notifications: Dict[str, List[Optional[Notification]]|Optional[int]] = await NotificationQueryAndStatementManager.get_notifications(
            session=session,
            
            for_admin=False,
            subject_id=None,
            initiator_user_uuid=None,
            recipient_user_id=None,
            recipient_user_uuid=None,
            notification_list_uuid=notification_list_uuid,
        )
        if not notifications["data"]:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Уведомлений по запрошенному списку UUID не существует!")
        
        notification_status_list: List[bool] = [True if notification.recipient_user_uuid == None or notification.recipient_user_uuid == user_uuid else False for notification in notifications["data"]]  # noqa: E711
        if all(notification_status_list):
            return True
        else:
            return False
    
    @staticmethod
    async def get_notifications(
        session: AsyncSession,
        
        requester_user_id: int,
        requester_user_uuid: str,
        requester_user_privilege: int,
        
        for_admin: bool,
        subject: Literal["Заявка", "Контрагент", "Прочее", "Предварительный расчет", "Все"],
        subject_uuid: Optional[str],
        initiator_user_uuid: Optional[str],
        recipient_user_uuid: Optional[str],
        
        page: Optional[int] = None,
        page_size: Optional[int] = None,
        
        filter: Optional[FiltersNotifications] = None,
        order: Optional[OrdersNotifications] = None,
    ) -> Dict[str, List[Optional[Notification]]|Optional[int]]:
        if page or page_size:
            if (isinstance(page, int) and page <= 0) or (isinstance(page_size, int) and page_size <= 0):
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Не корректное разделение на страницы, запрошенных данных!")
        if recipient_user_uuid:
            if recipient_user_uuid and requester_user_privilege != PRIVILEGE_MAPPING["Admin"]:
                if recipient_user_uuid != requester_user_uuid:
                    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Вы не можете просмотреть Уведомления других Пользователей!")
            
            recipient_user_id: Optional[int] = await UserQueryAndStatementManager.get_user_id_by_uuid(
                session=session,
                
                uuid=recipient_user_uuid,
            )
            if recipient_user_id is None:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Пользователь-получатель уведомления с указанным UUID не существует!")
        else:
            recipient_user_uuid = None
        
        if initiator_user_uuid:
            initiator_user_id: Optional[int] = await UserQueryAndStatementManager.get_user_id_by_uuid(
                session=session,
                
                uuid=initiator_user_uuid,
            )
            if initiator_user_id is None:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Пользователь-инициатор уведомления с указанным UUID не существует!")
        
        if for_admin and requester_user_privilege != PRIVILEGE_MAPPING["Admin"]:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Вы не можете просмотреть Уведомления для Администраторов!")
        
        if requester_user_privilege != PRIVILEGE_MAPPING["Admin"]:  # TODO тут надо предусмотреть предварительные расчеты (только Админы) (!)
            if subject_uuid:
                if subject == "Заявка":
                    application_check_access_response_object: Optional[Tuple[int, int, str]] = await ApplicationQueryAndStatementManager.check_access(
                        session=session,
                        
                        requester_user_uuid=requester_user_uuid,
                        requester_user_privilege=requester_user_privilege,
                        application_uuid=subject_uuid,
                    )
                    if application_check_access_response_object is None:
                        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Вы не можете просмотреть Уведомления по данной Заявке!")
                
                elif subject == "Контрагент":
                    counterparty_check_access_response_object: Optional[Tuple[int, int, int, str]] = await CounterpartyQueryAndStatementManager.check_access(
                        session=session,
                        
                        requester_user_uuid=requester_user_uuid,
                        requester_user_privilege=requester_user_privilege,
                        counterparty_uuid=subject_uuid,
                    )
                    if counterparty_check_access_response_object is None:
                        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Вы не можете просмотреть Уведомления по данному Контрагенту!")
        
        notifications: Dict[str, List[Optional[Notification]]|Optional[int]] = await NotificationQueryAndStatementManager.get_notifications(
            session=session,
            
            for_admin=for_admin,
            subject_id=NOTIFICATION_SUBJECT_MAPPING[subject] if subject != "Все" else None,
            subject_uuid=subject_uuid,
            initiator_user_uuid=initiator_user_uuid,
            recipient_user_id=requester_user_id if requester_user_privilege != PRIVILEGE_MAPPING["Admin"] else None,
            recipient_user_uuid=recipient_user_uuid,
            
            page=page,
            page_size=page_size,
            
            filter=filter,
            order=order,
        )
        
        return notifications
    
    @staticmethod
    async def get_count_notifications(
        session: AsyncSession,
        
        requester_user_uuid: str,
        requester_user_privilege: int,
        
        unread_only: Literal["Yes", "No"],
        notification_subject: Literal["Application", "Counterparty", "Other", "Preliminary_calculation", "All"],
    ) -> int:
        count_unread_notifications = await NotificationQueryAndStatementManager.get_count_notifications(
            session=session,
            
            requester_user_uuid=requester_user_uuid,
            requester_user_privilege=requester_user_privilege,
            
            unread_only=unread_only,
            notification_subject=notification_subject,
        )
        
        return count_unread_notifications
    
    @staticmethod
    async def read_notifications(
        session: AsyncSession,
        
        requester_user_uuid: str,
        requester_user_privilege: int,
        
        notification_list_uuid: List[str],
    ) -> None:
        if not notification_list_uuid:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Ничего не передано в список UUID-Уведомлений на изменение статуса прочтения!")
        
        if requester_user_privilege != PRIVILEGE_MAPPING["Admin"]:
            is_accessed: bool = await NotificationService.check_user_notification_access(
                session=session,
                
                notification_list_uuid=notification_list_uuid,
                user_uuid=requester_user_uuid
            )
            if is_accessed is False:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Вы не можете пометить прочитанными Уведомления других Пользователей!")
        
        await NotificationQueryAndStatementManager.read_notifications(
            session=session,
            
            notification_list_uuid=notification_list_uuid,
        )
    
    @staticmethod
    async def delete_notifications(
        session: AsyncSession,
        
        requester_user_uuid: str,
        requester_user_privilege: int,
        
        notification_list_uuid: List[str],
    ) -> None:
        if not notification_list_uuid:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Ничего не передано в список UUID-Уведомлений к удалению!")
        
        if requester_user_privilege != PRIVILEGE_MAPPING["Admin"]:
            is_accessed: bool = await NotificationService.check_user_notification_access(
                session=session,
                
                notification_list_uuid=notification_list_uuid,
                user_uuid=requester_user_uuid
            )
            if is_accessed is False:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Вы не можете удалить Уведомления других Пользователей!")
        
        await NotificationQueryAndStatementManager.delete_notifications(
            session=session,
            
            notification_list_uuid=notification_list_uuid,
        )
