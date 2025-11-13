import os
import traceback
from typing import Any, Dict, List, Literal, Optional

import aiofiles
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import APIRouter, Body, Depends, Query, Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse

from config import ADMIN_UUID, ROOT_DIR
from connection_module import get_async_session
from security import check_app_auth
from src.service.reference_service import ReferenceService
from src.schemas.user_schema import AuthData, ClientState, FiltersUsersInfo, OrdersUsersInfo, ResponseAuth, ResponseGetUsersInfo, UpdateUserContactData
from src.service.user_service import UserService
from src.query_and_statement.user_qas_manager import UserQueryAndStatementManager as UserQaSM
from src.utils.reference_mapping_data.user.mapping import PRIVILEGE_MAPPING

from lifespan import limiter



router = APIRouter(
    tags=["User"],
)

@router.post(
    "/register_client",
    description="""
    Регистрация пользовател с правами Client.
    """,
    dependencies=[Depends(check_app_auth)],
)
@limiter.limit("30/second")
async def register_client(
    request: Request,
    
    email: str,
    password: str,
    
    session: AsyncSession = Depends(get_async_session),
) -> JSONResponse:
    try:
        await UserService.register_client(
            session=session,
            email=email,
            password=password,
        )
        
        response_content = {"msg": "На почту выслано сообщение для активации аккаунта."}
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
            
            log_id = await ReferenceService.create_errlog(  # FIXME Логирование в этом месте потенциально опасно (может переполнить холодную память)
                endpoint="register_client",
                params={
                    "email": email,
                    "password": password,
                },
                msg=f"{error_message}\n{formatted_traceback}",
                user_uuid="-",
            )
            
            response_content = {"msg": f"ОШИБКА! #{log_id}"}
            return JSONResponse(content=response_content)

@router.get(
    "/confirmation/{unique_path}",
    description="""
    Подтверждение регистрации аккаунта.
    """,
)
@limiter.limit("30/minute")
async def confirmation(
    request: Request,
    
    unique_path: str,
    
    session: AsyncSession = Depends(get_async_session),
) -> HTMLResponse:
    try:
        data: Dict[str, str] = await UserService.confirmation(
            session=session,
            
            unique_path=unique_path,
        )
        html_type = data.get("type")
        if html_type == "confirmationnewaccount":
            await UserService.create_user(
                session=session,
                
                requester_user_uuid=ADMIN_UUID,
                requester_user_privilege=PRIVILEGE_MAPPING["Admin"],
                login=data.get("email"),
                password=data.get("password"),
                privilege=PRIVILEGE_MAPPING["Client"],
            )
        elif html_type == "confirmationnewpassword":
            await UserService.update_user_info(
                session=session,
                
                requester_user_uuid=ADMIN_UUID,
                requester_user_privilege=PRIVILEGE_MAPPING["Admin"],
                target_token=None,
                target_user_uuid=None,
                target_login=data.get("email"),
                new_login=None,
                new_password=data.get("password"),
                new_user_uuid=None,
            )
        
        async with aiofiles.open(os.path.join(ROOT_DIR, "src", "static", html_type + ".html"), "r", encoding="utf-8") as f:
            html_content = await f.read()
        return HTMLResponse(content=html_content)
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
            
            log_id = await ReferenceService.create_errlog(  # FIXME Логирование в этом месте потенциально опасно (может переполнить холодную память)
                endpoint="confirmation",
                params={
                    "unique_path": unique_path,
                },
                msg=f"{error_message}\n{formatted_traceback}",
                user_uuid="-",
            )
            
            response_content = {"msg": f"ОШИБКА! #{log_id}"}
            return JSONResponse(content=response_content)


