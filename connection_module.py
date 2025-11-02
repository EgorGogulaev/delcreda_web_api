from collections import defaultdict
from typing import Any, AsyncGenerator, Dict, List, Literal, Optional, Set

import aioredis
import aiohttp
from aiohttp import FormData
from fastapi import HTTPException, UploadFile, WebSocket, status
from fastapi.concurrency import asynccontextmanager
from fastapi.responses import StreamingResponse
from sqlalchemy import create_engine, URL
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine, AsyncSession

from config import (
    DB_USER, DB_PASS, DB_HOST, DB_PORT, DB_NAME,
    PG_BOUNCER_HOST, PG_BOUNCER_PORT,
    REDIS_HOST, REDIS_PORT, REDIS_PASSWORD,
    SIGNAL_URL, SIGNAL_LOGIN, SIGNAL_PASSWORD,
)


class Base(DeclarativeBase):
    __abstract__ = True
    
    repr_cols_ignore = (
        "created_at",
        "updated_at",
    )
    
    def __repr__(self):
        """Используем только столбцы данных, исключая relationship для избежания неожиданных загрузок."""
        cols = self.__table__.columns
        # Собираем имена всех атрибутов, участвующих в отношениях
        relationship_keys = set(rel.key for rel in self.__mapper__.relationships)
        # Фильтруем столбцы, исключая те, которые принадлежат к отношениям
        display_cols = [col for col in cols if col.name not in relationship_keys]
        # Фильтрация и выбор столбцов на основе repr_cols и repr_cols_num
        selected_cols = [
            col for col in display_cols if col.name not in self.repr_cols_ignore
        ]
        # Формирование строки представления
        cols_data = [f"{col.name}={getattr(self, col.name)}" for col in selected_cols]
        return f"<{self.__class__.__name__} {', '.join(cols_data)}>"


DATABASE_DSN_SYNC = (
    f"postgresql+psycopg2://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
)
DATABASE_DSN_ASYNC = (
    f"postgresql+asyncpg://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
)

DATABASE_DSN_SYNC = f"postgresql+psycopg2://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
DATABASE_DSN_ASYNC = f"postgresql+asyncpg://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

DATABASE_BOUNCER_DSN_SYNC = f'postgresql+psycopg2://{DB_USER}:{DB_PASS}@{PG_BOUNCER_HOST}:{PG_BOUNCER_PORT}/{DB_NAME}'
DATABASE_BOUNCER_DSN_ASYNC = f'postgresql+asyncpg://{DB_USER}:{DB_PASS}@{PG_BOUNCER_HOST}:{PG_BOUNCER_PORT}/{DB_NAME}'

sync_engine = create_engine(DATABASE_BOUNCER_DSN_SYNC)
async_engine = create_async_engine(
    DATABASE_BOUNCER_DSN_ASYNC,
    
    pool_size=10,
    max_overflow=20,
    pool_timeout=70,
    pool_pre_ping=True,
    pool_recycle=3600,
    
    connect_args={
        "prepared_statement_cache_size": 0,  # Должно быть int, а не строка
        "command_timeout": 180,
        "server_settings": {
            "application_name": "delcreda_web_api",
        }
    },
    
    echo=False,
)

sync_engine_without_bouncer = create_engine(
    url=URL.create(
        drivername="postgresql+psycopg2",
        username=DB_USER,
        password=DB_PASS,
        host=DB_HOST,
        port=DB_PORT,
        database=DB_NAME,
    ),
    pool_size=5,
)
async_engine_without_bouncer = create_async_engine(
    DATABASE_DSN_ASYNC,
    connect_args={
        "server_settings": {
            "application_name": "delcreda_web_api"
        }
    },
)

sync_session_maker = sessionmaker(sync_engine)
async_session_maker = async_sessionmaker(
    async_engine,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)

async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_maker() as session:
        try:
            yield session
        except Exception as e:
            await session.rollback()
            raise e
        finally:
            await session.close()


class RedisConnector:
    DSN_SLOW = f"redis://:{REDIS_PASSWORD}@{REDIS_HOST}:{REDIS_PORT}/0"
    DSN_CONN = f"redis://:{REDIS_PASSWORD}@{REDIS_HOST}:{REDIS_PORT}/1"
    
    @asynccontextmanager
    @staticmethod
    async def get_async_redis_session() -> AsyncGenerator[aioredis.Redis, None]:
        redis_pool = await aioredis.create_redis_pool(RedisConnector.DSN_CONN)  # Создание пула соединений Redis
        try:
            yield redis_pool
        finally:  # Закрываем пул соединений Redis
            redis_pool.close()
            await redis_pool.wait_closed()
    
    @asynccontextmanager
    @staticmethod
    async def get_async_redis_pipe() -> AsyncGenerator[aioredis.commands.transaction.Pipeline, None]:
        redis_pool = await aioredis.create_redis_pool(RedisConnector.DSN_CONN)
        pipe = redis_pool.pipeline()
        try:
            yield pipe
        finally:  # Закрываем пул соединений Redis
            redis_pool.close()
            await redis_pool.wait_closed()


