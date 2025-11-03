import aioredis
from fastapi import FastAPI
from fastapi.concurrency import asynccontextmanager
from slowapi import Limiter
from slowapi.util import get_remote_address

from connection_module import Base, sync_engine_without_bouncer, RedisConnector
from src.models.order.mt_models import MTOrderType
from src.models.order.order_models import OrderStatus, OrderType
from src.models.chat_models import ChatSubject
from src.models.notification_models import NotificationSubject
from src.models.file_store_models import Directory, DirectoryType, DocumentType
from src.models.reference_models import Country, Currency, ServiceNoteSubject
from src.models.user_models import Token, UserAccount, UserPrivilege
from src.utils.preparer_reference_information import prepare_reference
from src.utils.reference_mapping_data.app.app_reference_data import COUNTRY, CURRENCY
from src.utils.reference_mapping_data.user.reference import ADMIN, ADMIN_DIRECTORY, ADMIN_TOKEN, PRIVILEGE, SERVICE_NOTE_SUBJECT
from src.utils.reference_mapping_data.file_store.reference import DIRECTORY_TYPE, DOCUMENT_TYPE
from src.utils.reference_mapping_data.chat.reference import CHAT_SUBJECT
from src.utils.reference_mapping_data.notification.reference import NOTIFICATION_SUBJECT
from src.utils.reference_mapping_data.order.reference import ORDER_STATUS, ORDER_TYPE
from src.utils.reference_mapping_data.order.order.mt_reference import MT_ORDER_TYPE


limiter = Limiter(
    key_func=get_remote_address,  # ограничение по IP
    storage_uri=RedisConnector.DSN_SLOW,
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=sync_engine_without_bouncer)
    
    redis_conns = aioredis.create_connection(RedisConnector.DSN_CONN)
    
    for idx, (table, referense) in enumerate(
        zip(
            [
                UserPrivilege, Token, UserAccount,
                DirectoryType, DocumentType,
                Directory,
                
                Country, Currency,
                ChatSubject,
                NotificationSubject,
                
                OrderType, OrderStatus,
                MTOrderType,
                # TODO тут будут другие бизнес-направления
                
                ServiceNoteSubject,
            ],
            [
                PRIVILEGE, ADMIN_TOKEN, ADMIN,
                DIRECTORY_TYPE, DOCUMENT_TYPE,
                ADMIN_DIRECTORY,
                
                COUNTRY, CURRENCY,
                CHAT_SUBJECT,
                NOTIFICATION_SUBJECT,
                
                ORDER_TYPE, ORDER_STATUS,
                MT_ORDER_TYPE,
                # TODO тут будут другие бизнес-направления
                
                SERVICE_NOTE_SUBJECT,
            ],
        )
    ):
        prepare_reference(
            table=table,
            reference_data=referense,
            first_iteration=True if idx == 0 else False,
        )
    
    yield
    redis_conns.close()
