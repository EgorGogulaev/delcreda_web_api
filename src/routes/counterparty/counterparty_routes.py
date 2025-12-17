import traceback
from typing import Any, Dict, List, Literal, Optional, Tuple

from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import JSONResponse

from connection_module import get_async_session
from lifespan import limiter
from security import check_app_auth
from src.query_and_statement.counterparty.counterparty_qas_manager import CounterpartyQueryAndStatementManager
from src.schemas.user_schema import ClientState
from src.service.user_service import UserService
from src.service.reference_service import ReferenceService
from src.schemas.counterparty.counterparty_schema import (
    BaseLegalEntity, CreateIndividualDataSchema, ExtendedLegalEntity, FiltersCounterparties, OrdersCounterparties, FiltersPersons, OrdersPersons, PersonData, RegistrationIdentifierType,
    CreateLegalEntityDataSchema, UpdateCounterpartySchema, CreatePersonsSchema, ResponseGetLegalEntities, ResponseGetPersons, UpdateIndividualDataSchema, UpdateLegalEntityDataSchema, UpdateApplicationAccessList, UpdatePerson,
)
from src.schemas.reference_schema import CountryKey
from src.service.notification_service import NotificationService
from src.models.counterparty.counterparty_models import Counterparty, IndividualData, LegalEntityData, Person
from src.service.counterparty.counterparty_service import CounterpartyService
from src.query_and_statement.user_qas_manager import UserQueryAndStatementManager as UserQaSM
from src.utils.reference_mapping_data.app.app_mapping_data import COUNTRY_MAPPING
from src.utils.reference_mapping_data.user.mapping import PRIVILEGE_MAPPING
from src.utils.tz_converter import convert_tz


router = APIRouter(
    tags=["Counterparty"],
)


