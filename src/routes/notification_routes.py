import datetime
import traceback
from typing import Any, Dict, List, Literal, Optional

from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import JSONResponse

from connection_module import get_async_session
from lifespan import limiter
from security import check_app_auth
from src.schemas.user_schema import ClientState
from src.service.user_service import UserService
from src.service.reference_service import ReferenceService
from src.schemas.notification_schema import FiltersNotifications, NotificationData, OrdersNotifications, CreateNotificationDataSchema, ResponseGetNotifications
from src.models.notification_models import Notification
from src.service.notification_service import NotificationService
from src.query_and_statement.user_qas_manager import UserQueryAndStatementManager as UserQaSM
from src.utils.reference_mapping_data.notification.mapping import NOTIFICATION_SUBJECT_MAPPING
from src.utils.tz_converter import convert_tz


router = APIRouter(
    tags=["Notification"],
)

@router.post(
    "/notify",
    description="""
    Уведомить пользовател/ей системы.
    Админ может делать рассылку или отправлять точечные уведомления.
    
    input: CreateNotificationDataSchema
    """,
    dependencies=[Depends(check_app_auth)],
)
@limiter.limit("3/second")
async def notify(
    request: Request,
    data: CreateNotificationDataSchema,
    
    for_admin: bool = Query(
        ...,
        description="Кому предназначается Уведомление? (true-Админу/false-Пользователю)",
    ),
    subject: Literal["Application", "Legal_entity", "Preliminary_calculation", "Other",] = Query(
        ...,
        description="На какую тему Уведомление? (ЮЛ/Заявка/Прочее/Предварительный расчет)",
    ),
    
    subject_uuid: Optional[str] = Query(
        None,
        description="(None, если subject='Other') UUID сущности, по которой будет отправлено Уведомление.",
        min_length=36,
        max_length=36,
    ),
    recipient_user_uuid: Optional[str] = Query(
        None,
        description="(Опционально для Админа) UUID пользователя-получателя Уведомления. (Если None, то будет сделана рассылка)",
        min_length=36,
        max_length=36,
    ),
    
    is_important: bool = Query(
        False,
        description="Будет ли уведомление отображаться на главном экране?",
    ),
    time_importance_change: Optional[str] = Query(
        None,
        description="Дата и время, когда изменится статус важности на противоположный. (Формат: 'dd.mm.YYYY HH:MM:SS' (следует указывать текущее время, на backend дата-время будет переведена в UTC))",
        example="01.01.2025 00:00:00",
        min_length=19,
        max_length=19,
    ),
    
    token: str = Depends(UserQaSM.get_current_user_data),
    
    session: AsyncSession = Depends(get_async_session),
) -> JSONResponse:
    try:
        user_data: Dict[str, str|int] = token.model_dump()   # Парсинг данных пользователя
        
        await NotificationService.notify(
            session=session,
            
            requester_user_id=user_data["user_id"],
            requester_user_uuid=user_data["user_uuid"],
            requester_user_privilege=user_data["privilege_id"],
            
            subject="Заявка" if subject == "Application" else "ЮЛ" if subject == "Legal_entity" else "Предварительный расчет" if subject == "Preliminary_calculation" else "Прочее",
            subject_uuid=subject_uuid if subject == "Application" else subject_uuid if subject == "Legal_entity" else None,
            for_admin=for_admin,
            data=data.model_dump()["data"],
            recipient_user_uuid=recipient_user_uuid,
            
            is_important=is_important,
            time_importance_change=datetime.datetime.strptime(time_importance_change, "%d.%m.%Y %H:%M:%S") if time_importance_change else None,
        )
        
        return JSONResponse(content={"msg": "Уведомление(я) успешно отправлено(ы)."})
    except AssertionError as e:
        error_message = str(e)
        formatted_traceback = traceback.format_exc()
        
        response_content = {"msg": f"{error_message}\n{formatted_traceback}"}
        return JSONResponse(content=response_content)
    
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        else:
            error_message = str(e)
            formatted_traceback = traceback.format_exc()
            
            log_id = await ReferenceService.create_errlog(
                endpoint="notify",
                params={
                    "data": data.model_dump() if data else data,
                    "for_admin": for_admin,
                    "subject": subject,
                    "subject_uuid": subject_uuid,
                    "recipient_user_uuid": recipient_user_uuid,
                    "is_important": is_important,
                    "time_importance_change": time_importance_change,
                },
                msg=f"{error_message}\n{formatted_traceback}",
                user_uuid=user_data["user_uuid"],
            )
            
            response_content = {"msg": f"ОШИБКА! #{log_id}"}
            return JSONResponse(content=response_content)

