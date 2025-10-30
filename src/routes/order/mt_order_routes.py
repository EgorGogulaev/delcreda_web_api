import datetime
import traceback
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import JSONResponse

from connection_module import get_async_session
from lifespan import limiter
from security import check_app_auth
from src.query_and_statement.order.mt_order_qas_manager import MTOrderQueryAndStatementManager
from src.schemas.user_schema import ClientState
from src.service.user_service import UserService
from src.service.reference_service import ReferenceService
from src.schemas.order.order_schema import BaseOrder, FiltersOrders, OrdersOrders
from src.schemas.order.mt_order_schema import ResponseGetMTOrders
from src.schemas.order.mt_order_schema import ExtendedMTOrder,  CreateMTOrderDataSchema,  UpdateMTOrderDataSchema
from src.service.notification_service import NotificationService
from src.models.order.order_models import Order
from src.models.order.mt_models import MTOrderData
from service.order.mt_order_service import MTOrderService
from src.query_and_statement.user_qas_manager import UserQueryAndStatementManager as UserQaSM
from src.utils.reference_mapping_data.app.app_mapping_data import COUNTRY_MAPPING, CURRENCY_MAPPING
from src.utils.reference_mapping_data.order.order.mt_mapping import MT_ORDER_TYPE_MAPPING
from src.utils.reference_mapping_data.order.mapping import ORDER_STATUS_MAPPING
from src.utils.reference_mapping_data.user.mapping import PRIVILEGE_MAPPING
from src.utils.tz_converter import convert_tz


router = APIRouter(
    prefix="/mt",
    tags=["MTOrder"],
)