@router.post(
    "/create_counterparty",
    description="""
    Создание карточки Контрагента.
    
    input: CreateLegalEntityDataSchema | CreateIndividualDataSchema
    """,
    dependencies=[Depends(check_app_auth)],
)
@limiter.limit("30/second")
async def create_counterparty(
    request: Request,
    
    counterparty_type: Literal["ЮЛ", "ФЛ"],
    # LegalEntityData|IndividualData
    counterparty_data: CreateLegalEntityDataSchema|CreateIndividualDataSchema,
    
    country: CountryKey = Query( # type: ignore
        "Russia",
        description="Страна Контрагента.",
        example="Russia"
    ),
    identifier_type: RegistrationIdentifierType = Query( # type: ignore
        "OGRN",  # Пока учтен только OGRN
        description="Тип регистрационного идентификатора Контрагента.",
        example="OGRN"
    ),
    identifier_value: str = Query(
        ...,
        description="Значение регистрационного идентификатора Контрагента.",
        example="1027700070518"
    ),
    tax_identifier: str = Query(
        ...,
        description="Значение налогового идентификатора Контрагента.",
        example="7736050003"
    ),
    
    owner_user_uuid: str = Query(
        ...,
        description="UUID Пользователя Контрагента(владельца).",
        min_length=36,
        max_length=36
    ),
    new_directory_uuid: Optional[str] = Query(
        None,
        description="(Опиционально) Ручное выставление нового UUID для Директории Контрагента. (нужно для интеграции в другие системы)",
        min_length=36,
        max_length=36
    ),
    
    token: str = Depends(UserQaSM.get_current_user_data),
    
    session: AsyncSession = Depends(get_async_session),
) -> JSONResponse:
    try:
        user_data: Dict[str, str|int] = token.model_dump()   # Парсинг данных пользователя
        
        new_counterparty_with_data: Tuple[Tuple[Counterparty, LegalEntityData|IndividualData], Dict[str, int|str]] = await CounterpartyService.create_counterparty(
            session=session,
            
            counterparty_type=counterparty_type,
            
            requester_user_uuid=user_data["user_uuid"],
            requester_user_privilege=user_data["privilege_id"],
            
            owner_user_uuid=owner_user_uuid,
            new_directory_uuid=new_directory_uuid,
            
            country=COUNTRY_MAPPING[country],
            identifier_type=identifier_type,
            identifier_value=identifier_value,
            tax_identifier=tax_identifier,
            
            # CounterpartyData
            counterparty_data=counterparty_data,
        )
        new_counterparty_uuid = new_counterparty_with_data[0][0].uuid
        await NotificationService.notify(
            session=session,
            
            requester_user_id=user_data["user_id"],
            requester_user_uuid=user_data["user_uuid"],
            requester_user_privilege=user_data["privilege_id"],
            
            subject="Контрагент",
            subject_uuid=new_counterparty_uuid,
            for_admin=True if user_data["privilege_id"] != PRIVILEGE_MAPPING["Admin"] else False,
            data=f'Пользователь "<user>" ({user_data["user_uuid"]}) создал новую карточку Контрагента "<counterparty>" ({new_counterparty_with_data[0][0].identifier_value}).' if user_data["privilege_id"] != PRIVILEGE_MAPPING["Admin"] else f'Администратор создал новую карточку Контрагента "<counterparty>" ({new_counterparty_with_data[0][0].identifier_value}).',
            recipient_user_uuid=None if user_data["privilege_id"] != PRIVILEGE_MAPPING["Admin"] else owner_user_uuid,
            request_options={
                "<user>": {
                    "uuid": user_data["user_uuid"],
                },
                "<counterparty>": {
                    "uuid": new_counterparty_uuid,
                },
            } if user_data["privilege_id"] != PRIVILEGE_MAPPING["Admin"] else {
                "<counterparty>": {
                    "uuid": new_counterparty_uuid,
                },
            },
        )
        
        return JSONResponse(
            content={
                "msg": "Карточка Контрагента успешно создана.",
                "data": {
                    "uuid": new_counterparty_uuid,
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
                endpoint="create_counterparty",
                params={
                    "counterparty_type": counterparty_type,
                    "counterparty_data": counterparty_data.model_dump() if counterparty_data else counterparty_data,
                    "country": country,
                    "identifier_type": identifier_type,
                    "identifier_value": identifier_value,
                    "tax_identifier": tax_identifier,
                    "owner_user_uuid": owner_user_uuid,
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
    "/get_counterparties",
    description="""
    Получение основной информации о Контрагенте.
    Пользователь может получить только информацию о своих карточках Контрагента.
    Админ может получить информацию о всех карточках Контрагента.
    
    filter: FiltersCounterparties
    order: OrdersCounterparties
    state: ClientState
    output: ResponseGetLegalEntities
    """,
    dependencies=[Depends(check_app_auth)],
)
@limiter.limit("30/second")
async def get_counterparties(
    request: Request,
    
    counterparty_type: Optional[Literal["ЮЛ", "ФЛ"]] = Query(  # TODO при добавлении нового типа Контрагента - ЮЛ -> унифицировать выдачу
        "ЮЛ",
        description="(Опционально) Фильтр по типу Контрагента (ЮЛ/ФЛ) (точное совпадение)."
    ),
    user_uuid: Optional[str] = Query(
        None,
        description="(Опционально) Фильтр по UUID Пользователя (точное совпадение).",
        min_length=36,
        max_length=36
    ),
    
    legal_entity_name_ilike: Optional[str] = Query(
        None,
        description='(Опционально) Фильтр по названию компании (латиница/национальное написание) (частичное совпадение) (если counterparty_type === "ЮЛ").',
    ),
    
    extended_output: bool = Query(
        False,
        description="Выдача ответа с дополнительной информацией."
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
    
    filter: Optional[FiltersCounterparties] = None,
    order: Optional[OrdersCounterparties] = None,
    
    token: str = Depends(UserQaSM.get_current_user_data),
    
    session: AsyncSession = Depends(get_async_session),
    
    client_state: Optional[ClientState] = None,
) -> ResponseGetLegalEntities:
    try:
        user_data: Dict[str, str|int] = token.model_dump()   # Парсинг данных пользователя
        
        if client_state is None:
            client_state: ClientState = await UserService.get_client_state(
                requester_user_uuid=user_data["user_uuid"],
                requester_user_privilege=user_data["privilege_id"],
                user_uuid=user_data["user_uuid"],
            )
        client_state_data: Dict[str, Any] = client_state.model_dump()["data"]
        
        counterparties: Dict[str, List[Optional[Counterparty|int|bool]] | List[Optional[Tuple[Counterparty, bool]]]] = await CounterpartyService.get_counterparties(
            session=session,
            
            requester_user_uuid=user_data["user_uuid"],
            requester_user_privilege=user_data["privilege_id"],
            
            counterparty_type=counterparty_type,
            user_uuid=user_uuid,
            legal_entity_name_ilike=legal_entity_name_ilike,
            
            extended_output=extended_output,
            
            page=page,
            page_size=page_size,
            
            filter=filter,
            order=order,
        )
        
        response_content = ResponseGetLegalEntities(
            data=[],
            count=0,
            total_records=None,
            total_pages=None,
        )
        
        for counterparty in counterparties["data"]:
            if extended_output:
                if counterparty_type == "ЮЛ":
                    response_content.data.append(
                        ExtendedLegalEntity(
                            uuid=counterparty["legal_entity"].uuid,
                            country={v: k for k, v in COUNTRY_MAPPING.items()}[counterparty["legal_entity"].country],
                            identifier_type=counterparty["legal_entity"].identifier_type,
                            identifier_value=counterparty["legal_entity"].identifier_value,
                            tax_identifier=counterparty["legal_entity"].tax_identifier,
                            
                            name_latin=counterparty["name_latin"],
                            name_national=counterparty["name_national"],
                            organizational_and_legal_form_latin=counterparty["organizational_and_legal_form_latin"],
                            organizational_and_legal_form_national=counterparty["organizational_and_legal_form_national"],
                            data_updated_at=convert_tz(counterparty["updated_at"].strftime("%d.%m.%Y %H:%M:%S UTC"), tz_city=client_state_data.get("tz")) if counterparty["updated_at"] else None,
                            
                            user_id=counterparty["legal_entity"].user_id,
                            user_uuid=counterparty["legal_entity"].user_uuid,
                            directory_id=counterparty["legal_entity"].directory_id,
                            directory_uuid=counterparty["legal_entity"].directory_uuid,
                            is_active=counterparty["legal_entity"].is_active,
                            data_id=counterparty["legal_entity"].data_id,  # FIXME это возможно не стоит возвращать
                            can_be_updated_by_user=counterparty["legal_entity"].can_be_updated_by_user,
                            mt=counterparty["mt"],
                            application_access_list=counterparty["legal_entity"].application_access_list,
                            updated_at=convert_tz(counterparty["legal_entity"].updated_at.strftime("%d.%m.%Y %H:%M:%S UTC"), tz_city=client_state_data.get("tz")) if counterparty["legal_entity"].updated_at else None,
                            created_at=convert_tz(counterparty["legal_entity"].created_at.strftime("%d.%m.%Y %H:%M:%S UTC"), tz_city=client_state_data.get("tz")) if counterparty["legal_entity"].created_at else None,
                        )
                    )
                elif counterparty_type == "ФЛ":
                    ...  # TODO тут логика работы с ФЛ
                else:
                    ...  # TODO тут логика работы с комбинированным набором данных
            else:
                if counterparty_type == "ЮЛ":
                    response_content.data.append(
                        BaseLegalEntity(
                            uuid=counterparty[0].uuid,
                            country={v: k for k, v in COUNTRY_MAPPING.items()}[counterparty[0].country],
                            identifier_type=counterparty[0].identifier_type,
                            identifier_value=counterparty[0].identifier_value,
                            tax_identifier=counterparty[0].tax_identifier,
                            
                            user_id=counterparty[0].user_id,
                            user_uuid=counterparty[0].user_uuid,
                            directory_id=counterparty[0].directory_id,
                            directory_uuid=counterparty[0].directory_uuid,
                            is_active=counterparty[0].is_active,
                            data_id=counterparty[0].data_id,  # FIXME это возможно не стоит возвращать
                            can_be_updated_by_user=counterparty[0].can_be_updated_by_user,
                            mt=counterparty[1],
                            application_access_list=counterparty[0].application_access_list,
                            updated_at=convert_tz(counterparty[0].updated_at.strftime("%d.%m.%Y %H:%M:%S UTC"), tz_city=client_state_data.get("tz")) if counterparty[0].updated_at else None,
                            created_at=convert_tz(counterparty[0].created_at.strftime("%d.%m.%Y %H:%M:%S UTC"), tz_city=client_state_data.get("tz")) if counterparty[0].created_at else None,
                        )
                    )
                elif counterparty_type == "ФЛ":
                    ...  # TODO тут логика работы с ФЛ
                else:
                    ...  # TODO тут логика работы с комбинированным набором данных
            response_content.count += 1
        
        response_content.total_records = counterparties["total_records"]
        response_content.total_pages = counterparties["total_pages"]
        
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
                endpoint="get_counterparties",
                params={
                    "user_uuid": user_uuid,
                    "legal_entity_name_ilike": legal_entity_name_ilike,
                    "extended_output": extended_output,
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

@router.put(
    "/change_counterparties_edit_status",
    description="""
    Изменение статуса возможности Пользователем редактировать данные карточки Контрагента.
    (Может вызвать только Админ)
    """,
    dependencies=[Depends(check_app_auth)],
)
@limiter.limit("30/second")
async def change_counterparties_edit_status(
    request: Request,
    counterparty_uuids: List[Optional[str]] = Query(
        [],
        description="Массив UUID'ов карточек Контрагента, у которых должен быть изменен статус возможности редактирования Пользователем."
    ),
    
    edit_status: bool = Query(
        ...,
        description="Статус возможности редактирования Контрагента Пользователем (true-можно/false-нельзя).",
        example=False
    ),
    
    token: str = Depends(UserQaSM.get_current_user_data),
    
    session: AsyncSession = Depends(get_async_session),
) -> JSONResponse:
    try:
        user_data: Dict[str, str|int] = token.model_dump()   # Парсинг данных пользователя
        
        await CounterpartyService.change_counterparties_edit_status(
            session=session,
            
            requester_user_uuid=user_data["user_uuid"],
            requester_user_privilege=user_data["privilege_id"],
            
            counterparty_uuids=counterparty_uuids,
            edit_status=edit_status,
        )
        
        # TODO тут нужно уведомление для 1 и множества лиц (нужна фоновая задача)
        
        return JSONResponse(content={"msg": f"Возможность редактирования Контрагента изменена на {edit_status}."})
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
                endpoint="change_counterparties_edit_status",
                params={
                    "counterparty_uuids": counterparty_uuids,
                    "edit_status": edit_status,
                },
                msg=f"{error_message}\n{formatted_traceback}",
                user_uuid=user_data["user_uuid"],
            )
            
            response_content = {"msg": f"ОШИБКА! #{log_id}"}
            return JSONResponse(content=response_content)
    finally:
        await session.rollback()

@router.put(
    "/update_counterparty",
    description="""
    Обновление основной информации в карточке Контрагента.
    
    input: UpdateLegalEntitySchema
    """,
    dependencies=[Depends(check_app_auth)],
)
@limiter.limit("30/second")
async def update_counterparty(
    request: Request,
    
    data_for_update: UpdateCounterpartySchema,
    
    counterparty_uuid: str = Query(
        ...,
        description="UUID Контрагента, в основной информации которого, планируются изменения.",
        min_length=36,
        max_length=36
    ),
    
    token: str = Depends(UserQaSM.get_current_user_data),
    
    session: AsyncSession = Depends(get_async_session),
) -> JSONResponse:
    try:
        user_data: Dict[str, str|int] = token.model_dump()   # Парсинг данных пользователя
        
        await CounterpartyService.update_counterparty(
            session=session,
            
            requester_user_uuid=user_data["user_uuid"],
            requester_user_privilege=user_data["privilege_id"],
            
            counterparty_uuid=counterparty_uuid,
            
            data_for_update=data_for_update,
        )
        
        if user_data["privilege_id"] == PRIVILEGE_MAPPING["Admin"]:
            recipient_user_uuid = await CounterpartyQueryAndStatementManager.get_user_uuid_by_counterparty_uuid(
                session=session,
                
                counterparty_uuid=counterparty_uuid,
            )
        await NotificationService.notify(
            session=session,
            
            requester_user_id=user_data["user_id"],
            requester_user_uuid=user_data["user_uuid"],
            requester_user_privilege=user_data["privilege_id"],
            
            subject="Контрагент",
            subject_uuid=counterparty_uuid,
            for_admin=True if user_data["privilege_id"] != PRIVILEGE_MAPPING["Admin"] else False,
            data=f'Пользователь "<user>" ({user_data["user_uuid"]})' if user_data["privilege_id"] != PRIVILEGE_MAPPING["Admin"] else "Администратор" + f' внес изменения в основную информацию о Контрагенте "<counterparty>" ({counterparty_uuid}).',
            recipient_user_uuid=None if user_data["privilege_id"] != PRIVILEGE_MAPPING["Admin"] else recipient_user_uuid,
            request_options={
                "<user>": {
                    "uuid": user_data["user_uuid"],
                },
                "<counterparty>": {
                    "uuid": counterparty_uuid,
                },
            } if user_data["privilege_id"] != PRIVILEGE_MAPPING["Admin"] else {
                "<counterparty>": {
                    "uuid": counterparty_uuid,
                },
            },
        )
        
        return JSONResponse(content={"msg": "Основная информация о Контрагенте успешно обновлена."})
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
                endpoint="update_counterparty",
                params={
                    "data_for_update": data_for_update.model_dump() if data_for_update else data_for_update,
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
    "/update_application_access_list",
    description="""
    Изменение списка доступных к созданию типов Заявок.
    """,
    dependencies=[Depends(check_app_auth)],
)
async def update_application_access_list(
    request: Request,
    
    data_for_update: UpdateApplicationAccessList,
    counterparty_uuid: str = Query(
        ...,
        description="UUID Контрагента, в котором планируется изменение списка доступных к созданию типов Заявок.",
        min_length=36,
        max_length=36
    ),
    
    token: str = Depends(UserQaSM.get_current_user_data),
    
    session: AsyncSession = Depends(get_async_session),
) -> JSONResponse:
    try:
        user_data: Dict[str, str|int] = token.model_dump()   # Парсинг данных пользователя
        
        
        await CounterpartyService.update_application_access_list(
            session=session,
            
            requester_user_privilege=user_data["privilege_id"],
            counterparty_uuid=counterparty_uuid,
            
            mt=data_for_update.mt,
            # TODO тут будут другие бизнес процессы
        )
        response_content = {"msg": f'Список доступов к типам Заявок для Контрагента с UUID - "{counterparty_uuid}" успешно изменен.'}
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
                endpoint="update_application_access_list",
                params={
                    "data_for_update": data_for_update.model_dump() if data_for_update else data_for_update,
                    "counterparty_uuid": counterparty_uuid,
                },
                msg=f"{error_message}\n{formatted_traceback}",
                user_uuid=user_data["user_uuid"],
            )
            
            response_content = {"msg": f"ОШИБКА! #{log_id}"}
            return JSONResponse(content=response_content)
    finally:
        await session.rollback()

@router.post(  # FIXME
    "/get_counterparties_data",
    description="""
    Получении подробных данных о Контрагенте.
    
    state: ClientState
    """,
    dependencies=[Depends(check_app_auth)],
)
@limiter.limit("30/second")
async def get_counterparties_data(
    request: Request,
    
    counterparty_type: Literal["ЮЛ", "ФЛ"] = Query(
        "ЮЛ",
        description="Тип карточки Контрагента(ЮЛ/ФЛ) по которому будут запрошены подробные данные."
    ),
    counterparty_uuid_list: List[Optional[str]] = Query(
        [],
        description="(Опционально) Массив UUID'ов Контрагентов, подробные данные которых нужно получить."
    ),
    user_uuid: Optional[str] = Query(
        None,
        description="(Опционально) UUID Пользователя владельца карточки Контрагента."
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
        
        counterparties_data: List[Optional[LegalEntityData|IndividualData]] = await CounterpartyService.get_counterparties_data(
            session=session,
            
            counterparty_type=counterparty_type,
            
            requester_user_uuid=user_data["user_uuid"],
            requester_user_privilege=user_data["privilege_id"],
            
            counterparty_uuid_list=counterparty_uuid_list,
            user_uuid=user_uuid,
        )
        
        response_content = {"data": {}, "count": 0}
        
        for counterparty_data in counterparties_data:  # FIXME
            response_content["count"] += 1
            if counterparty_type == "ЮЛ":
                response_content["data"][counterparty_data.id] = {
                    "name_latin": counterparty_data.name_latin,
                    "name_national": counterparty_data.name_national,
                    "organizational_and_legal_form_latin": counterparty_data.organizational_and_legal_form_latin,
                    "organizational_and_legal_form_national": counterparty_data.organizational_and_legal_form_national,
                    "site": counterparty_data.site,
                    "registration_date": counterparty_data.registration_date.strftime("%d.%m.%Y") if counterparty_data.registration_date else None,
                    "legal_address": counterparty_data.legal_address,
                    "postal_address": counterparty_data.postal_address,
                    "additional_address": counterparty_data.additional_address,
                    "updated_at": convert_tz(counterparty_data.updated_at.strftime("%d.%m.%Y %H:%M:%S UTC"), tz_city=client_state_data.get("tz")) if counterparty_data.updated_at else None,
                }
            else:
                ...  # TODO тут логика работы с ФЛ
        
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
                endpoint="get_counterparties_data",
                params={
                    "counterparty_uuid_list": counterparty_uuid_list,
                    "user_uuid": user_uuid,
                },
                msg=f"{error_message}\n{formatted_traceback}",
                user_uuid=user_data["user_uuid"],
            )
            
            response_content = {"msg": f"ОШИБКА! #{log_id}"}
            return JSONResponse(content=response_content)
    finally:
        await session.rollback()

@router.put(
    "/update_counterparty_data",
    description="""
    Обновление подробных данных о Контрагенте.
    
    input: UpdateLegalEntityDataSchema | UpdateIndividualDataSchema
    """,
    dependencies=[Depends(check_app_auth)],
)
@limiter.limit("30/second")
async def update_counterparty_data(
    request: Request,
    data_for_update: UpdateLegalEntityDataSchema | UpdateIndividualDataSchema,
    
    counterparty_uuid: str = Query(
        ...,
        description="UUID Контрагента, в подробных данных которого предполагаются изменения.",
        min_length=36,
        max_length=36
    ),
    
    token: str = Depends(UserQaSM.get_current_user_data),
    
    session: AsyncSession = Depends(get_async_session),
) -> JSONResponse:
    try:
        user_data: Dict[str, str|int] = token.model_dump()   # Парсинг данных пользователя
        
        await CounterpartyService.update_counterparty_data(
            session=session,
            
            requester_user_uuid=user_data["user_uuid"],
            requester_user_privilege=user_data["privilege_id"],
            
            counterparty_uuid=counterparty_uuid,
            
            data_for_update=data_for_update,
        )
        
        if user_data["privilege_id"] == PRIVILEGE_MAPPING["Admin"]:
            recipient_user_uuid = await CounterpartyQueryAndStatementManager.get_user_uuid_by_counterparty_uuid(
                session=session,
                
                counterparty_uuid=counterparty_uuid,
            )
        await NotificationService.notify(
            session=session,
            
            requester_user_id=user_data["user_id"],
            requester_user_uuid=user_data["user_uuid"],
            requester_user_privilege=user_data["privilege_id"],
            
            subject="Контрагент",
            subject_uuid=counterparty_uuid,
            for_admin=True if user_data["privilege_id"] != PRIVILEGE_MAPPING["Admin"] else False,
            data=f'Пользователь "<user>" ({user_data["user_uuid"]})' if user_data["privilege_id"] != PRIVILEGE_MAPPING["Admin"] else "Администратор" + f' внес изменения в данные о Контрагенте "<counterparty>" ({counterparty_uuid}).',
            recipient_user_uuid=None if user_data["privilege_id"] != PRIVILEGE_MAPPING["Admin"] else recipient_user_uuid,
            request_options={
                "<user>": {
                    "uuid": user_data["user_uuid"],
                },
                "<counterparty>": {
                    "uuid": counterparty_uuid,
                },
            } if user_data["privilege_id"] != PRIVILEGE_MAPPING["Admin"] else {
                "<counterparty>": {
                    "uuid": counterparty_uuid,
                },
            },
        )
        
        return JSONResponse(content={"msg": "Данные Контрагента успешно обновлены."})
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
                endpoint="update_counterparty_data",
                params={
                    "data_for_update": data_for_update.model_dump() if data_for_update else data_for_update,
                    "counterparty_uuid": counterparty_uuid,
                },
                msg=f"{error_message}\n{formatted_traceback}",
                user_uuid=user_data["user_uuid"],
            )
            
            response_content = {"msg": f"ОШИБКА! #{log_id}"}
            return JSONResponse(content=response_content)
    finally:
        await session.rollback()

@router.delete(
    "/delete_counterparties",
    description="""
    Удаление карточек Контрагентов.
    """,
    dependencies=[Depends(check_app_auth)],
)
@limiter.limit("30/second")
async def delete_counterparties(  # TODO Нужно предусмотреть параметр для удаления из хранилища Директорий и Документов (ЮЛ и ПР)
    request: Request,
    counterparty_uuids: List[str] = Query(
        [],
        description="Массив UUID карточек Контрагента к удалению."
    ),
    
    token: str = Depends(UserQaSM.get_current_user_data),
    
    session: AsyncSession = Depends(get_async_session),
) -> JSONResponse:
    try:
        user_data: Dict[str, str|int] = token.model_dump()   # Парсинг данных пользователя
        
        await CounterpartyService.delete_counterparties(
            session=session,
            
            requester_user_id=user_data["user_id"],
            requester_user_uuid=user_data["user_uuid"],
            requester_user_privilege=user_data["privilege_id"],
            
            counterparty_uuids=counterparty_uuids,
        )
        
        # TODO тут нужно уведомление для 1 и множества лиц (нужна фоновая задача)
        
        return JSONResponse({"msg": "Контрагент/ы успешно удалено/ы."})
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
                endpoint="delete_counterparties",
                params={
                    "counterparty_uuids": counterparty_uuids,
                },
                msg=f"{error_message}\n{formatted_traceback}",
                user_uuid=user_data["user_uuid"],
            )
            
            response_content = {"msg": f"ОШИБКА! #{log_id}"}
            return JSONResponse(content=response_content)
    finally:
        await session.rollback()

@router.post(
    "/create_persons",
    description="""
    Создание записи о ФЛ(которое относится всегда к Контрагенту типа ЮЛ).
    
    input: CreatePersonsSchema
    """,
    dependencies=[Depends(check_app_auth)],
)
@limiter.limit("30/second")
async def create_persons(
    request: Request,
    new_persons: CreatePersonsSchema,
    
    token: str = Depends(UserQaSM.get_current_user_data),
    
    session: AsyncSession = Depends(get_async_session),
) -> JSONResponse:
    try:
        user_data: Dict[str, str|int] = token.model_dump()   # Парсинг данных пользователя
        
        new_person_ids: List[int] = await CounterpartyService.create_persons(
            session=session,
            
            requester_user_uuid=user_data["user_uuid"],
            requester_user_privilege=user_data["privilege_id"],
            
            new_persons=new_persons,
        )
        
        counterparty_uuid = new_persons.new_persons[0].counterparty_uuid
        
        # TODO тут нужно уведомление для 1 и множества лиц (нужна фоновая задача) заменить блок снизу
        
        if user_data["privilege_id"] != PRIVILEGE_MAPPING["Admin"]:
            await NotificationService.notify(
                session=session,
                
                requester_user_id=user_data["user_id"],
                requester_user_uuid=user_data["user_uuid"],
                requester_user_privilege=user_data["privilege_id"],
                
                subject="Контрагент",
                subject_uuid=counterparty_uuid,
                for_admin=True,
                data=f'Пользователь "<user>" ({user_data["user_uuid"]}) создал новую/ые запись/и о ФЛ с ID: "{", ".join([str(new_person_id) for new_person_id in new_person_ids])}" в карточке Контрагента(ЮЛ) "<counterparty>" ({counterparty_uuid}).',
                recipient_user_uuid=None,
                request_options={
                    "<user>": {
                        "uuid": user_data["user_uuid"],
                    },
                    "<counterparty>": {
                        "uuid": counterparty_uuid,
                    }
                },
            )
        
        return JSONResponse(content={"msg": "ФЛ для Контрагента(ЮЛ) создано/ы."})
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
                endpoint="create_persons",
                params={
                    "new_persons": new_persons.model_dump() if new_persons else new_persons,
                },
                msg=f"{error_message}\n{formatted_traceback}",
                user_uuid=user_data["user_uuid"],
            )
            
            response_content = {"msg": f"ОШИБКА! #{log_id}"}
            return JSONResponse(content=response_content)
    finally:
        await session.rollback()

@router.post(
    "/get_persons",
    description="""
    Получение информации о ФЛ.
    
    filter: FiltersPersons
    order: OrdersPersons
    state: ClientState
    output: ResponseGetPersons
    """,
    dependencies=[Depends(check_app_auth)],
)
@limiter.limit("30/second")
async def get_persons(
    request: Request,
    counterparty_uuid: Optional[str] = Query(
        None,
        description="(Опционально) Фильтр по UUID Контрагента."
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
    
    filter: Optional[FiltersPersons] = None,
    order: Optional[OrdersPersons] = None,
    
    token: str = Depends(UserQaSM.get_current_user_data),
    
    session: AsyncSession = Depends(get_async_session),
    
    client_state: Optional[ClientState] = None,
) -> ResponseGetPersons:
    try:
        user_data: Dict[str, str|int] = token.model_dump()   # Парсинг данных пользователя
        
        if client_state is None:
            client_state: ClientState = await UserService.get_client_state(
                requester_user_uuid=user_data["user_uuid"],
                requester_user_privilege=user_data["privilege_id"],
                user_uuid=user_data["user_uuid"],
            )
        client_state_data: Dict[str, Any] = client_state.model_dump()["data"]
        
        response_content = ResponseGetPersons(
            data=[],
            count=0,
            total_records=None,
            total_pages=None
        )
        
        persons: Dict[str, List[Optional[Person]]|Optional[int]] = await CounterpartyService.get_persons(
            session=session,
            
            requester_user_uuid=user_data["user_uuid"],
            requester_user_privilege=user_data["privilege_id"],
            
            counterparty_uuid=counterparty_uuid,
            
            page=page,
            page_size=page_size,
            
            filter=filter,
            order=order,
        )
        
        for person in persons["data"]:
            response_content.data.append(
                PersonData(
                    id=person.id,
                    surname=person.surname,
                    name=person.name,
                    patronymic=person.patronymic,
                    gender=person.gender,
                    job_title=person.job_title,
                    basic_action_signatory=person.basic_action_signatory,
                    power_of_attorney_number=person.power_of_attorney_number,
                    power_of_attorney_date=person.power_of_attorney_date.strftime("%d.%m.%Y") if person.power_of_attorney_date else None,
                    email=person.email,
                    phone=person.phone,
                    contact=person.contact,
                    counterparty_uuid=person.counterparty_uuid,
                    updated_at=convert_tz(person.updated_at.strftime("%d.%m.%Y %H:%M:%S UTC"), tz_city=client_state_data.get("tz")) if person.updated_at else None,
                    created_at=convert_tz(person.created_at.strftime("%d.%m.%Y %H:%M:%S UTC"), tz_city=client_state_data.get("tz")) if person.created_at else None,
                )
            )
            response_content.count += 1
        
        response_content.total_records = persons["total_records"]
        response_content.total_pages = persons["total_pages"]
        
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
                endpoint="get_persons",
                params={
                    "counterparty_uuid": counterparty_uuid,
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

@router.put(
    "/update_person",
    description="""
    Обновление информации о ФЛ.
    
    input: UpdatePerson
    """,
    dependencies=[Depends(check_app_auth)],
)
@limiter.limit("30/second")
async def update_person(
    request: Request,
    person_id: int,
    data_for_update: UpdatePerson,
    
    token: str = Depends(UserQaSM.get_current_user_data),
    
    session: AsyncSession = Depends(get_async_session),
) -> JSONResponse:
    try:
        user_data: Dict[str, str|int] = token.model_dump()   # Парсинг данных пользователя
        
        counterparty_uuid: str = await CounterpartyService.update_person(
            session=session,
            
            requester_user_uuid=user_data["user_uuid"],
            requester_user_privilege=user_data["privilege_id"],
            
            person_id=person_id,
            surname=data_for_update.surname,
            name=data_for_update.name,
            patronymic=data_for_update.patronymic,
            gender=data_for_update.gender,
            job_title=data_for_update.job_title,
            basic_action_signatory=data_for_update.basic_action_signatory,
            power_of_attorney_number=data_for_update.power_of_attorney_number,
            power_of_attorney_date=data_for_update.power_of_attorney_date,
            email=data_for_update.email,
            phone=data_for_update.phone,
            contact=data_for_update.contact,
            counterparty_uuid=data_for_update.counterparty_uuid,
        )
        
        # TODO тут нужно уведомление для 1 и множества лиц (нужна фоновая задача) заменить блок снизу
        
        if user_data["privilege_id"] != PRIVILEGE_MAPPING["Admin"]:
            await NotificationService.notify(
                session=session,
                
                requester_user_id=user_data["user_id"],
                requester_user_uuid=user_data["user_uuid"],
                requester_user_privilege=user_data["privilege_id"],
                
                subject="Контрагент",
                subject_uuid=counterparty_uuid,
                for_admin=True,
                data=f'Пользователь "<user>" ({user_data["user_uuid"]}) внес изменения в информацию о ФЛ с ID "{person_id}"; Контрагент - "<counterparty>" ({counterparty_uuid}).',
                recipient_user_uuid=None,
                request_options={
                    "<user>": {
                        "uuid": user_data["user_uuid"],
                    },
                    "<counterparty>": {
                        "uuid": counterparty_uuid,
                    }
                },
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
                endpoint="update_person",
                params={
                    "person_id": person_id,
                    "data_for_update": data_for_update.model_dump() if data_for_update else data_for_update,
                },
                msg=f"{error_message}\n{formatted_traceback}",
                user_uuid=user_data["user_uuid"],
            )
            
            response_content = {"msg": f"ОШИБКА! #{log_id}"}
            return JSONResponse(content=response_content)
    finally:
        await session.rollback()

@router.delete(
    "/delete_persons",
    description="""
    Удаление информации о ФЛ.
    """,
    dependencies=[Depends(check_app_auth)],
)
@limiter.limit("30/second")
async def delete_persons(
    request: Request,
    person_ids: List[Optional[int]] = Query(
        [],
        description="Массив ID ФЛ к удалению."
    ),
    
    token: str = Depends(UserQaSM.get_current_user_data),
    
    session: AsyncSession = Depends(get_async_session),
) -> JSONResponse:
    try:
        user_data: Dict[str, str|int] = token.model_dump()   # Парсинг данных пользователя
        
        counterparty_uuid: Optional[str] = await CounterpartyService.delete_persons(
            session=session,
            
            requester_user_uuid=user_data["user_uuid"],
            requester_user_privilege=user_data["privilege_id"],
            
            person_ids=person_ids,
        )
        
        # TODO тут нужно уведомление для 1 и множества лиц (нужна фоновая задача) заменить блок снизу
        
        if user_data["privilege_id"] != PRIVILEGE_MAPPING["Admin"]:
            await NotificationService.notify(
                session=session,
                
                requester_user_id=user_data["user_id"],
                requester_user_uuid=user_data["user_uuid"],
                requester_user_privilege=user_data["privilege_id"],
                
                subject="Контрагент",
                subject_uuid=counterparty_uuid,
                for_admin=True,
                data=f'Пользователь "<user>" ({user_data["user_uuid"]}) удалил информацию о ФЛ с ID "{", ".join([str(person_id) for person_id in person_ids])}"; Контрагент - "<counterparty>" ({counterparty_uuid}).',
                recipient_user_uuid=None,
                request_options={
                    "<user>": {
                        "uuid": user_data["user_uuid"],
                    },
                    "<counterparty>": {
                        "uuid": counterparty_uuid,
                    }
                },
            )
        
        return JSONResponse(content={"msg": "Информация о ФЛ успешно удалена."})
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
                endpoint="delete_persons",
                params={
                    "person_ids": person_ids,
                },
                msg=f"{error_message}\n{formatted_traceback}",
                user_uuid=user_data["user_uuid"],
            )
            
            response_content = {"msg": f"ОШИБКА! #{log_id}"}
            return JSONResponse(content=response_content)
    finally:
        await session.rollback()
