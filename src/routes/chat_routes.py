import asyncio
import datetime
import json
import traceback
from typing import Any, Dict, List, Literal, Optional

from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import APIRouter, Depends, HTTPException, Query, Request, WebSocket, WebSocketDisconnect, status
from fastapi.responses import JSONResponse

from lifespan import limiter
from connection_module import WSConnectionManager, get_async_session, ws_connection_manager
from security import check_app_auth
from src.service.user_service import UserService
from src.service.reference_service import ReferenceService
from src.schemas.chat_schema import MessageData, ResponseGetMessages
from src.schemas.user_schema import ClientState, UserSchema
from src.query_and_statement.chat_qas_manager import ChatQueryAndStatementManager
from src.service.chat_service import ChatService
from src.query_and_statement.user_qas_manager import UserQueryAndStatementManager as UserQaSM
from src.models.chat_models import Message
from src.utils.reference_mapping_data.user.mapping import PRIVILEGE_MAPPING
from src.utils.tz_converter import convert_tz


router = APIRouter(
    tags=["Chat"],
)


@router.websocket("/ws/{chat_subject}/{subject_uuid}")
async def websocket_chat(
    websocket: WebSocket,
    chat_subject: Literal["Application", "Counterparty", "CommercialProposal"],
    subject_uuid: str,
    token: str = Query(...),
    manager: WSConnectionManager = Depends(lambda: ws_connection_manager),
) -> None:
    # TODO (!!!) pip install 'uvicorn[standard]'
    token: UserSchema = await UserQaSM.get_current_user_data(token=token)
    
    if not token:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return
    
    user_data: Dict[str, str|int] = token.model_dump()   # Парсинг данных пользователя
    
    chat_subject = "Заявка" if chat_subject == "Application" else "Контрагент" if chat_subject == "Counterparty" else "КП"
    
    chat_id: Optional[int] = await ChatQueryAndStatementManager.check_access(
        session=None,
        
        requester_user_uuid=user_data["user_uuid"],
        requester_user_privilege=user_data["privilege_id"],
        chat_subject=chat_subject,
        subject_uuid=subject_uuid,
    )
    
    if chat_id is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Чат Вам не доступен для отправки сообщений или же не существует!")
    
    channel = f"{chat_subject}_{subject_uuid}"
    await manager.connect(websocket, channel)
    
    try:
        while True:
            message_data = await asyncio.wait_for(
                websocket.receive_json(),
                timeout=300
            )
            
            if not (message := message_data.get("msg")):
                continue
            
            await ChatService.send_message(
                session=None,
                
                requester_user_id=user_data["user_id"],
                requester_user_uuid=user_data["user_uuid"],
                requester_user_privilege=user_data["privilege_id"],
                chat_subject=chat_subject,
                subject_uuid=subject_uuid,
                message=message,
            )
            
            await manager.send_message(
                message=json.dumps({
                    "user_id": user_data["user_id"],
                    "user_uuid": user_data["user_uuid"],
                    "user_privilege_id": user_data["privilege_id"],
                    "chat_subject": chat_subject,
                    "subject_uuid": subject_uuid,
                    "data": message,
                    "created_at": datetime.datetime.now().strftime("%d.%m.%Y %H:%M:%S UTC"),
                    "chat_id": chat_id  # Добавляем ID чата из проверки доступа
                }),
                channel=channel,
            )
    
    except (asyncio.TimeoutError, WebSocketDisconnect):
        manager.disconnect(channel, websocket)
    
    except Exception as e:
        # print(f"WebSocket error: {e}")
        manager.disconnect(channel, websocket)
        if isinstance(e, HTTPException):
            raise e
        else:
            error_message = str(e)
            formatted_traceback = traceback.format_exc()
            
            log_id = await ReferenceService.create_errlog(
                endpoint="websocket_chat",
                params={
                    "chat_subject": chat_subject,
                    "subject_uuid": subject_uuid,
                },
                msg=f"{error_message}\n{formatted_traceback}",
                user_uuid=user_data["user_uuid"],
            )
            
            response_content = {"msg": f"ОШИБКА! #{log_id}"}
            return JSONResponse(content=response_content)
    finally:
        try: await websocket.close()  # noqa: E701
        except: ...  # noqa: E722