@router.post(
    "/get_notifications",
    description="""
    Получение уведомлений.
    
    filter: FiltersNotifications
    order: OrdersNotifications
    state: ClientState
    output: ResponseGetNotifications
    """,
    dependencies=[Depends(check_app_auth)],
)
@limiter.limit("20/second")
async def get_notifications(
    request: Request,
    for_admin: bool = Query(
        True,
        description="Фильтр по назначению Уведомлений. (true-для Админа/false-для Пользователя)"
    ),
    subject: Literal["Application", "Legal_entity", "Preliminary_calculation", "Other", "All"] = Query(
        "All",
        description="Фильтр по теме Уведомлений (ЮЛ/Заявка/Предварительный расчет/Прочее/Все) (Для ЮЛ дополнительно отдает уведомления по его Заявкам)."
    ),
    subject_uuid: Optional[str] = Query(
        None,
        description="(None, если subject='All') Фильтр по UUID сущности по которой отправлены Уведомления (Для ЮЛ дополнительно отдает уведомления по его Заявкам).",
        min_length=36,
        max_length=36
    ),
    initiator_user_uuid: Optional[str] = Query(
        None,
        description="(Опционально) Фильтр по UUID пользователя-отправителя Уведомлений (точное совпадение).",
        min_length=36,
        max_length=36
    ),
    recipient_user_uuid: Optional[str] = Query(
        None,
        description="(Опционально) Фильтр по UUID пользователя-получателя Уведомлений (точное совпадение).",
        min_length=36,
        max_length=36
    ),
    
    page: Optional[int] = Query(
        None,
        description="Пагинация. (По умолчанию - 1)",
        example=1
    ),
    page_size: Optional[int] = Query(
        None,
        description="Размер страницы (По умолчанию - 50).",
        example=50
    ),
    
    filter: Optional[FiltersNotifications] = None,
    order: Optional[OrdersNotifications] = None,
    
    token: str = Depends(UserQaSM.get_current_user_data),
    
    session: AsyncSession = Depends(get_async_session),
    
    client_state: Optional[ClientState] = None,
) -> ResponseGetNotifications:
    try:
        user_data: Dict[str, str|int] = token.model_dump()   # Парсинг данных пользователя
        
        if client_state is None:
            client_state: ClientState = await UserService.get_client_state(
                requester_user_uuid=user_data["user_uuid"],
                requester_user_privilege=user_data["privilege_id"],
                user_uuid=user_data["user_uuid"],
            )
        
        client_state_data: Dict[str, Any] = client_state.model_dump()["data"]
        
        notification_objects: Dict[str, List[Optional[Notification]]|Optional[int]] = await NotificationService.get_notifications(
            session=session,
            
            requester_user_id=user_data["user_id"],
            requester_user_uuid=user_data["user_uuid"],
            requester_user_privilege=user_data["privilege_id"],
            
            for_admin=for_admin,
            subject="Заявка" if subject == "Application" else "ЮЛ" if subject == "Legal_entity" else "Предварительный расчет" if subject == "Preliminary_calculation" else "Прочее" if subject == "Other" else "Все",  # TODO тут надо предусмотреть предварительные расчеты (!)
            subject_uuid=subject_uuid if subject == "Application" else subject_uuid if subject == "Legal_entity" else None,
            initiator_user_uuid=initiator_user_uuid,
            recipient_user_uuid=recipient_user_uuid,
            
            page=page,
            page_size=page_size,
            
            filter=filter,
            order=order,
        )
        
        response_content = ResponseGetNotifications(
            data=[],
            count=0,
            total_records=None,
            total_pages=None,
        )
        
        for notification_object in notification_objects["data"]:
            notification = NotificationData(
                uuid=notification_object.uuid,
                for_admin=notification_object.for_admin,
                subject={v:k for k,v in NOTIFICATION_SUBJECT_MAPPING.items()}[notification_object.subject_id] if notification_object.subject_id else None,
                subject_uuid=notification_object.subject_uuid,
                initiator_user_id=notification_object.initiator_user_id,
                initiator_user_uuid=notification_object.initiator_user_uuid,
                recipient_user_id=notification_object.recipient_user_id,
                recipient_user_uuid=notification_object.recipient_user_uuid,
                data=notification_object.data,
                is_read=notification_object.is_read,
                read_at=convert_tz(notification_object.read_at.strftime("%d.%m.%Y %H:%M:%S UTC"), tz_city=client_state_data.get("tz")) if notification_object.read_at else None,
                is_important=notification_object.is_important,
                time_importance_change=convert_tz(notification_object.time_importance_change.strftime("%d.%m.%Y %H:%M:%S UTC"), tz_city=client_state_data.get("tz")) if notification_object.time_importance_change else None,
                created_at=convert_tz(notification_object.created_at.strftime("%d.%m.%Y %H:%M:%S UTC"), tz_city=client_state_data.get("tz")) if notification_object.created_at else None,
            )
            response_content.data.append(notification)
        
        response_content.count = len(response_content.data)
        response_content.total_records = notification_objects["total_records"]
        response_content.total_pages = notification_objects["total_pages"]
        
        return response_content
    except AssertionError as e:
        error_message = str(e)
        formatted_traceback = traceback.format_exc()
        
        response_content = {"msg": f"{error_message}\n{formatted_traceback}"}
        return JSONResponse(content=response_content)
    
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        else:
            error_message = str(e)
            formatted_traceback = traceback.format_exc()
            
            log_id = await ReferenceService.create_errlog(
                endpoint="get_notifications",
                params={
                    "for_admin": for_admin,
                    "subject": subject,
                    "subject_uuid": subject_uuid,
                    "initiator_user_uuid": initiator_user_uuid,
                    "recipient_user_uuid": recipient_user_uuid,
                    "page": page,
                    "page_size": page_size,
                    "filter": filter.model_dump() if filter else filter,
                    "order": order.model_dump() if order else order,
                },
                msg=f"{error_message}\n{formatted_traceback}",
                user_uuid=user_data["user_uuid"],
            )
            
            response_content = {"msg": f"ОШИБКА! #{log_id}"}
            return JSONResponse(content=response_content)

