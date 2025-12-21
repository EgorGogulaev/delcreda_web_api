import traceback
from typing import Any, Dict, List, Literal, Optional

from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import JSONResponse

from connection_module import get_async_session
from lifespan import limiter
from security import check_app_auth
from src.service.user_service import UserService
from src.schemas.user_schema import ClientState
from src.models.reference_models import ServiceNote
from src.schemas.reference_schema import FiltersServiceNote, OrdersServiceNote, ResponseGetServiceNotes, ServiceNoteData
from src.service.reference_service import ReferenceService
from src.query_and_statement.user_qas_manager import UserQueryAndStatementManager as UserQaSM
from src.utils.reference_mapping_data.app.app_mapping_data import COUNTRY_MAPPING_RUSSIA
from src.utils.reference_mapping_data.user.mapping import SERVICE_NOTE_SUBJECT_MAPPING
from src.utils.tz_converter import convert_tz


router = APIRouter(
    tags=["Reference"],
)

@router.get(
    "/check_uuid",
    description="""
    Проверка, занят ли UUID для определенной сущности в приложении.
    Нужно для сторонней интеграции с другими системами.
    (НЕ ИСПОЛЬЗУЕТСЯ в React-приложении)
    """,
    dependencies=[Depends(check_app_auth)],
)
@limiter.limit("30/second")
async def check_uuid(
    request: Request,
    object: Literal["User", "Directory", "Document", "Notification", "Legal entity", "Application"] = Query(
        "User",
        description="UUID какой сущности проверяется?"
    ),
    uuid: str = Query(
        ...,
        description="UUID к проверке."
    ),
    
    token: str = Depends(UserQaSM.get_current_user_data),
    
    session: AsyncSession = Depends(get_async_session),
) -> JSONResponse:    
    try:
        user_data: Dict[str, str|int] = token.model_dump()   # Парсинг данных пользователя
        
        result: bool = await ReferenceService.check_uuid(
            session=session,
            
            requester_user_uuid=user_data["user_uuid"],
            requester_user_privilege=user_data["privilege_id"],
            
            uuid=uuid,
            object=object
        )
        
        return JSONResponse(content={"exists": result})
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
                endpoint="check_uuid",
                params={
                    "object": object,
                    "uuid": uuid,
                },
                msg=f"{error_message}\n{formatted_traceback}",
                user_uuid=user_data["user_uuid"],
            )
            
            response_content = {"msg": f"ОШИБКА! #{log_id}"}
            return JSONResponse(content=response_content)
    finally:
        await session.rollback()

@router.post(
    "/create_service_note",
    description="""
    Создание служебной заметки по Заявке/Контрагент/Документу/Пользователю.
    """,
    dependencies=[Depends(check_app_auth)],
)
@limiter.limit("30/second")
async def create_service_note(
    request: Request,
    subject: Literal[
        "Заявка",
        "Контрагент",
        "Документ",
        "Пользователь",
    ] = Query(
        "Заявка",
        description="К чему будет прикреплена служебная заметка?",
    ),
    subject_uuid: str = Query(
        ...,
        description="UUID-сущности, к которой будет прикреплена служебная заметка.",
        min_length=36,
        max_length=36,
    ),
    title: str = Query(
        ...,
        description="Уникальный(для отдельной сущности - Заявка, Контрагент, Документ, Пользователь) заголовок служебной заметки.",
        max_length=256,
    ),
    data: Optional[str] = Query(
        None,
        description="Контент служебной заметки.",
        max_length=512,
    ),
    
    token: str = Depends(UserQaSM.get_current_user_data),
    
    session: AsyncSession = Depends(get_async_session),
) -> JSONResponse:
    try:
        user_data: Dict[str, str|int] = token.model_dump()   # Парсинг данных пользователя
        
        await ReferenceService.create_service_note(
            session=session,
            
            requester_user_id=user_data["user_id"],
            requester_user_uuid=user_data["user_uuid"],
            requester_user_privilege=user_data["privilege_id"],
            
            subject=subject,
            subject_uuid=subject_uuid,
            title=title,
            data=data,
        )
        
        response_content = {"msg": "Служебная заметка успешно создана."}
        return JSONResponse(content=response_content)
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
                endpoint="create_service_note",
                params={
                    "subject": subject,
                    "subject_uuid": subject_uuid,
                    "title": title,
                    "data": data,
                },
                msg=f"{error_message}\n{formatted_traceback}",
                user_uuid=user_data["user_uuid"],
            )
            
            response_content = {"msg": f"ОШИБКА! #{log_id}"}
            return JSONResponse(content=response_content)
    finally:
        await session.rollback()