@router.post(
    "/register",
    description="""
    Регистрация пользователя.
    Доступно только Администраторам.
    """,
    dependencies=[Depends(check_app_auth)],
)
@limiter.limit("30/second")
async def register(
    request: Request,
    login: str = Query(
        ...,
        description="Логин Пользователя. (не менее 4 и не более 255 символов)",
        min_length=4,
        max_length=255,
        example="test",
    ),
    password: str = Query(
        ...,
        description="Пароль Пользователя. (не менее 5 и не более 255 символов)",
        min_length=8,
        max_length=255,
        example="1234578",
    ),
    privilege: Literal["Client", "Сounterparty"] = Query(
        "Client",
        description="Права выдаваемые пользователю. (Доступно - Клиент/Контрагент)",
        example="Client",
    ),
    new_user_uuid: Optional[str] = Query(
        None,
        description="(Опиционально) Ручное выставление нового UUID для пользователя. (нужно для интеграции в другие системы)",
        min_length=36,
        max_length=36,
    ),
    token: str = Depends(UserQaSM.get_current_user_data),
    
    session: AsyncSession = Depends(get_async_session),
) -> JSONResponse:
    try:
        user_data: Dict[str, str|int] = token.model_dump()   # Парсинг данных пользователя
        
        response_content: Dict[str, Any] = await UserService.create_user(
            session=session,
            
            requester_user_uuid=user_data["user_uuid"],
            requester_user_privilege=user_data["privilege_id"],
            login=login,
            password=password,
            privilege=PRIVILEGE_MAPPING[privilege],
            new_user_uuid=new_user_uuid,
        )
        
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
                endpoint="register",
                params={
                    "login": login,
                    "password": password,
                    "privilege": privilege,
                    "new_user_uuid": new_user_uuid,
                },
                msg=f"{error_message}\n{formatted_traceback}",
                user_uuid=user_data["user_uuid"],
            )
            
            response_content = {"msg": f"ОШИБКА! #{log_id}"}
            return JSONResponse(content=response_content)

@router.post(
    "/auth",
    description="""
    Авторизация. (именно этот метод НЕ ИСПОЛЬЗУЕТСЯ В React-приложении)
    """,
    dependencies=[Depends(check_app_auth)],
)
@limiter.limit("30/second")
async def auth(  # TODO этот метод будет использоваться при работе с шифрованием, шифровать будем только токен (???)
    request: Request,
    data: AuthData,
    
    session: AsyncSession = Depends(get_async_session),
) -> JSONResponse:
    try:
        enrypt_user_data: Dict[str, str] = await UserService.auth_user(
            session=session,
            
            login=data.login,
            password=data.password,
            for_flet=True,
        )
        
        return JSONResponse(content=enrypt_user_data)
    except AssertionError as e:
        error_message = str(e)
        formatted_traceback = traceback.format_exc()
        
        response_content = {"msg": f"{error_message}\n{formatted_traceback}"}
        return JSONResponse(content=response_content)


@router.post(
    "/auth_v2",
    description="""
    Авторизация пользователя.
    Предполагается ведение сессий на стороне клиента,
    для этого разработаны методы для JS/Python шифрования AES-GCM,
    поэтому чувствительные данные сможем хранить на стороне клиента в зашифрованном виде.
    
    input: AuthData
    output: ResponseAuth
    """,
    dependencies=[Depends(check_app_auth)],
)
@limiter.limit("30/second")
async def auth_v2(
    request: Request,
    data: AuthData,
    
    session: AsyncSession = Depends(get_async_session),
) -> ResponseAuth:
    try:
        response_content: Dict[str, str] | ResponseAuth = await UserService.auth_user(
            session=session,
            
            login=data.login,
            password=data.password,
            for_flet=False,
        )
        
        return response_content
    except AssertionError as e:
        error_message = str(e)
        formatted_traceback = traceback.format_exc()
        
        response_content = {"msg": f"{error_message}\n{formatted_traceback}"}
        return JSONResponse(content=response_content)