@router.post(
    "/create_order",
    description="""
    Создание Поручения.
    
    input: CreateMTOrderDataSchema
    """,
    dependencies=[Depends(check_app_auth)],
)
@limiter.limit("3/second")
async def create_order(
    request: Request,
    order_data: CreateMTOrderDataSchema,
    legal_entity_uuid: str = Query(
        ...,
        description="UUID ЮЛ по которому создается MT-Поручение.",
        min_length=36,
        max_length=36
    ),
    user_uuid: str = Query(
        ...,
        description="UUID Пользователя-владельца ЮЛ по которому создается MT-Поручение.",
        min_length=36,
        max_length=36
    ),
    new_directory_uuid: Optional[str] = Query(
        None,
        description="(Опиционально) Ручное выставление нового UUID для Директории под новое MT-Поручение. (нужно для интеграции в другие системы)",
        min_length=36,
        max_length=36
    ),
    
    token: str = Depends(UserQaSM.get_current_user_data),
    
    session: AsyncSession = Depends(get_async_session),
) -> JSONResponse:
    try:
        user_data: Dict[str, str|int] = token.model_dump()   # Парсинг данных пользователя
        
        new_order_with_data: Tuple[Tuple[Order, MTOrderData], Dict[str, str|int]] = await MTOrderService.create_order(
            session=session,
            
            requester_user_uuid=user_data["user_uuid"],
            requester_user_privilege=user_data["privilege_id"],
            
            user_uuid=user_uuid,
            legal_entity_uuid=legal_entity_uuid,
            new_directory_uuid=new_directory_uuid,
            
            # OrderData
            payment_deadline_not_earlier_than=datetime.datetime.strptime(order_data.payment_deadline_not_earlier_than, "%d.%m.%Y").date() if order_data.payment_deadline_not_earlier_than else None,
            payment_deadline_no_later_than=datetime.datetime.strptime(order_data.payment_deadline_no_later_than, "%d.%m.%Y").date() if order_data.payment_deadline_no_later_than else None,
            invoice_date=datetime.datetime.strptime(order_data.invoice_date, "%d.%m.%Y").date() if order_data.invoice_date else None,
            
            type=MT_ORDER_TYPE_MAPPING[order_data.type],
            
            invoice_currency=CURRENCY_MAPPING[order_data.invoice_currency] if order_data.invoice_currency else None,
            invoice_amount=float(order_data.invoice_amount) if order_data.invoice_amount else None,
            payment_amount=float(order_data.payment_amount) if order_data.payment_amount else None,
            payment_amount_in_words=order_data.payment_amount_in_words,
            partial_payment_allowed=True if order_data.partial_payment_allowed and order_data.partial_payment_allowed == "true" else False if order_data.partial_payment_allowed and order_data.partial_payment_allowed == "false" else None,  # FIXME протестить
            invoice_number=order_data.invoice_number,
            
            amount_to_withdraw=order_data.amount_to_withdraw,
            amount_to_replenish=order_data.amount_to_replenish,
            amount_to_principal=order_data.amount_to_principal,
            amount_credited=order_data.amount_credited,
            is_amount_different=True if order_data.is_amount_different and order_data.is_amount_different == "true" else False if order_data.is_amount_different and order_data.is_amount_different == "false" else None,  # FIXME протестить
            source_bank=order_data.source_bank,
            target_bank=order_data.target_bank,
            source_currency=CURRENCY_MAPPING[order_data.source_currency] if order_data.source_currency else None,
            target_currency=CURRENCY_MAPPING[order_data.target_currency] if order_data.target_currency else None,
            amount=order_data.amount,
            subagent_bank=order_data.subagent_bank,
            
            payment_purpose_ru=order_data.payment_purpose_ru,
            payment_purpose_en=order_data.payment_purpose_en,
            payment_category_golomt=order_data.payment_category_golomt,
            payment_category_td=order_data.payment_category_td,
            goods_description_en=order_data.goods_description_en,
            
            contract_date=datetime.datetime.strptime(order_data.contract_date, "%d.%m.%Y").date() if order_data.contract_date else None,
            contract_name=order_data.contract_name,
            contract_number=order_data.contract_number,
            vat_exempt=True if order_data.vat_exempt and order_data.vat_exempt == "true" else False if order_data.vat_exempt and order_data.vat_exempt == "false" else None,  # FIXME протестить
            vat_percentage=float(order_data.vat_percentage) if order_data.vat_percentage else None,
            vat_amount=float(order_data.vat_amount) if order_data.vat_amount else None,
            priority=order_data.priority,
            company_name_latin=order_data.company_name_latin,
            company_name_national=order_data.company_name_national,
            company_legal_form=order_data.company_legal_form,
            company_address_latin=order_data.company_address_latin,
            company_registration_number=order_data.company_registration_number,
            company_tax_number=order_data.company_tax_number,
            company_internal_identifier=order_data.company_internal_identifier,
            recipient_first_name=order_data.recipient_first_name,
            recipient_last_name=order_data.recipient_last_name,
            recipient_id_number=order_data.recipient_id_number,
            recipient_phone=order_data.recipient_phone,
            recipient_website=order_data.recipient_website,
            transaction_confirmation_type=order_data.transaction_confirmation_type,
            
            recipient_bank_name_latin=order_data.recipient_bank_name_latin,
            recipient_bank_name_national=order_data.recipient_bank_name_national,
            recipient_bank_legal_form=order_data.recipient_bank_legal_form,
            recipient_bank_registration_number=order_data.recipient_bank_registration_number,
            recipient_account_or_iban=order_data.recipient_account_or_iban,
            recipient_swift=order_data.recipient_swift,
            recipient_bic=order_data.recipient_bic,
            recipient_bank_code=order_data.recipient_bank_code,
            recipient_bank_branch=order_data.recipient_bank_branch,
            spfs=order_data.spfs,
            cips=order_data.cips,
            recipient_bank_address=order_data.recipient_bank_address,
            
            sender_company_name_latin=order_data.sender_company_name_latin,
            sender_company_name_national=order_data.sender_company_name_national,
            sender_company_legal_form=order_data.sender_company_legal_form,
            sender_country=COUNTRY_MAPPING[order_data.sender_country] if order_data.sender_country else None,
            
            comment=order_data.comment,
        )
        
        await NotificationService.notify(
            session=session,
            
            requester_user_id=user_data["user_id"],
            requester_user_uuid=user_data["user_uuid"],
            requester_user_privilege=user_data["privilege_id"],
            
            subject="Поручение",
            subject_uuid=new_order_with_data[0][0].uuid,
            for_admin=True if user_data["privilege_id"] != PRIVILEGE_MAPPING["Admin"] else False,
            data=f'Пользователь "{user_data["user_uuid"]}" создал Поручение с ID "{new_order_with_data[0][0].id}".',
            recipient_user_uuid=None if user_data["privilege_id"] != PRIVILEGE_MAPPING["Admin"] else user_uuid,
        )
        
        return JSONResponse(
            content={
                "msg": "Поручение успешно создано.",
                "data": {
                    "uuid": new_order_with_data[0][0].uuid,
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
                endpoint="create_order",
                params={
                    "order_data": order_data.model_dump() if order_data else order_data,
                    "legal_entity_uuid": legal_entity_uuid,
                    "user_uuid": user_uuid,
                    "new_directory_uuid": new_directory_uuid,
                },
                msg=f"{error_message}\n{formatted_traceback}",
                user_uuid=user_data["user_uuid"],
            )
            
            response_content = {"msg": f"ОШИБКА! #{log_id}"}
            return JSONResponse(content=response_content)

@router.post(
    "/get_orders",
    description="""
    Получение основной информации Поручений.
    
    filter: FiltersOrders
    order: OrdersOrders
    state: ClientState
    output: ResponseGetMTOrders
    """,
    dependencies=[Depends(check_app_auth)],
)
@limiter.limit("3/second")
async def get_orders(
    request: Request,
    legal_entity_uuid: Optional[str] = Query(
        None,
        description="(Опционально) Фильтр по UUID ЮЛ, по которому будут искаться Поручения (точное совпадение).",
        min_length=36,
        max_length=36
    ),
    
    user_uuid: Optional[str] = Query(
        None,
        description="(Опционально) Фильтр по UUID Пользователя, по которому будут искаться Поручения (точное совпадение).",
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
        description="(Опционально, если extended_output==true (!)) Фильтр для поиска по наименованию ЮЛ (латиница/национальное написание)."
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
    
    filter: Optional[FiltersOrders] = None,
    order: Optional[OrdersOrders] = None,
    
    token: str = Depends(UserQaSM.get_current_user_data),
    
    session: AsyncSession = Depends(get_async_session),
    
    client_state: Optional[ClientState] = None,
) -> ResponseGetMTOrders:
    try:
        user_data: Dict[str, str|int] = token.model_dump()   # Парсинг данных пользователя
        
        if client_state is None:
            client_state: ClientState = await UserService.get_client_state(
                requester_user_uuid=user_data["user_uuid"],
                requester_user_privilege=user_data["privilege_id"],
                user_uuid=user_data["user_uuid"],
            )
        client_state_data: Dict[str, Any] = client_state.model_dump()["data"]
        
        orders: Dict[str, List[Optional[Order]]|Optional[int]] = await MTOrderService.get_orders(
            session=session,
            
            requester_user_uuid=user_data["user_uuid"],
            requester_user_privilege=user_data["privilege_id"],
            user_uuid=user_uuid,
            legal_entity_uuid=legal_entity_uuid,
            
            extended_output=extended_output,
            
            user_login_ilike=user_login_ilike,
            legal_entity_name=legal_entity_name,
            
            page=page,
            page_size=page_size,
            
            filter=filter,
            order=order,
        )
        
        response_content = ResponseGetMTOrders(
            data=[],
            count=0,
            total_records=None,
            total_pages=None,
        )
        
        for order_ in orders["data"]:
            if extended_output:
                response_content.data.append(
                    ExtendedMTOrder(
                        uuid=order_["order"].uuid,
                        name=order_["order"].name,
                        
                        type=list(MT_ORDER_TYPE_MAPPING)[list(MT_ORDER_TYPE_MAPPING.values()).index(order_["type"])] if order_.get("type") else order_["type"],
                        priority=order_["priority"],
                        user_login=order_["login"],
                        legal_entity_name_latin=order_["name_latin"],
                        legal_entity_name_national=order_["name_national"],
                        data_updated_at=convert_tz(order_["updated_at"].strftime("%d.%m.%Y %H:%M:%S UTC"), tz_city=client_state_data.get("tz")) if order_["updated_at"] else None,
                        # TODO тут можно добавить вывод полей (согласовать с Юрием)
                        
                        user_id=order_["order"].user_id,
                        user_uuid=order_["order"].user_uuid,
                        legal_entity_id=order_["order"].legal_entity_id,
                        legal_entity_uuid=order_["order"].legal_entity_uuid,
                        directory_id=order_["order"].directory_id,
                        directory_uuid=order_["order"].directory_uuid,
                        status=list(ORDER_STATUS_MAPPING)[list(ORDER_STATUS_MAPPING.values()).index(order_["order"].status)] if order_["order"].status else order_["order"].status,
                        data_id=order_["order"].data_id,  # FIXME это возможно не стоит возвращать
                        can_be_updated_by_user=order_["order"].can_be_updated_by_user,
                        updated_at=convert_tz(order_["order"].updated_at.strftime("%d.%m.%Y %H:%M:%S UTC"), tz_city=client_state_data.get("tz")) if order_["order"].updated_at else None,
                        created_at=convert_tz(order_["order"].created_at.strftime("%d.%m.%Y %H:%M:%S UTC"), tz_city=client_state_data.get("tz")) if order_["order"].created_at else None,
                    )
                )
            else:
                response_content.data.append(
                    BaseOrder(
                        uuid=order_.uuid,
                        name=order_.name,
                        user_id=order_.user_id,
                        user_uuid=order_.user_uuid,
                        legal_entity_id=order_.legal_entity_id,
                        legal_entity_uuid=order_.legal_entity_uuid,
                        directory_id=order_.directory_id,
                        directory_uuid=order_.directory_uuid,
                        status=list(ORDER_STATUS_MAPPING)[list(ORDER_STATUS_MAPPING.values()).index(order_.status)] if order_.status else order_.status,
                        data_id=order_.data_id,  # FIXME это возможно не стоит возвращать
                        can_be_updated_by_user=order_.can_be_updated_by_user,
                        updated_at=convert_tz(order_.updated_at.strftime("%d.%m.%Y %H:%M:%S UTC"), tz_city=client_state_data.get("tz")) if order_.updated_at else None,
                        created_at=convert_tz(order_.created_at.strftime("%d.%m.%Y %H:%M:%S UTC"), tz_city=client_state_data.get("tz")) if order_.created_at else None,
                    )
                )
            response_content.count += 1
        response_content.total_records = orders["total_records"]
        response_content.total_pages = orders["total_pages"]
        
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
                endpoint="get_orders",
                params={
                    "legal_entity_uuid": legal_entity_uuid,
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

@router.post(
    "/get_orders_data",
    description="""
    Получение подробной информации о Поручении.
    
    state: ClientState
    """,
    dependencies=[Depends(check_app_auth)],
)
@limiter.limit("3/second")
async def get_orders_data(
    request: Request,
    order_uuid_list: List[Optional[str]] = Query(
        [],
        description="(Опционально) Массив UUID, подробные данные которых нужно получить."
    ),
    legal_entity_uuid: Optional[str] = Query(
        None,
        description="(Опционально для Админа) Фильтр по UUID ЮЛ, по Поручениям которого будет взята подробная информация (точное совпадение).",
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
        
        orders_data: List[Optional[MTOrderData]] = await MTOrderService.get_orders_data(
            session=session,
            
            requester_user_uuid=user_data["user_uuid"],
            requester_user_privilege=user_data["privilege_id"],
            
            order_uuid_list=order_uuid_list,
            legal_entity_uuid=legal_entity_uuid,
        )
        
        response_content = {"data": {}, "count": 0}
        
        for order_data in orders_data:
            response_content["count"] += 1
            response_content["data"][order_data.id] = {
                "payment_deadline_not_earlier_than": datetime.datetime.strftime(order_data.payment_deadline_not_earlier_than, "%d.%m.%Y") if order_data.payment_deadline_not_earlier_than else None,
                "payment_deadline_no_later_than": datetime.datetime.strftime(order_data.payment_deadline_no_later_than, "%d.%m.%Y") if order_data.payment_deadline_no_later_than else None,
                "invoice_date": datetime.datetime.strftime(order_data.invoice_date, "%d.%m.%Y") if order_data.invoice_date else None,
                
                "type":  {v:k for k, v in MT_ORDER_TYPE_MAPPING.items()}[order_data.type],
                
                "invoice_currency": {v:k for k, v in CURRENCY_MAPPING.items()}[order_data.invoice_currency] if order_data.invoice_currency else None,
                "invoice_amount": str(float(order_data.invoice_amount)) if order_data.invoice_amount else None,
                "payment_amount": str(float(order_data.payment_amount)) if order_data.payment_amount else None,
                "payment_amount_in_words": order_data.payment_amount_in_words,
                "partial_payment_allowed": order_data.partial_payment_allowed,
                "invoice_number": order_data.invoice_number,
                
                "amount_to_withdraw": str(float(order_data.amount_to_withdraw)) if order_data.amount_to_withdraw else None,
                "amount_to_replenish": str(float(order_data.amount_to_replenish)) if order_data.amount_to_replenish else None,
                "amount_to_principal": str(float(order_data.amount_to_principal)) if order_data.amount_to_principal else None,
                "amount_credited": str(float(order_data.amount_credited)) if order_data.amount_credited else None,
                "is_amount_different": order_data.is_amount_different,
                "source_bank": order_data.source_bank,
                "target_bank": order_data.target_bank,
                "source_currency": {v:k for k, v in CURRENCY_MAPPING.items()}[order_data.source_currency] if order_data.source_currency else None,
                "target_currency": {v:k for k, v in CURRENCY_MAPPING.items()}[order_data.target_currency] if order_data.target_currency else None,
                "amount": str(float(order_data.amount)) if order_data.amount else None,
                "subagent_bank": order_data.subagent_bank,
                "payment_purpose_ru": order_data.payment_purpose_ru,
                "payment_purpose_en": order_data.payment_purpose_en,
                "payment_category_golomt": order_data.payment_category_golomt,
                "payment_category_td": order_data.payment_category_td,
                "goods_description_en": order_data.goods_description_en,
                
                "contract_date": datetime.datetime.strftime(order_data.contract_date, "%d.%m.%Y") if order_data.contract_date else None,
                "contract_name": order_data.contract_name,
                "contract_number": order_data.contract_number,
                "vat_exempt": order_data.vat_exempt,
                "vat_percentage": str(float(order_data.vat_percentage)) if order_data.vat_percentage else None,
                "vat_amount": str(float(order_data.vat_amount)) if order_data.vat_amount else None,
                "priority": order_data.priority,
                
                "end_customer_company_name": order_data.end_customer_company_name,
                "end_customer_company_legal_form": order_data.end_customer_company_legal_form,
                "end_customer_company_registration_country": {v:k for k, v in COUNTRY_MAPPING.items()}[order_data.end_customer_company_registration_country] if order_data.end_customer_company_registration_country else None,
                
                "company_name_latin": order_data.company_name_latin,
                "company_name_national": order_data.company_name_national,
                "company_legal_form": order_data.company_legal_form,
                "company_address_latin": order_data.company_address_latin,
                "company_registration_number": order_data.company_registration_number,
                "company_tax_number": order_data.company_tax_number,
                "company_internal_identifier": order_data.company_internal_identifier,
                "recipient_first_name": order_data.recipient_first_name,
                "recipient_last_name": order_data.recipient_last_name,
                "recipient_id_number": order_data.recipient_id_number,
                "recipient_phone": order_data.recipient_phone,
                "recipient_website": order_data.recipient_website,
                "transaction_confirmation_type": order_data.transaction_confirmation_type,
                
                "recipient_bank_name_latin": order_data.recipient_bank_name_latin,
                "recipient_bank_name_national": order_data.recipient_bank_name_national,
                "recipient_bank_legal_form": order_data.recipient_bank_legal_form,
                "recipient_bank_registration_number": order_data.recipient_bank_registration_number,
                "recipient_account_or_iban": order_data.recipient_account_or_iban,
                "recipient_swift": order_data.recipient_swift,
                "recipient_bic": order_data.recipient_bic,
                "recipient_bank_code": order_data.recipient_bank_code,
                "recipient_bank_branch": order_data.recipient_bank_branch,
                "spfs": order_data.spfs,
                "cips": order_data.cips,
                "recipient_bank_address": order_data.recipient_bank_address,
                
                "sender_company_name_latin": order_data.sender_company_name_latin,
                "sender_company_name_national": order_data.sender_company_name_national,
                "sender_company_legal_form": order_data.sender_company_legal_form,
                "sender_country": {v:k for k, v in COUNTRY_MAPPING.items()}[order_data.sender_country] if order_data.sender_country else None,
                
                "comment": order_data.comment,
                "updated_at": convert_tz(datetime.datetime.strftime(order_data.updated_at, "%d.%m.%Y %H:%M:%S UTC"), tz_city=client_state_data.get("tz")) if order_data.updated_at else None,
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
                endpoint="get_orders_data",
                params={
                    "order_uuid_list": order_uuid_list,
                    "legal_entity_uuid": legal_entity_uuid,
                },
                msg=f"{error_message}\n{formatted_traceback}",
                user_uuid=user_data["user_uuid"],
            )
            
            response_content = {"msg": f"ОШИБКА! #{log_id}"}
            return JSONResponse(content=response_content)

@router.put(
    "/update_order_data",
    description="""
    Обновление подробной информации о Поручении.
    
    input: UpdateOrderDataSchema
    """,
    dependencies=[Depends(check_app_auth)],
)
@limiter.limit("3/second")
async def update_order_data(
    request: Request,
    data_for_update: UpdateMTOrderDataSchema,
    
    order_uuid: str = Query(
        ...,
        description="UUID Поручения, в котором будут обновления подробной информации.",
        min_length=36,
        max_length=36
    ),
    
    token: str = Depends(UserQaSM.get_current_user_data),
    
    session: AsyncSession = Depends(get_async_session),
) -> JSONResponse:
    try:
        user_data: Dict[str, str|int] = token.model_dump()   # Парсинг данных пользователя
        
        await MTOrderService.update_order_data(
            session=session,
            
            requester_user_uuid=user_data["user_uuid"],
            requester_user_privilege=user_data["privilege_id"],
            
            order_uuid=order_uuid,
            
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
            recipient_user_uuid = await MTOrderQueryAndStatementManager.get_user_uuid_by_order_uuid(
                session=session,
                
                order_uuid=order_uuid,
            )
        await NotificationService.notify(
            session=session,
            
            requester_user_id=user_data["user_id"],
            requester_user_uuid=user_data["user_uuid"],
            requester_user_privilege=user_data["privilege_id"],
            
            subject="Поручение",
            subject_uuid=order_uuid,
            for_admin=True if user_data["privilege_id"] != PRIVILEGE_MAPPING["Admin"] else False,
            data=(f'Пользователь "{user_data["user_uuid"]}"' if user_data["privilege_id"] != PRIVILEGE_MAPPING["Admin"] else "Администратор") + f' внес изменения в данные о Поручении "{order_uuid}".',
            recipient_user_uuid=None if user_data["privilege_id"] != PRIVILEGE_MAPPING["Admin"] else recipient_user_uuid,
        )
        
        return JSONResponse(content={"msg": "Данные Поручения успешно обновлены."})
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
                endpoint="update_order_data",
                params={
                    "data_for_update": data_for_update.model_dump() if data_for_update else data_for_update,
                    "order_uuid": order_uuid,
                },
                msg=f"{error_message}\n{formatted_traceback}",
                user_uuid=user_data["user_uuid"],
            )
            
            response_content = {"msg": f"ОШИБКА! #{log_id}"}
            return JSONResponse(content=response_content)