@router.get(
    "/get_count_notifications",
    description="""
    Получение количества уведомлений по категориям.
    """,
    dependencies=[Depends(check_app_auth)],
)
@limiter.limit("20/second")
async def get_count_notifications(
    request: Request,
    unread_only: Literal["Yes", "No"] = Query(
        "Yes",
        description="Только непрочитанные? ('Yes'/'No')"
    ),
    notification_subject: Literal["Application", "Legal_entity", "Other", "Preliminary_calculation", "All"] = Query(
        "All",
        description="Категория по которой получаем количество Уведомлений. (ЮЛ/Заявки/Прочие/Все)"
    ),
    
    token: str = Depends(UserQaSM.get_current_user_data),
    
    session: AsyncSession = Depends(get_async_session),
) -> JSONResponse:
    try:
        user_data: Dict[str, str|int] = token.model_dump()   # Парсинг данных пользователя
        
        count: int = await NotificationService.get_count_notifications(
            session=session,
            
            requester_user_uuid=user_data["user_uuid"],
            requester_user_privilege=user_data["privilege_id"],
            
            unread_only=unread_only,
            notification_subject=notification_subject,
        )
        
        return JSONResponse(content={"count": count})
    
    except AssertionError as e:
        error_message = str(e)
        formatted_traceback = traceback.format_exc()
        
        response_content = {"msg": f"{error_message}\n{formatted_traceback}"}
        return JSONResponse(content=response_content)
    
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        else:
            error_message = str(e)
            formatted_traceback = traceback.format_exc()
            
            log_id = await ReferenceService.create_errlog(
                endpoint="get_count_notifications",
                params={
                    "unread_only": unread_only,
                    "notification_subject": notification_subject,
                },
                msg=f"{error_message}\n{formatted_traceback}",
                user_uuid=user_data["user_uuid"],
            )
            
            response_content = {"msg": f"ОШИБКА! #{log_id}"}
            return JSONResponse(content=response_content)

