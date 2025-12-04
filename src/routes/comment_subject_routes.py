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
from src.models.comment_subject_models import CommentSubject
from src.service.comment_subject_service import CommentSubjectService
from src.query_and_statement.user_qas_manager import UserQueryAndStatementManager as UserQaSM
from src.utils.reference_mapping_data.comment_subject.mapping import COMMENT_SUBJECT_MAPPING
from src.utils.tz_converter import convert_tz


router = APIRouter(
    tags=["Comment subject"],
)


@router.post(
    "/create_comment_subject",
    description="""
    Создание Комментария для Контрагента/Заявки.
    (Доступно только Админу)
    """,
    dependencies=[Depends(check_app_auth)],
)
@limiter.limit("30/second")
async def create_comment_subject(
    request: Request,
    comment_subject: Literal["Application", "Counterparty"] = Query(
        ...,
        description="К чему будет прикреплен Коммент (Контрагент/Заявка)."
    ),
    subject_uuid: str = Query(
        ...,
        description="UUID Контрагент/Заявки к которому/ой будет прикреплен Комментарий.",
        min_length=36,
        max_length=36
    ),
    
    data: Optional[str] = Query(
        None,
        description="Контент Комментария."
    ),
    
    token: str = Depends(UserQaSM.get_current_user_data),
    
    session: AsyncSession = Depends(get_async_session),
) -> JSONResponse:
    try:
        user_data: Dict[str, str|int] = token.model_dump()   # Парсинг данных пользователя
        
        
        await CommentSubjectService.create_comment_subject(
            session=session,
            
            requester_user_uuid=user_data["user_uuid"],
            requester_user_privilege=user_data["privilege_id"],
            
            subject_id=COMMENT_SUBJECT_MAPPING["Заявка"] if comment_subject == "Application" else COMMENT_SUBJECT_MAPPING["Контрагент"],
            subject_uuid=subject_uuid,
            
            data=data,
        )
        
        return JSONResponse(content={"msg": f'Комментарий для {"Заявки" if comment_subject == "Application" else "Контрагента"} успешно создан.'})
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
                endpoint="create_comment_subject",
                params={
                    "comment_subject": comment_subject,
                    "subject_uuid": subject_uuid,
                    "data": data,
                },
                msg=f"{error_message}\n{formatted_traceback}",
                user_uuid=user_data["user_uuid"],
            )
            
            response_content = {"msg": f"ОШИБКА! #{log_id}"}
            return JSONResponse(content=response_content)
    finally:
        await session.rollback()

@router.get(
    "/get_comment_subject",
    description="""
    Получение Комментария для Контрагента/Заявки.
    
    state: ClientState
    """,
    dependencies=[Depends(check_app_auth)],
)
@limiter.limit("30/second")
async def get_comment_subject(
    request: Request,
    comment_subject: Literal["Application", "Counterparty"] = Query(
        ...,
        description="К чему прикреплен Коммент (Контрагент/Заявка)."
    ),
    subject_uuid: str = Query(
        ...,
        description="UUID Контрагента/Заявки к которому/ой прикреплен Комментарий.",
        min_length=36,
        max_length=36
    ),
    
    token: str = Depends(UserQaSM.get_current_user_data),
    
    session: AsyncSession = Depends(get_async_session),
    
    client_state: Optional[ClientState] = None,
) -> JSONResponse:
    try:
        user_data: Dict[str, str|int] = token.model_dump()   # Парсинг данных пользователя
        
        if client_state is None:
            client_state: ClientState = await UserService.get_client_state(
                requester_user_uuid=user_data["user_uuid"],
                requester_user_privilege=user_data["privilege_id"],
                user_uuid=user_data["user_uuid"],
            )
        client_state_data: Dict[str, Any] = client_state.model_dump()["data"]
        
        comments: List[Optional[CommentSubject]] = await CommentSubjectService.get_comment_subject(
            session=session,
            
            requester_user_uuid=user_data["user_uuid"],
            requester_user_privilege=user_data["privilege_id"],
            
            subject_id=COMMENT_SUBJECT_MAPPING["Заявка"] if comment_subject == "application" else COMMENT_SUBJECT_MAPPING["Контрагент"],
            subject_uuid=subject_uuid,
        )
        if comments:
            response_content = {
                    "msg": "Успешный запрос Комменатрия.",
                    "data": {
                        "id": comments[0].id,
                        "subject_id": comments[0].subject_id,
                        "subject_uuid": comments[0].subject_uuid,
                        "creator_uuid": comments[0].creator_uuid,
                        "last_updater_uuid": comments[0].last_updater_uuid,
                        "data": comments[0].data,
                        "updated_at": convert_tz(comments[0].updated_at.strftime("%d.%m.%Y %H:%M:%S UTC"), tz_city=client_state_data.get("tz")) if comments[0].updated_at else None,
                        "created_at": convert_tz(comments[0].created_at.strftime("%d.%m.%Y %H:%M:%S UTC"), tz_city=client_state_data.get("tz")) if comments[0].created_at else None,
                    },
                    "count": 1,
            }
        else:
            response_content = {
                    "msg": "Комментарий отсутствует.",
                    "data": None,
                    "count": 0,
            }
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
                endpoint="get_comment_subject",
                params={
                    "comment_subject": comment_subject,
                    "subject_uuid": subject_uuid,
                },
                msg=f"{error_message}\n{formatted_traceback}",
                user_uuid=user_data["user_uuid"],
            )
            
            response_content = {"msg": f"ОШИБКА! #{log_id}"}
            return JSONResponse(content=response_content)
    finally:
        await session.rollback()