@router.post(
    "/get_users_info",
    description="""
    Получение информации по пользователям системы.
    (Пользователь(privilage=User) может запросить только информацию о себе.)
    
    filter: FiltersUsersInfo
    order: OrdersUsersInfo
    state: ClientState
    output: ResponseGetUsersInfo
    """,
    dependencies=[Depends(check_app_auth)],
)
@limiter.limit("30/second")
async def get_users_info(
    request: Request,
    privilege: Literal["Client", "Сounterparty", "Admin", "all"] = Query(
        "all",
        description="Фильтр для поиска по Правам пользователей.",
        min_length=3,
        max_length=12,
        example="Admin",
    ),
    login: Optional[str] = Query(
        None,
        description="(Опционально) Фильтр для поиска по Логину пользователя (точное совпадение).",
        min_length=4,
        max_length=255,
        example="Admin",
    ),
    user_token: Optional[str] = Query(
        None,
        description="(Опционально) Фильтр для поиска по Токену пользователя (точное совпадение)."
    ),
    user_token_ilike: Optional[str] = Query(
        None,
        description="(Опционально) Фильтр для поиска по Токену пользователя (частичное совпадение)."
    ),
    uuid: Optional[str] = Query(
        None,
        description="(Опционально) Фильтр для поиска по UUID пользователя (точное совпадение)."
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
    
    filter: Optional[FiltersUsersInfo] = None,
    order: Optional[OrdersUsersInfo] = None,
    
    token: str = Depends(UserQaSM.get_current_user_data),
    
    session: AsyncSession = Depends(get_async_session),
    
    client_state: Optional[ClientState] = None,
) -> ResponseGetUsersInfo:
    try:
        user_data: Dict[str, str|int] = token.model_dump()   # Парсинг данных пользователя
        
        if client_state is None:
            client_state: ClientState = await UserService.get_client_state(
                requester_user_uuid=user_data["user_uuid"],
                requester_user_privilege=user_data["privilege_id"],
                user_uuid=user_data["user_uuid"],
            )
        client_state_data: Dict[str, Any] = client_state.model_dump()["data"]
        
        response_content: ResponseGetUsersInfo = await UserService.get_users_info(
            session=session,
            
            requester_user_uuid=user_data["user_uuid"],
            requester_user_privilege=user_data["privilege_id"],
            privilege=PRIVILEGE_MAPPING[privilege] if privilege != "all" else None,
            login=login,
            user_token=user_token,
            user_token_ilike=user_token_ilike,
            uuid=uuid,
            
            page=page,
            page_size=page_size,
            
            filter=filter,
            order=order,
            
            tz=client_state_data.get("tz"),
        )
        
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
                endpoint="get_users_info",
                params={
                    "privilege": privilege,
                    "login": login,
                    "user_token": user_token,
                    "user_token_ilike": user_token_ilike,
                    "uuid": uuid,
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

@router.put(
    "/change_password",
    description="""
    Изменение пароля ПОЛЬЗОВАТЕЛЕМ с подтверждением через email.
    """,
    dependencies=[Depends(check_app_auth)],
)  # TODO На фронте нужно будет предусмотреть капчу от спама
@limiter.limit("30/second")
async def change_password(
    request: Request,
    
    email: str,
    old_password: str,
    new_password: str,
    
    session: AsyncSession = Depends(get_async_session),
) -> JSONResponse:
    try:
        await UserService.change_password(
            session=session,
            email=email,
            old_password=old_password,
            new_password=new_password,
        )
        
        response_content = {"msg": "На почту отправлена ссылка для подтверждения."}
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
            
            log_id = await ReferenceService.create_errlog(  # FIXME Логирование в этом месте потенциально опасно (может переполнить холодную память)
                endpoint="change_password",
                params={
                    "email": email,
                    "old_password": old_password,
                    "new_password": new_password,
                },
                msg=f"{error_message}\n{formatted_traceback}",
                user_uuid="-",
            )
            
            response_content = {"msg": f"ОШИБКА! #{log_id}"}
            return JSONResponse(content=response_content)

@router.put(
    "/update_user_info",
    description="""
    Изменение учетных данных пользователя.
    """,
    dependencies=[Depends(check_app_auth)],
)
@limiter.limit("30/second")
async def update_user_info(
    request: Request,
    target_token: Optional[str] = Query(
        None,
        description="Идентификатор пользователя (target_login/target_user_uuid/target_token - одно из трех полей обязательно к заполнению (можно все или пару))",
    ),
    target_user_uuid: Optional[str] = Query(
        None,
        min_length=36,
        max_length=36,
        description="Идентификатор пользователя (target_login/target_user_uuid/target_token - одно из трех полей обязательно к заполнению (можно все или пару))",
    ),
    target_login: Optional[str] = Query(
        None,
        min_length=4,
        max_length=255,
        description="Идентификатор пользователя (target_login/target_user_uuid/target_token - одно из трех полей обязательно к заполнению (можно все или пару))",
    ),
    
    new_login: Optional[str] = Query(
        None,
        min_length=4,
        max_length=255,
        description="Новый логин (если, None останется прежним)",
    ),
    new_password: Optional[str] = Query(
        None,
        min_length=5,
        max_length=255,
        description="Новый пароль (если, None останется прежним)",
    ),
    new_user_uuid: Optional[str] = Query(
        None,
        min_length=36,
        max_length=36,
        description="Новый пароль (если, None останется прежним)",
    ),
    
    token: str = Depends(UserQaSM.get_current_user_data),
    
    session: AsyncSession = Depends(get_async_session),
) -> JSONResponse:
    try:
        user_data: Dict[str, str|int] = token.model_dump()   # Парсинг данных пользователя
        
        await UserService.update_user_info(
            session=session,
            
            requester_user_uuid=user_data["user_uuid"],
            requester_user_privilege=user_data["privilege_id"],
            
            target_token=target_token,
            target_user_uuid=target_user_uuid,
            target_login=target_login,
            
            new_login=new_login,
            new_password=new_password,
            new_user_uuid=new_user_uuid,
        )
        
        response_content = {"msg": "Данные пользователя успешно обновлены."}
        
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
                endpoint="update_user_info",
                params={
                    "target_token": target_token,
                    "target_user_uuid": target_user_uuid,
                    "target_login": target_login,
                    "new_login": new_login,
                    "new_password": new_password,
                    "new_user_uuid": new_user_uuid,
                },
                msg=f"{error_message}\n{formatted_traceback}",
                user_uuid=user_data["user_uuid"],
            )
            
            response_content = {"msg": f"ОШИБКА! #{log_id}"}
            return JSONResponse(content=response_content)

@router.delete(
    "/delete_users",
    description="""
    Удаление пользователей (только НЕ админов).
    """,
    dependencies=[Depends(check_app_auth)],
)
@limiter.limit("30/minute")
async def delete_users(
    request: Request,
    tokens: List[str] = Query(
        [],
        description="Массив токенов-пользователей к удалению."
    ),
    uuids: List[str] = Query(
        [],
        description="Массив UUID'ов пользователей к удалению."
    ),
    
    with_documents: bool = Query(
        False,
        description="Нужно ли удалять документы пользователей? (true-да / false-нет)"
    ),
    
    token: str = Depends(UserQaSM.get_current_user_data),
    
    session: AsyncSession = Depends(get_async_session),
) -> JSONResponse:
    try:
        user_data: Dict[str, str|int] = token.model_dump()   # Парсинг данных пользователя
        
        await UserService.delete_users(
            session=session,
            
            requester_user_id=user_data["user_id"],
            requester_user_uuid=user_data["user_uuid"],
            requester_user_privilege=user_data["privilege_id"],
            
            with_documents=with_documents,
            
            tokens=tokens,
            uuids=uuids,
        )
        
        response_content = {"msg": "Пользователь/и успешно удален/ы."}
        
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
                endpoint="delete_users",
                params={
                    "tokens": tokens,
                    "uuids": uuids,
                    "with_documents": with_documents,
                },
                msg=f"{error_message}\n{formatted_traceback}",
                user_uuid=user_data["user_uuid"],
            )
            
            response_content = {"msg": f"ОШИБКА! #{log_id}"}
            return JSONResponse(content=response_content)