class WSConnectionManager:
    def __init__(self):
        # Храним соединения по каналам (channel -> set of websockets)
        self.active_connections: Dict[str, Set[WebSocket]] = defaultdict(set)
    
    async def connect(self, websocket: WebSocket, channel: str):
        await websocket.accept()
        self.active_connections[channel].add(websocket)
    
    def disconnect(self, channel: str, websocket: WebSocket):
        if channel in self.active_connections:
            self.active_connections[channel].discard(websocket)
            if not self.active_connections[channel]:
                del self.active_connections[channel]
    
    async def send_message(self, message: str, channel: str):
        if channel not in self.active_connections:
            return
        
        dead_connections = []
        for connection in self.active_connections[channel]:
            try:
                await connection.send_text(message)
            except Exception:
                dead_connections.append(connection)
        
        # Удаляем мертвые соединения
        for connection in dead_connections:
            self.active_connections[channel].discard(connection)
        
        # Если канал пуст - удаляем его
        if not self.active_connections[channel]:
            del self.active_connections[channel]


ws_connection_manager = WSConnectionManager()


class SignalConnector:
    api_url = SIGNAL_URL if SIGNAL_URL.endswith("/") else SIGNAL_URL + "/"
    auth = aiohttp.BasicAuth(
        login=SIGNAL_LOGIN,
        password=SIGNAL_PASSWORD,
    )
    
    @classmethod
    async def __http_request_signal(
        cls,
        method: Literal["POST", "GET", "PUT", "DELETE"],
        endpoint_path: str,
        
        headers: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
        json: Optional[Dict[str, Any]] = None,
        data: Optional[Dict[str, Any]] = None,
        
        streaming_response: bool = False,
    ) -> Dict[str, Any] | StreamingResponse:
        async with aiohttp.ClientSession(auth=cls.auth) as session:
            async with session.request(
                method=method,
                headers=headers,
                params=params,
                json=json,
                data=data,
                url=cls.api_url + endpoint_path,
                
                ssl=False,
            ) as response:
                if response.status in range(200, 300):
                    if streaming_response is False:
                        return await response.json()
                    else:
                        headers_to_forward = {}
                        content_disposition = response.headers.get("Content-Disposition")
                        if content_disposition:
                            headers_to_forward["Content-Disposition"] = content_disposition
                        content_type = response.headers.get("Content-Type", "application/octet-stream")
                        return StreamingResponse(
                            content=response.content,      # это асинхронный итератор байтов
                            media_type=content_type,
                            headers=headers_to_forward
                        )
                elif response.status in range(500, 600):
                    raise SystemError("Серверная ошибка на стороне DELCREDA SIGNAL!")
                else:
                    text = await response.text()
                    raise Exception(f"Ошибка {response.status}: {text}")
    
    
    @classmethod
    async def check_identifier(
        cls,
        
        target: str,
        uuid: str,
    ) -> bool:
        response: Dict[str, List] = await cls.__http_request_signal(
            method="GET",
            headers={
                'accept': 'application/json',
            },
            endpoint_path="identifier/get_identifiers_info",
            params={
                'uuids': [uuid],
                'targets': [target],
            }
        )
        
        return response["identifiers_info"][0]["is_exist"]
    
    @classmethod
    async def generate_identifiers(
        cls,
        target: str,
        count: int = 1,
    ) -> List[str]:
        response: Dict[str, List] = await cls.__http_request_signal(
            method="POST",
            endpoint_path="identifier/generate_identifiers",
            headers={
                'accept': 'application/json',
                'content-type': 'application/x-www-form-urlencoded',
            },
            params={
                'source': 'delcreda_web_api',
                'target': target,
                'count': count,
            }
        )
        
        return [identifier["uuid"] for identifier in response["identifiers"]]
    
    
    @classmethod
    async def notify_email(
        cls,
        
        subject: str,
        body: str,
        
        emails: List[str],
    ) -> None:
        await cls.__http_request_signal(
            method="POST",
            endpoint_path="notification/email",
            headers = {
                'accept': 'application/json',
                'Content-Type': 'application/json',
            },
            json={
                'to_emails': emails,
                'subject': subject,
                'body': body,
                'headers': {},
                'attachments': [],
                'body_html': '',
            }
        )
    
    @classmethod
    async def notify_telegram(
        cls,
        
        tg_user_name: str,
        message: str,
    ) -> None:
        await cls.__http_request_signal(
            method="POST",
            endpoint_path="notification/telegram",
            headers={
                'accept': 'application/json',
            },
            params={
                'user_name': tg_user_name,
                'message': message,
            }
        )
    
    
    # FIXME ПРОТЕСТИРОВАТЬ РАБОТУ С S3-ХРАНИЛИЩЕМ
    @classmethod
    async def upload_s3(
        cls,
        
        path: str,
        files: List[UploadFile],
    ) -> None:
        data = FormData()
        for file in files:
            filename = file.filename
            content_type = file.content_type or "application/octet-stream"
            async with file:
                content = await file.read()
                data.add_field(
                    name="files",
                    value=content,
                    filename=filename,
                    content_type=content_type,
                )
        await cls.__http_request_signal(
            method="POST",
            endpoint_path="file_store/upload",
            headers={"accept": "application/json"},
            params={"path": path},
            data=data,
        )
    
    @classmethod
    async def download_s3(
        cls,
        
        path: str,
    ) -> StreamingResponse:
        streaming_data: StreamingResponse = await cls.__http_request_signal(
            method="POST",
            endpoint_path="file_store/download",
            headers={
                'accept': 'application/json',
                'content-type': 'application/x-www-form-urlencoded',
            },
            params={
                'path': path,
            },
            data=b"",
            streaming_response=True,
        )
        
        return streaming_data
    
    @classmethod
    async def get_object_info_s3(
        cls,
        
        path: str,
    ) -> Dict[str, str|int]:
        data: Dict[str, str|int] = await cls.__http_request_signal(
            method="GET",
            endpoint_path="file_store/get_object_info",
            headers={
                'accept': 'application/json',
            },
            params={
                'path': path,
            },
        )
        
        return data
    
    @classmethod
    async def delete_s3(
        cls,
        
        path: str,  # НЕ НУЖЕН ПРЕФИКС НАЗВАНИЯ БАКЕТА!
    ) -> None:
        await cls.__http_request_signal(
            method="DELETE",
            endpoint_path="file_store/delete",
            headers={
                'accept': 'application/json',
            },
            params={
                'path': path,
            }
        )
    
    @classmethod
    async def create_user_s3(
        cls,
        
        username: str,
        password: str,
    ) -> None:
        if password and len(password) < 8:
            raise HTTPException(status_code=status.HTTP_411_LENGTH_REQUIRED, detail="Пароль пользователя S3-хранилища не должен быть более 8 символов!")
        
        await cls.__http_request_signal(
            method="POST",
            endpoint_path="file_store/create_user",
            headers={
                'accept': 'application/json',
                'Content-Type': 'application/x-www-form-urlencoded',
            },
            params={
                'username': username,
                'password': password,
            },
        )
    
    @classmethod
    async def get_users_s3(
        cls,
    ) -> List[Optional[Dict[str, str]]]:
        data: List[Optional[Dict[str, str]]] = await cls.__http_request_signal(
            method="GET",
            endpoint_path="file_store/get_users",
            headers={
                'accept': 'application/json',
            },
        )
        
        return data
    
    @classmethod
    async def change_user_password_s3(
        cls,
        
        username: str,
        new_password: str,
    ) -> None:
        await cls.__http_request_signal(
            method="PUT",
            endpoint_path="file_store/change_user_password",
            headers={
                'accept': 'application/json',
            },
            params={
                'username': username,
                'new_password': new_password,
            },
        )
    
    @classmethod
    async def enable_user_s3(
        cls,
        
        username: str,
    ) -> None:
        await cls.__http_request_signal(
            method="PUT",
            endpoint_path="file_store/enable_user",
            headers={
                'accept': 'application/json',
            },
            params={
                'username': username,
            }
        )
    
    @classmethod
    async def disable_user_s3(
        cls,
        
        username: str,
    ) -> None:
        await cls.__http_request_signal(
            method="PUT",
            endpoint_path="file_store/disable_user",
            headers={
                'accept': 'application/json',
            },
            params={
                'username': username,
            }
        )
    
    @classmethod
    async def remove_user_s3(
        cls,
        
        username: str,
    ) -> None:
        await cls.__http_request_signal(
            method="DELETE",
            endpoint_path="file_store/remove_user",
            headers={
                'accept': 'application/json',
            },
            params={
                'username': username,
            },
        )
    # FIXME ПРОТЕСТИРОВАТЬ РАБОТУ С S3-ХРАНИЛИЩЕМ