@router.put(
    "/update_comment_subject",
    description="""
    Обновление Комментария для Контрагента/Заявки.
    (Доступно только Админу)
    """,
    dependencies=[Depends(check_app_auth)],
)
@limiter.limit("30/second")
async def update_comment_subject(
    request: Request,
    comment_subject: Literal["Application", "Counterparty"] = Query(
        ...,
        description="К чему прикреплен Комментарий, в котором планируется обновление (Контрагент/Заявка)."
    ),
    subject_uuid: str = Query(
        ...,
        description="UUID Контрагент/Заявки к которому/ой прикреплен Комментарий, в котором планируется обновление.",
        min_length=36,
        max_length=36
    ),
    
    new_data: Optional[str] = Query("~", description="Новый контент Комментария. (значение '~' == оставить без изменений)"),
    
    token: str = Depends(UserQaSM.get_current_user_data),
    
    session: AsyncSession = Depends(get_async_session),
) -> JSONResponse:
    try:
        user_data: Dict[str, str|int] = token.model_dump()   # Парсинг данных пользователя
        
        await CommentSubjectService.update_comment_subject(
            session=session,
            
            requester_user_uuid=user_data["user_uuid"],
            requester_user_privilege=user_data["privilege_id"],
            
            subject_id=COMMENT_SUBJECT_MAPPING["Заявка"] if comment_subject == "Application" else COMMENT_SUBJECT_MAPPING["Контрагент"],
            subject_uuid=subject_uuid,
            
            new_data=new_data
        )
        
        return JSONResponse(content={"msg": "Комментарий успешно обновлен."})
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
                endpoint="update_comment_subject",
                params={
                    "comment_subject": comment_subject,
                    "subject_uuid": subject_uuid,
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
    "/delete_comment_subject",
    description="""
    Удаление комментария для Контрагента/Заявки.
    (Доступно только Админу)
    """,
    dependencies=[Depends(check_app_auth)],
)
@limiter.limit("30/second")
async def delete_comment_subject(
    request: Request,
    comment_subject: Literal["Application", "Counterparty"] = Query(
        ...,
        description="К чему прикреплен Комментарий, который планируется удалить (Контрагент/Заявка)."
    ),
    subject_uuid: str = Query(
        ...,
        description="UUID Контрагента/Заявки к которому прикреплен Комментарий, который планируется удалить.",
        min_length=36,
        max_length=36
    ),
    
    token: str = Depends(UserQaSM.get_current_user_data),
    
    session: AsyncSession = Depends(get_async_session),
) -> JSONResponse:
    try:
        user_data: Dict[str, str|int] = token.model_dump()   # Парсинг данных пользователя
        
        await CommentSubjectService.delete_comment_subject(
            session=session,
            
            requester_user_uuid=user_data["user_uuid"],
            requester_user_privilege=user_data["privilege_id"],
            
            subject_id=COMMENT_SUBJECT_MAPPING["Заявка"] if comment_subject == "Application" else COMMENT_SUBJECT_MAPPING["Контрагент"],
            subject_uuid=subject_uuid,
        )
        
        return JSONResponse(content={"msg": "Комментарий успешно обновлен."})
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
                endpoint="delete_comment_subject",
                params={
                    "comment_subject": comment_subject,
                    "subject_uuid": subject_uuid,
                },
                msg=f"{error_message}\n{formatted_traceback}",
                user_uuid=user_data["user_uuid"],
            )
            
            response_content = {"msg": f"ОШИБКА! #{log_id}"}
            return JSONResponse(content=response_content)
    finally:
        await session.rollback()
