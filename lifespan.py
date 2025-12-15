import aioredis
from fastapi import FastAPI
from fastapi.concurrency import asynccontextmanager
from slowapi import Limiter
from slowapi.util import get_remote_address

from connection_module import Base, sync_engine_without_bouncer, RedisConnector
from src.models.commercial_proposal_models import CommercialProposalStatus, CommercialProposalType
from src.models.counterparty.counterparty_models import CounterpartyType
from src.models.application.mt_models import MTApplicationType
from src.models.application.application_models import ApplicationStatus, ApplicationType
from src.models.chat_models import ChatSubject
from src.models.notification_models import NotificationSubject
from src.models.file_store_models import Directory, DirectoryType, DocumentType
from src.models.reference_models import Country, Currency, ServiceNoteSubject
from src.models.user_models import Token, UserAccount, UserPrivilege
from src.utils.preparer_reference_information import prepare_reference
from src.utils.reference_mapping_data.app.app_reference_data import COUNTRY, CURRENCY
from src.utils.reference_mapping_data.user.reference import ADMIN, ADMIN_DIRECTORY, ADMIN_TOKEN, PRIVILEGE, SERVICE_NOTE_SUBJECT
from src.utils.reference_mapping_data.file_store.reference import DIRECTORY_TYPE
from src.utils.reference_mapping_data.chat.reference import CHAT_SUBJECT
from src.utils.reference_mapping_data.notification.reference import NOTIFICATION_SUBJECT
from src.utils.reference_mapping_data.application.reference import APPLICATION_STATUS, APPLICATION_TYPE
from src.utils.reference_mapping_data.application.application.mt_reference import MT_APPLICATION_TYPE
from src.utils.reference_mapping_data.counterparty.reference import COUNTERPARTY_TYPE
from src.utils.reference_mapping_data.commercial_proposal.reference import COMMERCIAL_PROPOSAL_STATUS, COMMERCIAL_PROPOSAL_TYPE


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
                DirectoryType,
                Directory,
                
                Country, Currency,
                ChatSubject,
                NotificationSubject,
                
                CounterpartyType,
                
                ApplicationType, ApplicationStatus,
                MTApplicationType,
                # TODO тут будут другие бизнес-направления
                CommercialProposalType,
                CommercialProposalStatus,
                
                ServiceNoteSubject,
            ],
            [
                PRIVILEGE, ADMIN_TOKEN, ADMIN,
                DIRECTORY_TYPE,
                ADMIN_DIRECTORY,
                
                COUNTRY, CURRENCY,
                CHAT_SUBJECT,
                NOTIFICATION_SUBJECT,
                
                COUNTERPARTY_TYPE,
                
                APPLICATION_TYPE, APPLICATION_STATUS,
                MT_APPLICATION_TYPE,
                # TODO тут будут другие бизнес-направления
                COMMERCIAL_PROPOSAL_TYPE,
                COMMERCIAL_PROPOSAL_STATUS,
                
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