@router.post(
    "/send_message",
    description="""
    Отправка сообщения в определенный Чат по HTTP.
    """,
    dependencies=[Depends(check_app_auth)],
)
@limiter.limit("30/second")
async def send_message(
    request: Request,
    chat_subject: Literal["Application", "Legal entity"] = Query(
        ...,
        description="В какой Чат отправляем сообщение? (В Чат для Заявки или для Контрагента)"
    ),
    subject_uuid: str = Query(
        ...,
        description="UUID Контрагент/Заявки в Чат которого будет отправлено сообщение.",
        min_length=36,
        max_length=36
    ),
    message: Dict[str, str] = {"msg": ""},
    
    token: str = Depends(UserQaSM.get_current_user_data),
    
    session: AsyncSession = Depends(get_async_session),
) -> JSONResponse:
    try:
        if message.get("msg") in (None, ""):
            raise HTTPException(status_code=status.HTTP_411_LENGTH_REQUIRED, detail="Тело Сообщения пустое!")
        
        
        user_data: Dict[str, str|int] = token.model_dump()   # Парсинг данных пользователя
        
        await ChatService.send_message(
            session=session,
            
            requester_user_id=user_data["user_id"],
            requester_user_uuid=user_data["user_uuid"],
            requester_user_privilege=user_data["privilege_id"],
            chat_subject="Заявка" if chat_subject == "Application" else "Контрагент",
            subject_uuid=subject_uuid,
            message=message.get("msg"),
        )
        
        return JSONResponse(content={"msg": "Успешная доставка."})
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
                endpoint="send_messages",
                params={
                    "chat_subject": chat_subject,
                    "subject_uuid": subject_uuid,
                    "message": message,
                },
                msg=f"{error_message}\n{formatted_traceback}",
                user_uuid=user_data["user_uuid"],
            )
            
            response_content = {"msg": f"ОШИБКА! #{log_id}"}
            return JSONResponse(content=response_content)
    finally:
        await session.rollback()

@router.get(
    "/get_messages",
    description="""
    Получение сообщений из Чата.
    
    state: ClientState
    output: ResponseGetMessages
    """,
    dependencies=[Depends(check_app_auth)],
)
@limiter.limit("30/second")
async def get_messages(
    request: Request,
    chat_subject: Literal["Application", "Counterparty"] = Query(
        ...,
        description="Из какого Чата достаем сообщения? (Из Чата для Заявки или для Контрагента)"
    ),
    subject_uuid: str = Query(
        ...,
        description="UUID Контрагента/Заявки из Чата которго/ой будут взяты сообщение.",
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
    
    token: str = Depends(UserQaSM.get_current_user_data),
    
    session: AsyncSession = Depends(get_async_session),
    
    client_state: Optional[ClientState] = None,
) -> ResponseGetMessages:
    try:
        user_data: Dict[str, str|int] = token.model_dump()   # Парсинг данных пользователя
        
        if client_state is None:
            client_state: ClientState = await UserService.get_client_state(
                requester_user_uuid=user_data["user_uuid"],
                requester_user_privilege=user_data["privilege_id"],
                user_uuid=user_data["user_uuid"],
            )
        client_state_data: Dict[str, Any] = client_state.model_dump()["data"]
        
        messages: Dict[str, List[Optional[Message]]|Optional[int]] = await ChatService.get_messages(
            session=session,
            
            requester_user_uuid=user_data["user_uuid"],
            requester_user_privilege=user_data["privilege_id"],
            chat_subject="Заявка" if chat_subject == "Application" else "Контрагент",
            subject_uuid=subject_uuid,
            
            page=page,
            page_size=page_size,
        )
        response_content = ResponseGetMessages(
            data=[],
            count=0,
            total_records=None,
            total_pages=None,
        )
        
        for message in messages["data"]:
            msg_data = MessageData(
                user_id=message.user_id,
                user_uuid=message.user_uuid,
                user_privilege={v: k for k, v in PRIVILEGE_MAPPING.items()}[message.user_privilege_id],
                chat_id=message.chat_id,
                data=message.data,
                created_at=convert_tz(message.created_at.strftime("%d.%m.%Y %H:%M:%S UTC"), tz_city=client_state_data.get("tz")) if message.created_at else None,
            )
            response_content.count += 1
            response_content.data.append(msg_data)
        
        
        response_content.total_records = messages["total_records"]
        response_content.total_pages = messages["total_pages"]
        
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
                endpoint="get_messages",
                params={
                    "chat_subject": chat_subject,
                    "subject_uuid": subject_uuid,
                    "page": page,
                    "page_size": page_size,
                },
                msg=f"{error_message}\n{formatted_traceback}",
                user_uuid=user_data["user_uuid"],
            )
            
            response_content = {"msg": f"ОШИБКА! #{log_id}"}
            return JSONResponse(content=response_content)
    finally:
        await session.rollback()

@router.delete(
    "/delete_messages",
    description="""
    Удаление сообщений из Чата.
    Не вызывает исключений при удалении по несуществующему ID.
    (Доступно только для Админа)
    """,
    dependencies=[Depends(check_app_auth)],
)
@limiter.limit("30/second")
async def delete_messages(
    request: Request,
    list_ids: List[int] = Query(
        [],
        description="Массив ID сообщений к удалению."
    ),
    
    token: str = Depends(UserQaSM.get_current_user_data),
    
    session: AsyncSession = Depends(get_async_session),
) -> JSONResponse:
    try:
        user_data: Dict[str, str|int] = token.model_dump()   # Парсинг данных пользователя
        
        await ChatService.delete_messages(
            session=session,
            
            requester_user_privilege=user_data["privilege_id"],
            list_ids=list_ids,
        )
        
        return JSONResponse(content={"msg": f"Сообщения с id: {list_ids,} были удалены (всего {len(list_ids)})."})
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
                endpoint="delete_messages",
                params={
                    "list_ids": list_ids,
                },
                msg=f"{error_message}\n{formatted_traceback}",
                user_uuid=user_data["user_uuid"],
            )
            
            response_content = {"msg": f"ОШИБКА! #{log_id}"}
            return JSONResponse(content=response_content)
    finally:
        await session.rollback()