@router.put(
    "/read_notifications",
    description="""
    Изменение статуса прочитения у Уведомлений.
    """,
    dependencies=[Depends(check_app_auth)],
)
@limiter.limit("3/second")
async def read_notifications(
    request: Request,
    notification_list_uuid: List[str] = Query(
        [],
        description="Массив UUID Уведомлений, которые нужно пометить прочитанными."
    ),
    
    token: str = Depends(UserQaSM.get_current_user_data),
    
    session: AsyncSession = Depends(get_async_session),
) -> JSONResponse:
    try:
        user_data: Dict[str, str|int] = token.model_dump()   # Парсинг данных пользователя
        
        await NotificationService.read_notifications(
            session=session,
            
            requester_user_uuid=user_data["user_uuid"],
            requester_user_privilege=user_data["privilege_id"],
            
            notification_list_uuid=notification_list_uuid,
        )
        
        return JSONResponse(content={"msg": "Уведомление(я) успешно прочитано(ы)."})
    except AssertionError as e:
        error_message = str(e)
        formatted_traceback = traceback.format_exc()
        
        response_content = {"msg": f"{error_message}\n{formatted_traceback}"}
        return JSONResponse(content=response_content)
    
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        else:
            error_message = str(e)
            formatted_traceback = traceback.format_exc()
            
            log_id = await ReferenceService.create_errlog(
                endpoint="read_notifications",
                params={
                    "notification_list_uuid": notification_list_uuid,
                },
                msg=f"{error_message}\n{formatted_traceback}",
                user_uuid=user_data["user_uuid"],
            )
            
            response_content = {"msg": f"ОШИБКА! #{log_id}"}
            return JSONResponse(content=response_content)

@router.delete(
    "/delete_notifications",
    description="""
    Удаление уведомлений.
    (Пока можно удалить только Админу)
    """,
    dependencies=[Depends(check_app_auth)],
)
@limiter.limit("3/second")
async def delete_notifications(
    request: Request,
    notification_list_uuid: List[str] = Query(
        [],
        description="Массив UUID Уведомлений, которые нужно удалить."
    ),
    
    token: str = Depends(UserQaSM.get_current_user_data),
    
    session: AsyncSession = Depends(get_async_session),
) -> JSONResponse:
    try:
        user_data: Dict[str, str|int] = token.model_dump()   # Парсинг данных пользователя
        
        await NotificationService.delete_notifications(
            session=session,
            
            requester_user_uuid=user_data["user_uuid"],
            requester_user_privilege=user_data["privilege_id"],
            
            notification_list_uuid=notification_list_uuid,
        )
        
        return JSONResponse(content={"msg": "Уведомление(я) успешно удалено(ы)."})
    except AssertionError as e:
        error_message = str(e)
        formatted_traceback = traceback.format_exc()
        
        response_content = {"msg": f"{error_message}\n{formatted_traceback}"}
        return JSONResponse(content=response_content)
    
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        else:
            error_message = str(e)
            formatted_traceback = traceback.format_exc()
            
            log_id = await ReferenceService.create_errlog(
                endpoint="delete_notifications",
                params={
                    "notification_list_uuid": notification_list_uuid,
                },
                msg=f"{error_message}\n{formatted_traceback}",
                user_uuid=user_data["user_uuid"],
            )
            
            response_content = {"msg": f"ОШИБКА! #{log_id}"}
            return JSONResponse(content=response_content)
