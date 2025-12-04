import datetime
import traceback
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import JSONResponse

from connection_module import get_async_session
from lifespan import limiter
from security import check_app_auth
from src.query_and_statement.application.application_qas_manager import ApplicationQueryAndStatementManager
from src.schemas.user_schema import ClientState
from src.service.user_service import UserService
from src.service.reference_service import ReferenceService
from src.schemas.application.application_schema import BaseApplication, FiltersApplications, OrdersApplications
from src.schemas.application.mt_application_schema import ResponseGetMTApplications
from src.schemas.application.mt_application_schema import ExtendedMTApplication,  CreateMTApplicationDataSchema,  UpdateMTApplicationDataSchema
from src.service.notification_service import NotificationService
from src.models.application.application_models import Application
from src.models.application.mt_models import MTApplicationData
from src.service.application.mt_application_service import MTApplicationService
from src.query_and_statement.user_qas_manager import UserQueryAndStatementManager as UserQaSM
from src.utils.reference_mapping_data.app.app_mapping_data import COUNTRY_MAPPING, CURRENCY_MAPPING
from src.utils.reference_mapping_data.application.application.mt_mapping import MT_APPLICATION_TYPE_MAPPING
from src.utils.reference_mapping_data.application.mapping import APPLICATION_STATUS_MAPPING
from src.utils.reference_mapping_data.user.mapping import PRIVILEGE_MAPPING
from src.utils.tz_converter import convert_tz


router = APIRouter(
    prefix="/mt",
    tags=["MT Application"],
)