@router.get(
    "/get_client_states",
    description="""
    Получение состояния клиента.
    
    output: ClientState
    """,
    dependencies=[Depends(check_app_auth)],
)
@limiter.limit("30/second")
async def get_client_state(
    request: Request,
    user_uuid: str = Query(
        ...,
        description="UUID-клиента, состояние которого нужно получить."
    ),
    token: str = Depends(UserQaSM.get_current_user_data),
) -> ClientState:
    try:
        user_data: Dict[str, str|int] = token.model_dump()   # Парсинг данных пользователя
        
        data: ClientState = await UserService.get_client_state(
            requester_user_uuid=user_data["user_uuid"],
            requester_user_privilege=user_data["privilege_id"],
            
            user_uuid=user_uuid,
        )
        
        return data
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
                endpoint="get_client_state",
                params={
                    "user_uuid": user_uuid,
                },
                msg=f"{error_message}\n{formatted_traceback}",
                user_uuid=user_data["user_uuid"],
            )
            
            response_content = {"msg": f"ОШИБКА! #{log_id}"}
            return JSONResponse(content=response_content)

@router.put(
    "/record_client_states",
    description="""
    Запись нового состояния клиента.
    
    input: ClientState
    """,
    dependencies=[Depends(check_app_auth)],
)
@limiter.limit("30/second")
async def record_client_states(
    request: Request,
    new_state: ClientState,
    
    token: str = Depends(UserQaSM.get_current_user_data),
) -> JSONResponse:
    try:
        user_data: Dict[str, str|int] = token.model_dump()   # Парсинг данных пользователя
        new_state_data = new_state.model_dump()
        await UserService.record_client_states(
            requester_user_uuid=user_data["user_uuid"],
            requester_user_privilege=user_data["privilege_id"],
            
            client_uuid=user_data["user_uuid"],
            new_state=new_state_data["data"],
            ttl=new_state_data["ttl"],
        )
        response_content = {"msg": "Состояние успепшно обновлено."}
        
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
                endpoint="record_client_states",
                params={
                    "new_state": new_state.model_dump() if new_state else new_state,
                },
                msg=f"{error_message}\n{formatted_traceback}",
                user_uuid=user_data["user_uuid"],
            )
            
            response_content = {"msg": f"ОШИБКА! #{log_id}"}
            return JSONResponse(content=response_content)

