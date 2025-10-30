import traceback
from typing import Dict, List, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from connection_module import get_async_session
from lifespan import limiter
from security import check_app_auth
from src.service.reference_service import ReferenceService
from src.service.order.order_service import OrderService
from src.query_and_statement.user_qas_manager import UserQueryAndStatementManager as UserQaSM


router = APIRouter(
    prefix="/",
    tags=["Order"],
)


@router.put(
    "/change_orders_status",
    description="""
    Изменение статуса Поручения.
    (Доступно только Админу)
    """,
    dependencies=[Depends(check_app_auth)],
)
@limiter.limit("3/second")
async def change_orders_status(
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
    order_uuids: List[str] = Query(
        [],
        description="Массив UUID-Поручений к изменению Cтатуса Поручение."
    ),
    
    token: str = Depends(UserQaSM.get_current_user_data),
    
    session: AsyncSession = Depends(get_async_session),
) -> JSONResponse:
    try:
        user_data: Dict[str, str|int] = token.model_dump()   # Парсинг данных пользователя
        
        await OrderService.change_orders_status(
            session=session,
            
            requester_user_uuid=user_data["user_uuid"],
            requester_user_privilege=user_data["privilege_id"],
            
            status=status,
            order_uuids=order_uuids,
        )
        
        # TODO тут нужно уведомление для 1 и множества лиц (нужна фоновая задача)
        
        response_content = {"msg": "Статус/ы Поручения/ий успешно изменен/ы."}
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
                endpoint="change_orders_status",
                params={
                    "status": status,
                    "order_uuids": order_uuids,
                },
                msg=f"{error_message}\n{formatted_traceback}",
                user_uuid=user_data["user_uuid"],
            )
            
            response_content = {"msg": f"ОШИБКА! #{log_id}"}
            return JSONResponse(content=response_content)

@router.put(
    "/change_orders_edit_status",
    description="""
    Изменение возможности Пользователем редактировать данные Поручении.
    (Может вызвать только Админ)
    """,
    dependencies=[Depends(check_app_auth)],
)
@limiter.limit("3/second")
async def change_orders_edit_status(
    request: Request,
    order_uuids: List[str] = Query(
        [],
        description="Массив UUID-Поручений к изменению возможности редактировать Поручение Пользователем."
    ),
    
    edit_status: bool = Query(
        ...,
        description="Значение на которое будет изменен возможности редактировать Поручение Пользователем.",
        example=False
    ),
    
    token: str = Depends(UserQaSM.get_current_user_data),
    
    session: AsyncSession = Depends(get_async_session),
) -> JSONResponse:
    try:
        user_data: Dict[str, str|int] = token.model_dump()   # Парсинг данных пользователя
        
        await OrderService.change_orders_edit_status(
            session=session,
            
            requester_user_uuid=user_data["user_uuid"],
            requester_user_privilege=user_data["privilege_id"],
            
            order_uuids=order_uuids,
            edit_status=edit_status,
        )
        
        # TODO тут нужно уведомление для 1 и множества лиц (нужна фоновая задача)
        
        return JSONResponse(content={"msg": f"Возможность редактирования Поручения/ий изменена на {edit_status}."})
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
                endpoint="change_orders_edit_status",
                params={
                    "order_uuids": order_uuids,
                    "edit_status": edit_status,
                },
                msg=f"{error_message}\n{formatted_traceback}",
                user_uuid=user_data["user_uuid"],
            )
            
            response_content = {"msg": f"ОШИБКА! #{log_id}"}
            return JSONResponse(content=response_content)


@router.delete(
    "/delete_orders",
    description="""
    Удаление Поручений.
    """,
    dependencies=[Depends(check_app_auth)],
)
@limiter.limit("3/second")
async def delete_orders(  # TODO Нужно предусмотреть параметр для удаления из хранилища Директорий и Документов
    request: Request,
    orders_uuids: List[str] = Query(
        [],
        description="Массив UUID-Поручений к удалению."
    ),
    
    token: str = Depends(UserQaSM.get_current_user_data),
    
    session: AsyncSession = Depends(get_async_session),
) -> JSONResponse:
    try:
        user_data: Dict[str, str|int] = token.model_dump()   # Парсинг данных пользователя
        
        await OrderService.delete_orders(
            session=session,
            
            requester_user_id=user_data["user_id"],
            requester_user_uuid=user_data["user_uuid"],
            requester_user_privilege=user_data["privilege_id"],
            
            orders_uuids=orders_uuids,
        )
        
        # TODO тут нужно уведомление для 1 и множества лиц (нужна фоновая задача)
        
        return JSONResponse(content={"msg": "Поручения успешно удалено/ы."})
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
                endpoint="delete_orders",
                params={
                    "orders_uuids": orders_uuids,
                },
                msg=f"{error_message}\n{formatted_traceback}",
                user_uuid=user_data["user_uuid"],
            )
            
            response_content = {"msg": f"ОШИБКА! #{log_id}"}
            return JSONResponse(content=response_content)

