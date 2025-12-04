import traceback
from typing import Dict, List, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from connection_module import get_async_session
from lifespan import limiter
from security import check_app_auth
from src.service.reference_service import ReferenceService
from src.service.application.application_service import ApplicationService
from src.query_and_statement.user_qas_manager import UserQueryAndStatementManager as UserQaSM


router = APIRouter(
    tags=["Application"],
)


@router.put(
    "/change_applications_status",
    description="""
    Изменение статуса Заявки.
    (Доступно только Админу)
    """,
    dependencies=[Depends(check_app_auth)],
)
@limiter.limit("30/second")
async def change_applications_status(
    request: Request,
    status: Literal[
        "Requested",
        "In_progress",
        "Rejected",
        "Requires_customer_attention",
        "In_queue",
        "Completed_successfully",
        "Completed_unsuccessfully",
    ],
    application_uuids: List[str] = Query(
        [],
        description="Массив UUID-Заявок к изменению Cтатуса."
    ),
    
    token: str = Depends(UserQaSM.get_current_user_data),
    
    session: AsyncSession = Depends(get_async_session),
) -> JSONResponse:
    try:
        user_data: Dict[str, str|int] = token.model_dump()   # Парсинг данных пользователя
        
        await ApplicationService.change_applications_status(
            session=session,
            
            requester_user_uuid=user_data["user_uuid"],
            requester_user_privilege=user_data["privilege_id"],
            
            status_=status,
            application_uuids=application_uuids,
        )
        
        # TODO тут нужно уведомление для 1 и множества лиц (нужна фоновая задача)
        
        response_content = {"msg": "Статус/ы Заявки/ок успешно изменен/ы."}
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
                endpoint="change_applications_status",
                params={
                    "status": status,
                    "application_uuids": application_uuids,
                },
                msg=f"{error_message}\n{formatted_traceback}",
                user_uuid=user_data["user_uuid"],
            )
            
            response_content = {"msg": f"ОШИБКА! #{log_id}"}
            return JSONResponse(content=response_content)
    finally:
        await session.rollback()

@router.put(
    "/change_applications_edit_status",
    description="""
    Изменение возможности Пользователем редактировать данные Заявок.
    (Может вызвать только Админ)
    """,
    dependencies=[Depends(check_app_auth)],
)
@limiter.limit("30/second")
async def change_applications_edit_status(
    request: Request,
    application_uuids: List[str] = Query(
        [],
        description="Массив UUID-Заявок к изменению возможности редактировать Заявок Пользователем."
    ),
    
    edit_status: bool = Query(
        ...,
        description="Значение на которое будет изменен статус возможности редактировать Заявки Пользователем.",
        example=False
    ),
    
    token: str = Depends(UserQaSM.get_current_user_data),
    
    session: AsyncSession = Depends(get_async_session),
) -> JSONResponse:
    try:
        user_data: Dict[str, str|int] = token.model_dump()   # Парсинг данных пользователя
        
        await ApplicationService.change_applications_edit_status(
            session=session,
            
            requester_user_uuid=user_data["user_uuid"],
            requester_user_privilege=user_data["privilege_id"],
            
            application_uuids=application_uuids,
            edit_status=edit_status,
        )
        
        # TODO тут нужно уведомление для 1 и множества лиц (нужна фоновая задача)
        
        return JSONResponse(content={"msg": f"Возможность редактирования Заявки/ок изменена на {edit_status}."})
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
                endpoint="change_applications_edit_status",
                params={
                    "application_uuids": application_uuids,
                    "edit_status": edit_status,
                },
                msg=f"{error_message}\n{formatted_traceback}",
                user_uuid=user_data["user_uuid"],
            )
            
            response_content = {"msg": f"ОШИБКА! #{log_id}"}
            return JSONResponse(content=response_content)
    finally:
        await session.rollback()


@router.delete(
    "/delete_applications",
    description="""
    Удаление Заявок.
    """,
    dependencies=[Depends(check_app_auth)],
)
@limiter.limit("30/second")
async def delete_applications(  # TODO Нужно предусмотреть параметр для удаления из хранилища Директорий и Документов
    request: Request,
    applications_uuids: List[str] = Query(
        [],
        description="Массив UUID-Заявок к удалению."
    ),
    
    token: str = Depends(UserQaSM.get_current_user_data),
    
    session: AsyncSession = Depends(get_async_session),
) -> JSONResponse:
    try:
        user_data: Dict[str, str|int] = token.model_dump()   # Парсинг данных пользователя
        
        await ApplicationService.delete_applications(
            session=session,
            
            requester_user_id=user_data["user_id"],
            requester_user_uuid=user_data["user_uuid"],
            requester_user_privilege=user_data["privilege_id"],
            
            applications_uuids=applications_uuids,
        )
        
        # TODO тут нужно уведомление для 1 и множества лиц (нужна фоновая задача)
        
        return JSONResponse(content={"msg": "Заявка/и успешно удалена/ы."})
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
                endpoint="delete_applications",
                params={
                    "applications_uuids": applications_uuids,
                },
                msg=f"{error_message}\n{formatted_traceback}",
                user_uuid=user_data["user_uuid"],
            )
            
            response_content = {"msg": f"ОШИБКА! #{log_id}"}
            return JSONResponse(content=response_content)
    finally:
        await session.rollback()