@router.post(
    "/create_application",
    description="""
    Создание Заявки.
    
    input: CreateMTApplicationDataSchema
    """,
    dependencies=[Depends(check_app_auth)],
)
@limiter.limit("30/second")
async def create_application(
    request: Request,
    application_data: CreateMTApplicationDataSchema,
    counterparty_uuid: str = Query(
        ...,
        description="UUID Контрагента по которому создается MT-Заявка.",
        min_length=36,
        max_length=36
    ),
    user_uuid: str = Query(
        ...,
        description="UUID Пользователя-владельца карточки Контрагента по которому создается MT-Заявка.",
        min_length=36,
        max_length=36
    ),
    new_directory_uuid: Optional[str] = Query(
        None,
        description="(Опиционально) Ручное выставление нового UUID для Директории под новую MT-Заявку. (нужно для интеграции в другие системы)",
        min_length=36,
        max_length=36
    ),
    
    token: str = Depends(UserQaSM.get_current_user_data),
    
    session: AsyncSession = Depends(get_async_session),
) -> JSONResponse:
    try:
        user_data: Dict[str, str|int] = token.model_dump()   # Парсинг данных пользователя
        
        new_application_with_data: Tuple[Tuple[Application, MTApplicationData], Dict[str, str|int]] = await MTApplicationService.create_application(
            session=session,
            
            requester_user_uuid=user_data["user_uuid"],
            requester_user_privilege=user_data["privilege_id"],
            
            user_uuid=user_uuid,
            counterparty_uuid=counterparty_uuid,
            new_directory_uuid=new_directory_uuid,
            
            # ApplicationData
            order_name=application_data.order_name,
            payment_deadline_not_earlier_than=datetime.datetime.strptime(application_data.payment_deadline_not_earlier_than, "%d.%m.%Y").date() if application_data.payment_deadline_not_earlier_than else None,
            payment_deadline_no_later_than=datetime.datetime.strptime(application_data.payment_deadline_no_later_than, "%d.%m.%Y").date() if application_data.payment_deadline_no_later_than else None,
            invoice_date=datetime.datetime.strptime(application_data.invoice_date, "%d.%m.%Y").date() if application_data.invoice_date else None,
            
            type=MT_APPLICATION_TYPE_MAPPING[application_data.type],
            
            invoice_currency=CURRENCY_MAPPING[application_data.invoice_currency] if application_data.invoice_currency else None,
            invoice_amount=float(application_data.invoice_amount) if application_data.invoice_amount else None,
            payment_amount=float(application_data.payment_amount) if application_data.payment_amount else None,
            payment_amount_in_words=application_data.payment_amount_in_words,
            partial_payment_allowed=True if application_data.partial_payment_allowed and application_data.partial_payment_allowed == "true" else False if application_data.partial_payment_allowed and application_data.partial_payment_allowed == "false" else None,
            invoice_number=application_data.invoice_number,
            
            amount_to_withdraw=application_data.amount_to_withdraw,
            amount_to_replenish=application_data.amount_to_replenish,
            amount_to_principal=application_data.amount_to_principal,
            amount_credited=application_data.amount_credited,
            is_amount_different=True if application_data.is_amount_different and application_data.is_amount_different == "true" else False if application_data.is_amount_different and application_data.is_amount_different == "false" else None,
            source_bank=application_data.source_bank,
            target_bank=application_data.target_bank,
            source_currency=CURRENCY_MAPPING[application_data.source_currency] if application_data.source_currency else None,
            target_currency=CURRENCY_MAPPING[application_data.target_currency] if application_data.target_currency else None,
            amount=application_data.amount,
            subagent_bank=application_data.subagent_bank,
            
            payment_purpose_ru=application_data.payment_purpose_ru,
            payment_purpose_en=application_data.payment_purpose_en,
            payment_category_golomt=application_data.payment_category_golomt,
            payment_category_td=application_data.payment_category_td,
            goods_description_en=application_data.goods_description_en,
            
            contract_date=datetime.datetime.strptime(application_data.contract_date, "%d.%m.%Y").date() if application_data.contract_date else None,
            contract_name=application_data.contract_name,
            contract_number=application_data.contract_number,
            vat_exempt=True if application_data.vat_exempt and application_data.vat_exempt == "true" else False if application_data.vat_exempt and application_data.vat_exempt == "false" else None,
            vat_percentage=float(application_data.vat_percentage) if application_data.vat_percentage else None,
            vat_amount=float(application_data.vat_amount) if application_data.vat_amount else None,
            priority=application_data.priority,
            company_name_latin=application_data.company_name_latin,
            company_name_national=application_data.company_name_national,
            company_legal_form=application_data.company_legal_form,
            company_address_latin=application_data.company_address_latin,
            company_registration_number=application_data.company_registration_number,
            company_tax_number=application_data.company_tax_number,
            company_internal_identifier=application_data.company_internal_identifier,
            recipient_first_name=application_data.recipient_first_name,
            recipient_last_name=application_data.recipient_last_name,
            recipient_id_number=application_data.recipient_id_number,
            recipient_phone=application_data.recipient_phone,
            recipient_website=application_data.recipient_website,
            transaction_confirmation_type=application_data.transaction_confirmation_type,
            
            recipient_bank_name_latin=application_data.recipient_bank_name_latin,
            recipient_bank_name_national=application_data.recipient_bank_name_national,
            recipient_bank_legal_form=application_data.recipient_bank_legal_form,
            recipient_bank_registration_number=application_data.recipient_bank_registration_number,
            recipient_account_or_iban=application_data.recipient_account_or_iban,
            recipient_swift=application_data.recipient_swift,
            recipient_bic=application_data.recipient_bic,
            recipient_bank_code=application_data.recipient_bank_code,
            recipient_bank_branch=application_data.recipient_bank_branch,
            spfs=application_data.spfs,
            cips=application_data.cips,
            recipient_bank_address=application_data.recipient_bank_address,
            
            sender_company_name_latin=application_data.sender_company_name_latin,
            sender_company_name_national=application_data.sender_company_name_national,
            sender_company_legal_form=application_data.sender_company_legal_form,
            sender_country=COUNTRY_MAPPING[application_data.sender_country] if application_data.sender_country else None,
            
            comment=application_data.comment,
        )
        
        await NotificationService.notify(
            session=session,
            
            requester_user_id=user_data["user_id"],
            requester_user_uuid=user_data["user_uuid"],
            requester_user_privilege=user_data["privilege_id"],
            
            subject="Заявка",
            subject_uuid=new_application_with_data[0][0].uuid,
            for_admin=True if user_data["privilege_id"] != PRIVILEGE_MAPPING["Admin"] else False,
            data=(f'Пользователь "<user>" ({user_data["user_uuid"]})' if user_data["privilege_id"] != PRIVILEGE_MAPPING["Admin"] else "Администратор") + f' создал Заявку "<application>" ({new_application_with_data[0][0].uuid}). Контрагент - "<counterparty>" ({counterparty_uuid}).',
            recipient_user_uuid=None if user_data["privilege_id"] != PRIVILEGE_MAPPING["Admin"] else user_uuid,
            request_options={
                "<user>": {
                    "uuid": user_data["user_uuid"],
                },
                "<application>": {
                    "uuid": new_application_with_data[0][0].uuid,
                },
                "<counterparty>": {
                    "uuid": counterparty_uuid,
                },
            } if user_data["privilege_id"] != PRIVILEGE_MAPPING["Admin"] else {
                "<application>": {
                    "uuid": new_application_with_data[0][0].uuid,
                },
                "<counterparty>": {
                    "uuid": counterparty_uuid,
                },
            },
        )
        
        return JSONResponse(
            content={
                "msg": "Заявка успешно создана.",
                "data": {
                    "uuid": new_application_with_data[0][0].uuid,
                }
            }
        )
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
                endpoint="create_application",
                params={
                    "application_data": application_data.model_dump() if application_data else application_data,
                    "counterparty_uuid": counterparty_uuid,
                    "user_uuid": user_uuid,
                    "new_directory_uuid": new_directory_uuid,
                },
                msg=f"{error_message}\n{formatted_traceback}",
                user_uuid=user_data["user_uuid"],
            )
            
            response_content = {"msg": f"ОШИБКА! #{log_id}"}
            return JSONResponse(content=response_content)
    finally:
        await session.rollback()