@router.post(
    "/get_service_notes",
    description="""
    Получение служебных заметок по Заявке/Контрагент/Документу/Пользователю.
    
    filter: FiltersServiceNote
    order: OrdersServiceNote
    state: ClientState
    output: ResponseGetServiceNotes
    """,
    dependencies=[Depends(check_app_auth)],
)
@limiter.limit("30/second")
async def get_service_notes(
    request: Request,
    service_notes_ids: Optional[List[int]] = Query(
        None,
        description="(Опционально) Фильтр по ID служебных заметок."
    ),
    subject: Optional[Literal[
        "Заявка",
        "Контрагент",
        "Документ",
        "Пользователь",
        "Заявка на КП",
    ]] = Query(
        None,
        description="(Опционально) Фильтр по тому, к чему прикреплены служебные заметки.",
    ),
    subject_uuid: Optional[str] = Query(
        None,
        description="(Опционально) Фильтр по UUID-сущности, к которой прикреплены служебные заметки.",
        min_length=36,
        max_length=36,
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
    
    filter: Optional[FiltersServiceNote] = None,
    order: Optional[OrdersServiceNote] = None,
    
    token: str = Depends(UserQaSM.get_current_user_data),
    
    session: AsyncSession = Depends(get_async_session),
    
    client_state: Optional[ClientState] = None,
) -> ResponseGetServiceNotes:
    try:
        user_data: Dict[str, str|int] = token.model_dump()   # Парсинг данных пользователя
        
        if client_state is None:
            client_state: ClientState = await UserService.get_client_state(
                requester_user_uuid=user_data["user_uuid"],
                requester_user_privilege=user_data["privilege_id"],
                user_uuid=user_data["user_uuid"],
            )
        client_state_data: Dict[str, Any] = client_state.model_dump()
        
        service_notes_objects: Dict[str, List[Optional[ServiceNote]]|Optional[int]] = await ReferenceService.get_service_notes(
            session=session,
            
            requester_user_id=user_data["user_id"],
            requester_user_uuid=user_data["user_uuid"],
            requester_user_privilege=user_data["privilege_id"],
            
            subject=subject,
            subject_uuid=subject_uuid,
            
            page=page,
            page_size=page_size,
            
            filter=filter,
            order=order,
        )
        
        response_content = ResponseGetServiceNotes(
            data=[],
            count=0,
            total_records=None,
            total_pages=None,
        )
        
        for service_note_object in service_notes_objects["data"]:
            service_note_object: ServiceNote = service_note_object
            service_note = ServiceNoteData(
                id=service_note_object.id,
                subject={v:k for k,v in SERVICE_NOTE_SUBJECT_MAPPING.items()}[service_note_object.subject_id] if service_note_object.subject_id else None,
                subject_uuid=service_note_object.subject_uuid,
                creator_id=service_note_object.creator_id,
                creator_uuid=service_note_object.creator_uuid,
                title=service_note_object.title,
                data=service_note_object.data,
                updated_at=convert_tz(service_note_object.updated_at.strftime("%d.%m.%Y %H:%M:%S UTC"), tz_city=client_state_data["data"].get("tz")) if service_note_object.updated_at else None,
                created_at=convert_tz(service_note_object.created_at.strftime("%d.%m.%Y %H:%M:%S UTC"), tz_city=client_state_data["data"].get("tz")) if service_note_object.created_at else None,
            )
            response_content.data.append(service_note)
        
        response_content.count = len(response_content.data)
        response_content.total_records = service_notes_objects["total_records"]
        response_content.total_pages = service_notes_objects["total_pages"]
        
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
                endpoint="get_service_notes",
                params={
                    "service_notes_ids": service_notes_ids,
                    "subject": subject,
                    "subject_uuid": subject_uuid,
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
    finally:
        await session.rollback()

@router.put(
    "/update_service_note",
    description="""
    Обновление данных служебной заметки.
    """,
    dependencies=[Depends(check_app_auth)],
)
@limiter.limit("30/second")
async def update_service_note(
    request: Request,
    service_note_id: int = Query(
        ...,
        description="ID служебной заметки к обновлению.",
    ),
    new_title: str = Query(
        "~",
        description='Новое уникальное(в рамках сущности - Заявки/Контрагент/Документ/Пользователь) значение для заголовка служебной заметки ("~" - оставить текущее значение).',
    ),
    new_data: str = Query(
        "~",
        description='Новый контент служебной заметки ("~" - оставить текущие данные).',
    ),
    
    token: str = Depends(UserQaSM.get_current_user_data),
    
    session: AsyncSession = Depends(get_async_session),
) -> JSONResponse:
    try:
        user_data: Dict[str, str|int] = token.model_dump()   # Парсинг данных пользователя
        
        await ReferenceService.update_service_note(
            session=session,
            
            requester_user_id=user_data["user_id"],
            requester_user_uuid=user_data["user_uuid"],
            requester_user_privilege=user_data["privilege_id"],
            
            service_note_id=service_note_id,
            new_title=new_title,
            new_data=new_data,
        )
        
        response_content = {"msg": "Служебная заметка успешно обновлена."}
        return JSONResponse(content=response_content)
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
                endpoint="update_service_note",
                params={
                    "service_note_id": service_note_id,
                    "new_title": new_title,
                    "new_data": new_data,
                },
                msg=f"{error_message}\n{formatted_traceback}",
                user_uuid=user_data["user_uuid"],
            )
            
            response_content = {"msg": f"ОШИБКА! #{log_id}"}
            return JSONResponse(content=response_content)
    finally:
        await session.rollback()

@router.delete(
    "/delete_service_notes",
    description="""
    Удаление служебных заметок по фильтрам.
    """,
    dependencies=[Depends(check_app_auth)],
)
@limiter.limit("30/second")
async def delete_service_notes(
    request: Request,
    service_notes_ids: Optional[List[int]] = Query(
        None,
        description="(Опционально) Фильтр по ID служебных заметок к удалению."
    ),
    subject: Optional[Literal[
        "Заявка",
        "Контрагент",
        "Документ",
        "Пользователь",
        "Заявка на КП",
    ]] = Query(
        None,
        description="(Опционально) Фильтр по тому, к чему прикреплены служебные заметки.",
    ),
    subject_uuid: Optional[str] = Query(
        None,
        description="(Опционально) Фильтр по UUID-сущности, к которой прикреплены служебные заметки.",
        min_length=36,
        max_length=36,
    ),
    
    token: str = Depends(UserQaSM.get_current_user_data),
    
    session: AsyncSession = Depends(get_async_session),
) -> JSONResponse:
    try:
        user_data: Dict[str, str|int] = token.model_dump()   # Парсинг данных пользователя
        
        await ReferenceService.delete_service_notes(
            session=session,
            
            requester_user_id=user_data["user_id"],
            requester_user_uuid=user_data["user_uuid"],
            requester_user_privilege=user_data["privilege_id"],
            
            service_notes_ids=service_notes_ids,
            subject_id=SERVICE_NOTE_SUBJECT_MAPPING[subject] if subject else None,
            subject_uuid=subject_uuid,
        )
        
        response_content = {"msg": "Служебные заметки успешно удалены."}
        return JSONResponse(content=response_content)
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
                endpoint="delete_service_notes",
                params={
                    "service_notes_ids": service_notes_ids,
                    "subject": subject,
                    "subject_uuid": subject_uuid,
                },
                msg=f"{error_message}\n{formatted_traceback}",
                user_uuid=user_data["user_uuid"],
            )
            
            response_content = {"msg": f"ОШИБКА! #{log_id}"}
            return JSONResponse(content=response_content)
    finally:
        await session.rollback()


@router.get("/get_countries", dependencies=[Depends(check_app_auth)],)
@limiter.limit("30/second")
async def get_countries(
    request: Request,
    token: str = Depends(UserQaSM.get_current_user_data),
) -> JSONResponse:
    return JSONResponse(
        content=COUNTRY_MAPPING_RUSSIA
    )

@router.get("/test", dependencies=[Depends(check_app_auth)],)
@limiter.limit("1/second")
async def test(
    request: Request,
    token: str = Depends(UserQaSM.get_current_user_data),
    session: AsyncSession = Depends(get_async_session),
) -> None:
    user_data: Dict[str, str|int] = token.model_dump()   # Парсинг данных пользователя
    
    await ReferenceService._test(
        session=session,
        
        requester_user_privilege=user_data["privilege_id"]
    )
