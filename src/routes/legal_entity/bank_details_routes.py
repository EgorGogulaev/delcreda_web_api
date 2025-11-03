import traceback
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from connection_module import get_async_session
from lifespan import limiter
from security import check_app_auth
from src.schemas.user_schema import ClientState
from src.service.user_service import UserService
from src.service.reference_service import ReferenceService
from src.service.notification_service import NotificationService
from src.models.legal_entity.bank_details_models import BankDetails
from src.service.legal_entity.bank_details_service import BankDetailsService
from src.query_and_statement.user_qas_manager import UserQueryAndStatementManager as UserQaSM
from src.schemas.legal_entity.bank_details_schema import CreateBanksDetailsSchema, UpdateBankDetailsSchema
from src.utils.reference_mapping_data.user.mapping import PRIVILEGE_MAPPING
from src.utils.tz_converter import convert_tz


router = APIRouter(
    tags=["Bank details"],
)

@router.post(
    "/create_banks_details",
    description="""
    Создание банковских реквизитов.
    
    input: CreateBanksDetailsSchema
    """,
    dependencies=[Depends(check_app_auth)],
)
@limiter.limit("3/second")
async def create_banks_details(
    request: Request,
    new_banks_details: CreateBanksDetailsSchema,
    
    token: str = Depends(UserQaSM.get_current_user_data),
    
    session: AsyncSession = Depends(get_async_session),
) -> JSONResponse:
    try:
        user_data: Dict[str, str|int] = token.model_dump()   # Парсинг данных пользователя
        
        await BankDetailsService.create_banks_details(
            session=session,
            requester_user_uuid=user_data["user_uuid"],
            requester_user_privilege=user_data["privilege_id"],
            
            new_banks_details=new_banks_details,
        )
        
        le_uuid: str = new_banks_details.new_banks_details[0].legal_entity_uuid
        
        if user_data["privilege_id"] != PRIVILEGE_MAPPING["Admin"]:
            await NotificationService.notify(
                session=session,
                
                requester_user_id=user_data["user_id"],
                requester_user_uuid=user_data["user_uuid"],
                requester_user_privilege=user_data["privilege_id"],
                
                subject="ЮЛ",
                subject_uuid=new_banks_details.new_banks_details[0].legal_entity_uuid,
                for_admin=True,
                data=f'Пользователь "{user_data["user_uuid"]}" добавил банковские реквизиты в ЮЛ "{le_uuid}".',
                recipient_user_uuid=None,
            )
        
        return JSONResponse(content={"msg": "Банковские реквизиты созданы."})
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
                endpoint="create_banks_details",
                params={
                    "new_banks_details": new_banks_details.model_dump() if new_banks_details else new_banks_details,
                },
                msg=f"{error_message}\n{formatted_traceback}",
                user_uuid=user_data["user_uuid"],
            )
            
            response_content = {"msg": f"ОШИБКА! #{log_id}"}
            return JSONResponse(content=response_content)

