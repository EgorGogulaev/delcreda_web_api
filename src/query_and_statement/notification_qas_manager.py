import datetime
from typing import Any, Dict, List, Literal, Optional

from sqlalchemy import and_, delete, func, or_, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from connection_module import SignalConnector
from src.models.user_models import UserContact
from src.models.order.order_models import Order
from src.schemas.notification_schema import FiltersNotifications, OrdersNotifications
from src.models.notification_models import Notification
from src.utils.reference_mapping_data.user.mapping import PRIVILEGE_MAPPING
from src.utils.reference_mapping_data.notification.mapping import NOTIFICATION_SUBJECT_MAPPING


class NotificationQueryAndStatementManager:
    @staticmethod
    async def notify(
        session: AsyncSession,
        
        notification_options: Dict[str, Any],
    ) -> None:
        stmt = (
            insert(Notification)
            .values(
                uuid=notification_options["uuid"],
                for_admin=notification_options["for_admin"],
                subject_id=notification_options["subject_id"],
                subject_uuid=notification_options["subject_uuid"],
                initiator_user_id=notification_options["initiator_user_id"],
                initiator_user_uuid=notification_options["initiator_user_uuid"],
                recipient_user_id=notification_options["recipient_user_id"],
                recipient_user_uuid=notification_options["recipient_user_uuid"],
                data=notification_options["data"],
                
                is_important=notification_options["is_important"],
                time_importance_change=notification_options["time_importance_change"],
            )
        )
        await session.execute(stmt)
        await session.commit()
        
        user_contact_data: Optional[UserContact] = notification_options["user_contact_data"]
        if user_contact_data:
            email_notification = user_contact_data.email_notification
            email = user_contact_data.email
            telegram_notification = user_contact_data.telegram_notification
            telegram = user_contact_data.telegram
            
            notification_ex = None
            if email_notification:
                if email:
                    try:
                        await SignalConnector.notify_email(
                            emails=[email],
                            subject="Уведомление MT",
                            body=notification_options["data"],
                        )
                    except Exception as e:
                        notification_ex = e
            if telegram_notification:
                if telegram:
                    try:
                        await SignalConnector.notify_telegram(
                            tg_user_name=telegram,
                            message=notification_options["data"],
                        )
                    except Exception as e:
                        notification_ex = e
            if notification_ex is not None:
                raise notification_ex
    
    @staticmethod
    async def get_notifications(
        session: AsyncSession,
        
        for_admin: bool,
        subject_id: Optional[int]=None,
        subject_uuid: Optional[str]=None,
        initiator_user_uuid: Optional[str]=None,
        recipient_user_id: Optional[int]=None,
        recipient_user_uuid: Optional[str]=None,
        notification_list_uuid: Optional[List[str]]=None,
        
        page: Optional[int] = None,
        page_size: Optional[int] = None,
        
        filter: Optional[FiltersNotifications] = None,
        order: Optional[OrdersNotifications] = None,
    ) -> Dict[str, List[Optional[Notification]]|Optional[int]]:
        query = (
            select(Notification)
        )
        _filters = [Notification.for_admin == for_admin]
        if notification_list_uuid:
            _filters.append(Notification.uuid.in_(notification_list_uuid))
        
        if subject_id:
            if subject_id == NOTIFICATION_SUBJECT_MAPPING["ЮЛ"] and subject_uuid:  # Если мы фильтруем по ЮЛ и указано конкретное ЮЛ, то...
                query = (  # выводим уведомления о ПР, которые связаны с данным ЮЛ
                    query
                    .select_from(Notification)
                    .outerjoin(Order, Notification.subject_uuid == Order.uuid,)
                )
                _filters.append(
                    or_(
                        and_(
                            Notification.subject_uuid != None,  # noqa: E711
                            Order.legal_entity_uuid == subject_uuid,
                            Notification.subject_id.in_(
                                [
                                    NOTIFICATION_SUBJECT_MAPPING["Поручение"],
                                    NOTIFICATION_SUBJECT_MAPPING["ЮЛ"],
                                ]
                            )
                        ),
                        and_(
                            Notification.subject_id == NOTIFICATION_SUBJECT_MAPPING["ЮЛ"],
                            Notification.subject_uuid == subject_uuid,
                        )
                    )
                )
            
            else:
                _filters.append(Notification.subject_id == subject_id)
        
        if subject_id != NOTIFICATION_SUBJECT_MAPPING["ЮЛ"] and subject_uuid:  # Если мы фильтруем не по ЮЛ и есть фильтр по subject_uuid, то...
            _filters.append(Notification.subject_uuid == subject_uuid)  # добавляем фильтр
        
        if initiator_user_uuid:
            _filters.append(Notification.initiator_user_uuid == initiator_user_uuid)
        if recipient_user_id:
            _filters.append(Notification.recipient_user_id.in_([recipient_user_id, None]))
        if recipient_user_uuid:
            _filters.append(Notification.recipient_user_uuid == recipient_user_uuid)
        
        if filter is not None and filter.filters:
            for filter_item in filter.filters:
                column = getattr(Notification, filter_item.field)
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
                column = getattr(Notification, order_item.field)
                
                # Добавляем условие сортировки в зависимости от направления
                if order_item.direction == "asc":
                    _order_clauses.append(column.asc().nulls_last())
                else:
                    _order_clauses.append(column.desc().nulls_last())
        
        if not _order_clauses:
            _order_clauses.append(Notification.id.asc())
        # ===== КОНЕЦ блока сортировки =====
        
        query = (
            query
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
        if subject_id == NOTIFICATION_SUBJECT_MAPPING["ЮЛ"] and subject_uuid:
            count_query = (
                select(func.count())
                .select_from(Notification)
                .outerjoin(Order, Notification.subject_uuid == Order.uuid,)
                .filter(and_(*_filters))
            )
        else:
            count_query = select(func.count()).select_from(Notification).filter(and_(*_filters))
        
        # compiled_query = query.compile(
        #     dialect=postgresql.dialect(driver='psycopg2'),  # или 'psycopg', если используете psycopg3
        #     compile_kwargs={"literal_binds": True}
        # )
        # print(compiled_query)
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
    async def get_count_notifications(
        session: AsyncSession,
        
        requester_user_uuid: str,
        requester_user_privilege: int,
        
        unread_only: Literal["Yes", "No"],
        notification_subject: Literal["Order", "Legal_entity", "Other", "Preliminary_calculation", "All"],
    ) -> int:
        _filters = []
        
        if requester_user_privilege != PRIVILEGE_MAPPING["Admin"]:
            _filters.append(Notification.for_admin == False)  # noqa: E712
            _filters.append(Notification.recipient_user_uuid.in_([requester_user_uuid, None]))
        else:
            _filters.append(Notification.for_admin == True)  # noqa: E712
        
        if notification_subject == "Order":
            _filters.append(Notification.subject_id == 1)
        elif notification_subject == "Legal_entity":
            _filters.append(Notification.subject_id == 2)
        elif notification_subject == "Preliminary_calculation":
            _filters.append(Notification.subject_id == 3)
        elif notification_subject == "Other":
            _filters.append(Notification.subject_id == 4)  # noqa: E711
        
        if unread_only == "Yes":
            _filters.append(Notification.is_read == False)  # noqa: E712
        
        query = (
            select(func.count())
            .select_from(Notification)
            .filter(*_filters)
        )
        
        result = await session.execute(query)
        return result.scalar()
    
    @staticmethod
    async def read_notifications(
        session: AsyncSession,
        
        notification_list_uuid: List[str],
    ) -> None:
        stmt = (
            update(Notification)
            .filter(Notification.uuid.in_(notification_list_uuid))
            .values(
                is_read=True,
                read_at=datetime.datetime.now(tz=datetime.timezone.utc)
            )
            
        )
        await session.execute(stmt)
        await session.commit()
    
    @staticmethod
    async def delete_notifications(
        session: AsyncSession,
        
        notification_list_uuid: List[str],
    ) -> None:
        stmt = (
            delete(Notification)
            .filter(Notification.uuid.in_(notification_list_uuid))
        )
        await session.execute(stmt)
        await session.commit()