@router.put(
    "/update_user_contact",
    description="""
    Обновление контактной информации пользователя системы.
    (Используется для уведомлений)
    """,
    dependencies=[Depends(check_app_auth)],
)
@limiter.limit("30/second")
async def update_user_contact(
    request: Request,
    
    user_uuid: str = Query(..., description="UUID-пользователя, которому нужно сменить контактные данные."),
    new_user_contact_data: UpdateUserContactData = Body(..., description="Новые данные по контактам пользователя."),
    
    token: str = Depends(UserQaSM.get_current_user_data),
    session: AsyncSession = Depends(get_async_session),
) -> JSONResponse:
    try:
        user_data: Dict[str, str|int] = token.model_dump()   # Парсинг данных пользователя
        
        await UserService.update_user_contact(
            session=session,
            
            requester_user_uuid=user_data["user_uuid"],
            requester_user_privilege=user_data["privilege_id"],
            
            new_user_contact_data=new_user_contact_data,
            user_uuid=user_uuid,
        )
        
        response_content = {"msg": "Контактная информация пользователя успешно обновлена."}
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
                endpoint="update_user_contact_data",
                params={
                    "new_user_contact_data": new_user_contact_data.model_dump(),
                },
                msg=f"{error_message}\n{formatted_traceback}",
                user_uuid=user_data["user_uuid"],
            )
            
            response_content = {"msg": f"ОШИБКА! #{log_id}"}
            return JSONResponse(content=response_content)