@router.post(
    "/get_applications",
    description="""
    Получение основной информации Заявок.
    
    filter: FiltersApplications
    order: OrdersApplications
    state: ClientState
    output: ResponseGetMTApplications
    """,
    dependencies=[Depends(check_app_auth)],
)
@limiter.limit("30/second")
async def get_applications(
    request: Request,
    counterparty_uuid: Optional[str] = Query(
        None,
        description="(Опционально) Фильтр по UUID Контрагента, по которому будут искаться Заявки (точное совпадение).",
        min_length=36,
        max_length=36
    ),
    
    user_uuid: Optional[str] = Query(
        None,
        description="(Опционально) Фильтр по UUID Пользователя, по которому будут искаться Заявки (точное совпадение).",
        min_length=36,
        max_length=36
    ),
    
    extended_output: bool = Query(
        False,
        description="Выдача ответа с дополнительной информацией."
    ),
    user_login_ilike: Optional[str] = Query(
        None,
        description="(Опционально, если extended_output==true (!)) Фильтр для поиска по логину пользователя (частичное совпадение)."
    ),
    
    legal_entity_name: Optional[str] = Query(
        None,
        description="(Опционально, если extended_output==true (!)) Фильтр для поиска по наименованию Контрагента(ЮЛ) (латиница/национальное написание)."
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
    
    filter: Optional[FiltersApplications] = None,
    order: Optional[OrdersApplications] = None,
    
    token: str = Depends(UserQaSM.get_current_user_data),
    
    session: AsyncSession = Depends(get_async_session),
    
    client_state: Optional[ClientState] = None,
) -> ResponseGetMTApplications:
    try:
        user_data: Dict[str, str|int] = token.model_dump()   # Парсинг данных пользователя
        
        if client_state is None:
            client_state: ClientState = await UserService.get_client_state(
                requester_user_uuid=user_data["user_uuid"],
                requester_user_privilege=user_data["privilege_id"],
                user_uuid=user_data["user_uuid"],
            )
        client_state_data: Dict[str, Any] = client_state.model_dump()["data"]
        
        applications: Dict[str, List[Optional[Application]]|Optional[int]] = await MTApplicationService.get_applications(
            session=session,
            
            requester_user_uuid=user_data["user_uuid"],
            requester_user_privilege=user_data["privilege_id"],
            user_uuid=user_uuid,
            counterparty_uuid=counterparty_uuid,
            
            extended_output=extended_output,
            
            user_login_ilike=user_login_ilike,
            legal_entity_name=legal_entity_name,
            
            page=page,
            page_size=page_size,
            
            filter=filter,
            order=order,
        )
        
        response_content = ResponseGetMTApplications(
            data=[],
            count=0,
            total_records=None,
            total_pages=None,
        )
        
        for application in applications["data"]:  # FIXME
            if extended_output:
                response_content.data.append(
                    ExtendedMTApplication(
                        uuid=application["application"].uuid,
                        name=application["application"].name,
                        
                        mt_type=list(MT_APPLICATION_TYPE_MAPPING)[list(MT_APPLICATION_TYPE_MAPPING.values()).index(application["type"])] if application.get("type") else application["type"],
                        priority=application["priority"],
                        user_login=application["login"],
                        legal_entity_name_latin=application["name_latin"],
                        legal_entity_name_national=application["name_national"],
                        data_updated_at=convert_tz(application["updated_at"].strftime("%d.%m.%Y %H:%M:%S UTC"), tz_city=client_state_data.get("tz")) if application["updated_at"] else None,
                        order_name=application["order_name"],
                        # TODO тут можно добавить вывод полей (согласовать с Юрием)
                        
                        user_id=application["application"].user_id,
                        user_uuid=application["application"].user_uuid,
                        counterparty_id=application["application"].counterparty_id,
                        counterparty_uuid=application["application"].counterparty_uuid,
                        directory_id=application["application"].directory_id,
                        directory_uuid=application["application"].directory_uuid,
                        type="MT",
                        status=list(APPLICATION_STATUS_MAPPING)[list(APPLICATION_STATUS_MAPPING.values()).index(application["application"].status)] if application["application"].status else application["application"].status,
                        data_id=application["application"].data_id,  # FIXME это возможно не стоит возвращать
                        can_be_updated_by_user=application["application"].can_be_updated_by_user,
                        updated_at=convert_tz(application["application"].updated_at.strftime("%d.%m.%Y %H:%M:%S UTC"), tz_city=client_state_data.get("tz")) if application["application"].updated_at else None,
                        created_at=convert_tz(application["application"].created_at.strftime("%d.%m.%Y %H:%M:%S UTC"), tz_city=client_state_data.get("tz")) if application["application"].created_at else None,
                    )
                )
            else:
                response_content.data.append(
                    BaseApplication(
                        uuid=application.uuid,
                        name=application.name,
                        user_id=application.user_id,
                        user_uuid=application.user_uuid,
                        counterparty_id=application.counterparty_id,
                        counterparty_uuid=application.counterparty_uuid,
                        directory_id=application.directory_id,
                        directory_uuid=application.directory_uuid,
                        type="MT",
                        status=list(APPLICATION_STATUS_MAPPING)[list(APPLICATION_STATUS_MAPPING.values()).index(application.status)] if application.status else application.status,
                        data_id=application.data_id,  # FIXME это возможно не стоит возвращать
                        can_be_updated_by_user=application.can_be_updated_by_user,
                        updated_at=convert_tz(application.updated_at.strftime("%d.%m.%Y %H:%M:%S UTC"), tz_city=client_state_data.get("tz")) if application.updated_at else None,
                        created_at=convert_tz(application.created_at.strftime("%d.%m.%Y %H:%M:%S UTC"), tz_city=client_state_data.get("tz")) if application.created_at else None,
                    )
                )
            response_content.count += 1
        response_content.total_records = applications["total_records"]
        response_content.total_pages = applications["total_pages"]
        
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
                endpoint="get_applications",
                params={
                    "counterparty_uuid": counterparty_uuid,
                    "user_uuid": user_uuid,
                    "extended_output": extended_output,
                    "user_login_ilike": user_login_ilike,
                    "legal_entity_name": legal_entity_name,
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

@router.post(
    "/get_applications_data",
    description="""
    Получение подробной информации Заявки.
    
    state: ClientState
    """,
    dependencies=[Depends(check_app_auth)],
)
@limiter.limit("30/second")
async def get_applications_data(
    request: Request,
    application_uuid_list: List[Optional[str]] = Query(
        [],
        description="(Опционально) Массив UUID, подробные данные которых нужно получить."
    ),
    counterparty_uuid: Optional[str] = Query(
        None,
        description="(Опционально для Админа) Фильтр по UUID Контрагента, по Заявкам которого будет взята подробная информация (точное совпадение).",
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
        
        applications_data: List[Optional[MTApplicationData]] = await MTApplicationService.get_applications_data(
            session=session,
            
            requester_user_uuid=user_data["user_uuid"],
            requester_user_privilege=user_data["privilege_id"],
            
            application_uuid_list=application_uuid_list,
            counterparty_uuid=counterparty_uuid,
        )
        
        response_content = {"data": {}, "count": 0}
        
        for application_data in applications_data:
            response_content["count"] += 1
            response_content["data"][application_data.id] = {
                "order_name": application_data.order_name,
                
                "payment_deadline_not_earlier_than": datetime.datetime.strftime(application_data.payment_deadline_not_earlier_than, "%d.%m.%Y") if application_data.payment_deadline_not_earlier_than else None,
                "payment_deadline_no_later_than": datetime.datetime.strftime(application_data.payment_deadline_no_later_than, "%d.%m.%Y") if application_data.payment_deadline_no_later_than else None,
                "invoice_date": datetime.datetime.strftime(application_data.invoice_date, "%d.%m.%Y") if application_data.invoice_date else None,
                
                "type":  {v:k for k, v in MT_APPLICATION_TYPE_MAPPING.items()}[application_data.type],
                
                "invoice_currency": {v:k for k, v in CURRENCY_MAPPING.items()}[application_data.invoice_currency] if application_data.invoice_currency else None,
                "invoice_amount": str(float(application_data.invoice_amount)) if application_data.invoice_amount else None,
                "payment_amount": str(float(application_data.payment_amount)) if application_data.payment_amount else None,
                "payment_amount_in_words": application_data.payment_amount_in_words,
                "partial_payment_allowed": application_data.partial_payment_allowed,
                "invoice_number": application_data.invoice_number,
                
                "amount_to_withdraw": str(float(application_data.amount_to_withdraw)) if application_data.amount_to_withdraw else None,
                "amount_to_replenish": str(float(application_data.amount_to_replenish)) if application_data.amount_to_replenish else None,
                "amount_to_principal": str(float(application_data.amount_to_principal)) if application_data.amount_to_principal else None,
                "amount_credited": str(float(application_data.amount_credited)) if application_data.amount_credited else None,
                "is_amount_different": application_data.is_amount_different,
                "source_bank": application_data.source_bank,
                "target_bank": application_data.target_bank,
                "source_currency": {v:k for k, v in CURRENCY_MAPPING.items()}[application_data.source_currency] if application_data.source_currency else None,
                "target_currency": {v:k for k, v in CURRENCY_MAPPING.items()}[application_data.target_currency] if application_data.target_currency else None,
                "amount": str(float(application_data.amount)) if application_data.amount else None,
                "subagent_bank": application_data.subagent_bank,
                "payment_purpose_ru": application_data.payment_purpose_ru,
                "payment_purpose_en": application_data.payment_purpose_en,
                "payment_category_golomt": application_data.payment_category_golomt,
                "payment_category_td": application_data.payment_category_td,
                "goods_description_en": application_data.goods_description_en,
                
                "contract_date": datetime.datetime.strftime(application_data.contract_date, "%d.%m.%Y") if application_data.contract_date else None,
                "contract_name": application_data.contract_name,
                "contract_number": application_data.contract_number,
                "vat_exempt": application_data.vat_exempt,
                "vat_percentage": str(float(application_data.vat_percentage)) if application_data.vat_percentage else None,
                "vat_amount": str(float(application_data.vat_amount)) if application_data.vat_amount else None,
                "priority": application_data.priority,
                
                "end_customer_company_name": application_data.end_customer_company_name,
                "end_customer_company_legal_form": application_data.end_customer_company_legal_form,
                "end_customer_company_registration_country": {v:k for k, v in COUNTRY_MAPPING.items()}[application_data.end_customer_company_registration_country] if application_data.end_customer_company_registration_country else None,
                
                "company_name_latin": application_data.company_name_latin,
                "company_name_national": application_data.company_name_national,
                "company_legal_form": application_data.company_legal_form,
                "company_address_latin": application_data.company_address_latin,
                "company_registration_number": application_data.company_registration_number,
                "company_tax_number": application_data.company_tax_number,
                "company_internal_identifier": application_data.company_internal_identifier,
                "recipient_first_name": application_data.recipient_first_name,
                "recipient_last_name": application_data.recipient_last_name,
                "recipient_id_number": application_data.recipient_id_number,
                "recipient_phone": application_data.recipient_phone,
                "recipient_website": application_data.recipient_website,
                "transaction_confirmation_type": application_data.transaction_confirmation_type,
                
                "recipient_bank_name_latin": application_data.recipient_bank_name_latin,
                "recipient_bank_name_national": application_data.recipient_bank_name_national,
                "recipient_bank_legal_form": application_data.recipient_bank_legal_form,
                "recipient_bank_registration_number": application_data.recipient_bank_registration_number,
                "recipient_account_or_iban": application_data.recipient_account_or_iban,
                "recipient_swift": application_data.recipient_swift,
                "recipient_bic": application_data.recipient_bic,
                "recipient_bank_code": application_data.recipient_bank_code,
                "recipient_bank_branch": application_data.recipient_bank_branch,
                "spfs": application_data.spfs,
                "cips": application_data.cips,
                "recipient_bank_address": application_data.recipient_bank_address,
                
                "sender_company_name_latin": application_data.sender_company_name_latin,
                "sender_company_name_national": application_data.sender_company_name_national,
                "sender_company_legal_form": application_data.sender_company_legal_form,
                "sender_country": {v:k for k, v in COUNTRY_MAPPING.items()}[application_data.sender_country] if application_data.sender_country else None,
                
                "comment": application_data.comment,
                "updated_at": convert_tz(datetime.datetime.strftime(application_data.updated_at, "%d.%m.%Y %H:%M:%S UTC"), tz_city=client_state_data.get("tz")) if application_data.updated_at else None,
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
                endpoint="get_applications_data",
                params={
                    "application_uuid_list": application_uuid_list,
                    "counterparty_uuid": counterparty_uuid,
                },
                msg=f"{error_message}\n{formatted_traceback}",
                user_uuid=user_data["user_uuid"],
            )
            
            response_content = {"msg": f"ОШИБКА! #{log_id}"}
            return JSONResponse(content=response_content)
    finally:
        await session.rollback()

@router.put(
    "/update_application_data",
    description="""
    Обновление подробной информации Заявки.
    
    input: UpdateApplicationDataSchema
    """,
    dependencies=[Depends(check_app_auth)],
)
@limiter.limit("30/second")
async def update_application_data(
    request: Request,
    data_for_update: UpdateMTApplicationDataSchema,
    
    application_uuid: str = Query(
        ...,
        description="UUID-Заявки, в которой будут обновления подробной информации.",
        min_length=36,
        max_length=36
    ),
    
    token: str = Depends(UserQaSM.get_current_user_data),
    
    session: AsyncSession = Depends(get_async_session),
) -> JSONResponse:
    try:
        user_data: Dict[str, str|int] = token.model_dump()   # Парсинг данных пользователя
        
        await MTApplicationService.update_application_data(
            session=session,
            
            requester_user_uuid=user_data["user_uuid"],
            requester_user_privilege=user_data["privilege_id"],
            
            application_uuid=application_uuid,
            
            order_name=data_for_update.order_name,
            payment_deadline_not_earlier_than=data_for_update.payment_deadline_not_earlier_than,
            payment_deadline_no_later_than=data_for_update.payment_deadline_no_later_than,
            invoice_date=data_for_update.invoice_date,
            invoice_currency=data_for_update.invoice_currency,
            invoice_amount=data_for_update.invoice_amount,
            payment_amount=data_for_update.payment_amount,
            payment_amount_in_words=data_for_update.payment_amount_in_words,
            partial_payment_allowed=data_for_update.partial_payment_allowed,
            invoice_number=data_for_update.invoice_number,
            amount_to_withdraw=data_for_update.amount_to_withdraw,
            amount_to_replenish=data_for_update.amount_to_replenish,
            amount_to_principal=data_for_update.amount_to_principal,
            amount_credited=data_for_update.amount_credited,
            is_amount_different=data_for_update.is_amount_different,
            source_bank=data_for_update.source_bank,
            target_bank=data_for_update.target_bank,
            source_currency=data_for_update.source_currency,
            target_currency=data_for_update.target_currency,
            amount=data_for_update.amount,
            subagent_bank=data_for_update.subagent_bank,
            payment_purpose_ru=data_for_update.payment_purpose_ru,
            payment_purpose_en=data_for_update.payment_purpose_en,
            payment_category_golomt=data_for_update.payment_category_golomt,
            payment_category_td=data_for_update.payment_category_td,
            goods_description_en=data_for_update.goods_description_en,
            contract_date=data_for_update.contract_date,
            contract_name=data_for_update.contract_name,
            contract_number=data_for_update.contract_number,
            vat_exempt=data_for_update.vat_exempt,
            vat_percentage=data_for_update.vat_percentage,
            vat_amount=data_for_update.vat_amount,
            priority=data_for_update.priority,
            end_customer_company_name=data_for_update.end_customer_company_name,
            end_customer_company_legal_form=data_for_update.end_customer_company_legal_form,
            end_customer_company_registration_country=data_for_update.end_customer_company_registration_country,
            company_name_latin=data_for_update.company_name_latin,
            company_name_national=data_for_update.company_name_national,
            company_legal_form=data_for_update.company_legal_form,
            company_address_latin=data_for_update.company_address_latin,
            company_registration_number=data_for_update.company_registration_number,
            company_tax_number=data_for_update.company_tax_number,
            company_internal_identifier=data_for_update.company_internal_identifier,
            recipient_first_name=data_for_update.recipient_first_name,
            recipient_last_name=data_for_update.recipient_last_name,
            recipient_id_number=data_for_update.recipient_id_number,
            recipient_phone=data_for_update.recipient_phone,
            recipient_website=data_for_update.recipient_website,
            transaction_confirmation_type=data_for_update.transaction_confirmation_type,
            recipient_bank_name_latin=data_for_update.recipient_bank_name_latin,
            recipient_bank_name_national=data_for_update.recipient_bank_name_national,
            recipient_bank_legal_form=data_for_update.recipient_bank_legal_form,
            recipient_bank_registration_number=data_for_update.recipient_bank_registration_number,
            recipient_account_or_iban=data_for_update.recipient_account_or_iban,
            recipient_swift=data_for_update.recipient_swift,
            recipient_bic=data_for_update.recipient_bic,
            recipient_bank_code=data_for_update.recipient_bank_code,
            recipient_bank_branch=data_for_update.recipient_bank_branch,
            spfs=data_for_update.spfs,
            cips=data_for_update.cips,
            recipient_bank_address=data_for_update.recipient_bank_address,
            sender_company_name_latin=data_for_update.sender_company_name_latin,
            sender_company_name_national=data_for_update.sender_company_name_national,
            sender_company_legal_form=data_for_update.sender_company_legal_form,
            sender_country=data_for_update.sender_country,
            comment=data_for_update.comment,
        )
        
        if user_data["privilege_id"] == PRIVILEGE_MAPPING["Admin"]:
            recipient_user_uuid = await ApplicationQueryAndStatementManager.get_user_uuid_by_application_uuid(
                session=session,
                
                application_uuid=application_uuid,
            )
        await NotificationService.notify(
            session=session,
            
            requester_user_id=user_data["user_id"],
            requester_user_uuid=user_data["user_uuid"],
            requester_user_privilege=user_data["privilege_id"],
            
            subject="Заявка",
            subject_uuid=application_uuid,
            for_admin=True if user_data["privilege_id"] != PRIVILEGE_MAPPING["Admin"] else False,
            data=(f'Пользователь "<user>" ({user_data["user_uuid"]})' if user_data["privilege_id"] != PRIVILEGE_MAPPING["Admin"] else "Администратор") + f' внес изменения в данные о Заявке "<application>" ({application_uuid}).',
            recipient_user_uuid=None if user_data["privilege_id"] != PRIVILEGE_MAPPING["Admin"] else recipient_user_uuid,
            request_options={
                "<user>": {
                    "uuid": user_data["user_uuid"],
                },
                "<application>": {
                    "uuid": application_uuid,
                },
            } if user_data["privilege_id"] != PRIVILEGE_MAPPING["Admin"] else {
                "<application>": {
                    "uuid": application_uuid,
                },
            },
        )
        
        return JSONResponse(content={"msg": "Данные Заявки успешно обновлены."})
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
                endpoint="update_application_data",
                params={
                    "data_for_update": data_for_update.model_dump() if data_for_update else data_for_update,
                    "application_uuid": application_uuid,
                },
                msg=f"{error_message}\n{formatted_traceback}",
                user_uuid=user_data["user_uuid"],
            )
            
            response_content = {"msg": f"ОШИБКА! #{log_id}"}
            return JSONResponse(content=response_content)
    finally:
        await session.rollback()