@router.get(
    "/get_banks_details",
    description="""
    Получение банковских реквизитов.
    
    state: ClientState
    """,
    dependencies=[Depends(check_app_auth)],
)
@limiter.limit("3/second")
async def get_banks_details(  # FIXME тут скорее всего нужно будет добавить фильтр по полю "from_customer"
    request: Request,
    legal_entity_uuid: Optional[str] = Query(
        None,
        description="(Опционально) Фильтр по UUID ЮЛ к которому прикреплены реквизиты (точное совпадение)."
    ),
    user_uuid: Optional[str] = Query(
        None,
        description="(Опционально) Фильтр по UUID пользователя (точное совпадение)."
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
        
        banks_details: List[Optional[BankDetails]] = await BankDetailsService.get_banks_details(
            session=session,
            
            requester_user_uuid=user_data["user_uuid"],
            requester_user_privilege=user_data["privilege_id"],
            
            legal_entity_uuid=legal_entity_uuid,
            user_uuid=user_uuid,
        )
        
        response_content = {
            "data": [],
            "count": 0,
        }
        
        for bank_details in banks_details:
            response_content["count"] += 1
            response_content["data"].append(
                {
                    "id": bank_details.id,
                    "user_uuid": bank_details.user_uuid,
                    "from_customer": bank_details.from_customer,
                    "legal_entity_uuid": bank_details.legal_entity_uuid,
                    "name_latin": bank_details.name_latin,
                    "name_national": bank_details.name_national,
                    "organizational_and_legal_form": bank_details.organizational_and_legal_form,
                    "SWIFT": bank_details.SWIFT,
                    "BIC": bank_details.BIC,
                    "IBAN": bank_details.IBAN,
                    "banking_messaging_system": bank_details.banking_messaging_system,
                    "CIPS": bank_details.CIPS,
                    "registration_identifier": bank_details.registration_identifier,
                    "current_account_rub": bank_details.current_account_rub,
                    "current_account_eur": bank_details.current_account_eur,
                    "current_account_usd": bank_details.current_account_usd,
                    "current_account_cny": bank_details.current_account_cny,
                    "current_account_chf": bank_details.current_account_chf,
                    "correspondence_account": bank_details.correspondence_account,
                    "address": bank_details.address,
                    "created_at": convert_tz(bank_details.created_at.strftime("%d.%m.%Y %H:%M:%S UTC"), tz_city=client_state_data.get("tz")) if bank_details.created_at else None,
                }
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
                endpoint="get_banks_details",
                params={
                    "legal_entity_uuid": legal_entity_uuid,
                    "user_uuid": user_uuid,
                },
                msg=f"{error_message}\n{formatted_traceback}",
                user_uuid=user_data["user_uuid"],
            )
            
            response_content = {"msg": f"ОШИБКА! #{log_id}"}
            return JSONResponse(content=response_content)

@router.put(
    "/update_bank_details",
    description="""
    Обновление банковских реквизитов.
    
    input: UpdateBankDetailsSchema
    """,
    dependencies=[Depends(check_app_auth)],
)
@limiter.limit("3/second")
async def update_bank_details(
    request: Request,
    data_for_update: UpdateBankDetailsSchema,
    
    bank_details_id: int = Query(
        ...,
        description="ID банковских реквизитов, в которых планируются правки."
    ),
    
    token: str = Depends(UserQaSM.get_current_user_data),
    
    session: AsyncSession = Depends(get_async_session),
) -> JSONResponse:
    try:
        user_data: Dict[str, str|int] = token.model_dump()   # Парсинг данных пользователя
        
        await BankDetailsService.update_bank_details(
            session=session,
            
            requester_user_uuid=user_data["user_uuid"],
            requester_user_privilege=user_data["privilege_id"],
            
            bank_details_id=bank_details_id,
            user_uuid=data_for_update.user_uuid,
            from_customer=data_for_update.from_customer,
            legal_entity_uuid=data_for_update.legal_entity_uuid,
            name_latin=data_for_update.name_latin,
            name_national=data_for_update.name_national,
            organizational_and_legal_form=data_for_update.organizational_and_legal_form,
            SWIFT=data_for_update.SWIFT,
            BIC=data_for_update.BIC,
            IBAN=data_for_update.IBAN,
            banking_messaging_system=data_for_update.banking_messaging_system,
            CIPS=data_for_update.CIPS,
            registration_identifier=data_for_update.registration_identifier,
            current_account_rub=data_for_update.current_account_rub,
            current_account_eur=data_for_update.current_account_eur,
            current_account_usd=data_for_update.current_account_usd,
            current_account_cny=data_for_update.current_account_cny,
            current_account_chf=data_for_update.current_account_chf,
            correspondence_account=data_for_update.correspondence_account,
            address=data_for_update.address,
        )
        
        return JSONResponse(content={"msg": "Данные ФЛ успешно обновлены."})
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
                endpoint="update_bank_details",
                params={
                    "data_for_update": data_for_update.model_dump() if data_for_update else data_for_update,
                    "bank_details_id": bank_details_id,
                },
                msg=f"{error_message}\n{formatted_traceback}",
                user_uuid=user_data["user_uuid"],
            )
            
            response_content = {"msg": f"ОШИБКА! #{log_id}"}
            return JSONResponse(content=response_content)

@router.delete(
    "/delete_banks_details",
    description="""
    Удаление банковских реквизитов.
    """,
    dependencies=[Depends(check_app_auth)],
)
@limiter.limit("3/second")
async def delete_bank_details(
    request: Request,
    bank_details_ids: List[Optional[int]] = Query(
        [],
        description="Массив ID банковских реквизитов к удалению."
    ),
    
    token: str = Depends(UserQaSM.get_current_user_data),
    
    session: AsyncSession = Depends(get_async_session),
) -> JSONResponse:
    try:
        user_data: Dict[str, str|int] = token.model_dump()   # Парсинг данных пользователя
        
        await BankDetailsService.delete_banks_details(
            session=session,
            
            requester_user_uuid=user_data["user_uuid"],
            requester_user_privilege=user_data["privilege_id"],
            
            bank_details_ids=bank_details_ids,
        )
        
        return JSONResponse(content={"msg": "Запись о реквизитах успешно удалена."})
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
                endpoint="delete_bank_details",
                params={
                    "bank_details_ids": bank_details_ids,
                },
                msg=f"{error_message}\n{formatted_traceback}",
                user_uuid=user_data["user_uuid"],
            )
            
            response_content = {"msg": f"ОШИБКА! #{log_id}"}
            return JSONResponse(content=response_content)
