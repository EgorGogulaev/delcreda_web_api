import datetime
import traceback
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import JSONResponse

from connection_module import get_async_session
from lifespan import limiter
from security import check_app_auth
from src.query_and_statement.legal_entity.legal_entity_qas_manager import LegalEntityQueryAndStatementManager
from src.schemas.user_schema import ClientState
from src.service.user_service import UserService
from src.service.reference_service import ReferenceService
from src.schemas.legal_entity.legal_entity_schema import (
    BaseLegalEntity, ExtendedLegalEntity, FiltersLegalEntities, OrdersLegalEntities, FiltersPersons, OrdersPersons, PersonData, RegistrationIdentifierType,
    CreateLegalEntityDataSchema, UpdateLegalEntitySchema, CreatePersonsSchema, ResponseGetLegalEntities, ResponseGetPersons, UpdateLegalEntityDataSchema, UpdateOrderAccessList, UpdatePerson,
)
from src.schemas.reference_schema import CountryKey
from src.service.notification_service import NotificationService
from src.models.legal_entity.legal_entity_models import LegalEntity, LegalEntityData, Person
from src.service.legal_entity.legal_entity_service import LegalEntityService
from src.query_and_statement.user_qas_manager import UserQueryAndStatementManager as UserQaSM
from src.utils.reference_mapping_data.app.app_mapping_data import COUNTRY_MAPPING
from src.utils.reference_mapping_data.user.mapping import PRIVILEGE_MAPPING
from src.utils.tz_converter import convert_tz


router = APIRouter(
    tags=["Legal entity"],
)


@router.post(
    "/create_legal_entity",
    description="""
    Создание ЮЛ.
    
    input: CreateLegalEntityDataSchema
    """,
    dependencies=[Depends(check_app_auth)],
)
@limiter.limit("3/second")
async def create_legal_entity(
    request: Request,
    # LegalEntityData
    legal_entity_data: CreateLegalEntityDataSchema,
    
    country: CountryKey = Query( # type: ignore
        "Russia",
        description="Страна регистрации ЮЛ.",
        example="Russia"
    ),
    registration_identifier_type: RegistrationIdentifierType = Query( # type: ignore
        "OGRN",  # Пока учтен только OGRN
        description="Тип регистрационного идентификатора ЮЛ.",
        example="OGRN"
    ),
    registration_identifier_value: str = Query(
        ...,
        description="Значение регистрационного идентификатора ЮЛ.",
        example="1027700070518"
    ),
    tax_identifier: str = Query(
        ...,
        description="Значение налогового идентификатора ЮЛ.",
        example="7736050003"
    ),
    
    owner_user_uuid: str = Query(
        ...,
        description="UUID Пользователя от ЮЛ(владельца).",
        min_length=36,
        max_length=36
    ),
    new_directory_uuid: Optional[str] = Query(
        None,
        description="(Опиционально) Ручное выставление нового UUID для Директории ЮЛ. (нужно для интеграции в другие системы)",
        min_length=36,
        max_length=36
    ),
    
    token: str = Depends(UserQaSM.get_current_user_data),
    
    session: AsyncSession = Depends(get_async_session),
) -> JSONResponse:
    try:
        user_data: Dict[str, str|int] = token.model_dump()   # Парсинг данных пользователя
        
        new_le_with_data: Tuple[Tuple[LegalEntity, LegalEntityData], Dict[str, int|str]] = await LegalEntityService.create_legal_entity(
            session=session,
            
            requester_user_uuid=user_data["user_uuid"],
            requester_user_privilege=user_data["privilege_id"],
            
            owner_user_uuid=owner_user_uuid,
            new_directory_uuid=new_directory_uuid,
            
            country=COUNTRY_MAPPING[country],
            registration_identifier_type=registration_identifier_type,
            registration_identifier_value=registration_identifier_value,
            tax_identifier=tax_identifier,
            
            # LegalEntityData
            name_latin=legal_entity_data.name_latin,
            name_national=legal_entity_data.name_national,
            organizational_and_legal_form_latin=legal_entity_data.organizational_and_legal_form_latin,
            organizational_and_legal_form_national=legal_entity_data.organizational_and_legal_form_national,
            site=legal_entity_data.site,
            registration_date=datetime.datetime.strptime(legal_entity_data.registration_date, "%d.%m.%Y").date(),
            legal_address=legal_entity_data.legal_address,
            postal_address=legal_entity_data.postal_address,
            additional_address=legal_entity_data.additional_address,
        )
        
        await NotificationService.notify(
            session=session,
            
            requester_user_id=user_data["user_id"],
            requester_user_uuid=user_data["user_uuid"],
            requester_user_privilege=user_data["privilege_id"],
            
            subject="ЮЛ",
            subject_uuid=new_le_with_data[0][0].uuid,
            for_admin=True if user_data["privilege_id"] != PRIVILEGE_MAPPING["Admin"] else False,
            data=f'Пользователь "{user_data["user_uuid"]}" создал новое ЮЛ "{new_le_with_data[0][0].registration_identifier_value}".' if user_data["privilege_id"] != PRIVILEGE_MAPPING["Admin"] else f'Администратор создал новое ЮЛ "{new_le_with_data[0][0].registration_identifier_value}".',
            recipient_user_uuid=None if user_data["privilege_id"] != PRIVILEGE_MAPPING["Admin"] else owner_user_uuid,
        )
        
        return JSONResponse(
            content={
                "msg": "ЮЛ успешно создано.",
                "data": {
                    "uuid": new_le_with_data[0][0].uuid,
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
                endpoint="create_legal_entity",
                params={
                    "legal_entity_data": legal_entity_data.model_dump() if legal_entity_data else legal_entity_data,
                    "country": country,
                    "registration_identifier_type": registration_identifier_type,
                    "registration_identifier_value": registration_identifier_value,
                    "tax_identifier": tax_identifier,
                    "owner_user_uuid": owner_user_uuid,
                    "new_directory_uuid": new_directory_uuid,
                },
                msg=f"{error_message}\n{formatted_traceback}",
                user_uuid=user_data["user_uuid"],
            )
            
            response_content = {"msg": f"ОШИБКА! #{log_id}"}
            return JSONResponse(content=response_content)

@router.post(
    "/get_legal_entities",
    description="""
    Получение основной информации о ЮЛ.
    Пользователь может получить только информацию о своих ЮЛ.
    Админ может получить информацию о всех ЮЛ.
    
    filter: FiltersLegalEntities
    order: OrdersLegalEntities
    state: ClientState
    output: ResponseGetLegalEntities
    """,
    dependencies=[Depends(check_app_auth)],
)
@limiter.limit("3/second")
async def get_legal_entities(
    request: Request,
    user_uuid: Optional[str] = Query(
        None,
        description="(Опционально) Фильтр по UUID Пользователя (точное совпадение).",
        min_length=36,
        max_length=36
    ),
    
    legal_entity_name_ilike: Optional[str] = Query(
        None,
        description="(Опционально) Фильтр по названию компании (латиница/национальное написание) (частичное совпадение).",
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
    
    filter: Optional[FiltersLegalEntities] = None,
    order: Optional[OrdersLegalEntities] = None,
    
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
        
        legal_entities: Dict[str, List[Optional[LegalEntity|int|bool]] | List[Optional[Tuple[LegalEntity, bool]]]] = await LegalEntityService.get_legal_entities(
            session=session,
            
            requester_user_uuid=user_data["user_uuid"],
            requester_user_privilege=user_data["privilege_id"],
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
        
        for le in legal_entities["data"]:
            if extended_output:
                response_content.data.append(
                    ExtendedLegalEntity(
                        uuid=le["legal_entity"].uuid,
                        country={v: k for k, v in COUNTRY_MAPPING.items()}[le["legal_entity"].country],
                        registration_identifier_type=le["legal_entity"].registration_identifier_type,
                        registration_identifier_value=le["legal_entity"].registration_identifier_value,
                        tax_identifier=le["legal_entity"].tax_identifier,
                        
                        name_latin=le["name_latin"],
                        name_national=le["name_national"],
                        organizational_and_legal_form_latin=le["organizational_and_legal_form_latin"],
                        organizational_and_legal_form_national=le["organizational_and_legal_form_national"],
                        data_updated_at=convert_tz(le["updated_at"].strftime("%d.%m.%Y %H:%M:%S UTC"), tz_city=client_state_data.get("tz")) if le["updated_at"] else None,
                        
                        user_id=le["legal_entity"].user_id,
                        user_uuid=le["legal_entity"].user_uuid,
                        directory_id=le["legal_entity"].directory_id,
                        directory_uuid=le["legal_entity"].directory_uuid,
                        is_active=le["legal_entity"].is_active,
                        data_id=le["legal_entity"].data_id,  # FIXME это возможно не стоит возвращать
                        can_be_updated_by_user=le["legal_entity"].can_be_updated_by_user,
                        mt=le["mt"],
                        order_access_list=le["legal_entity"].order_access_list,
                        updated_at=convert_tz(le["legal_entity"].updated_at.strftime("%d.%m.%Y %H:%M:%S UTC"), tz_city=client_state_data.get("tz")) if le["legal_entity"].updated_at else None,
                        created_at=convert_tz(le["legal_entity"].created_at.strftime("%d.%m.%Y %H:%M:%S UTC"), tz_city=client_state_data.get("tz")) if le["legal_entity"].created_at else None,
                    )
                )
            else:
                response_content.data.append(
                    BaseLegalEntity(
                        uuid=le[0].uuid,
                        country={v: k for k, v in COUNTRY_MAPPING.items()}[le[0].country],
                        registration_identifier_type=le[0].registration_identifier_type,
                        registration_identifier_value=le[0].registration_identifier_value,
                        tax_identifier=le[0].tax_identifier,
                        
                        user_id=le[0].user_id,
                        user_uuid=le[0].user_uuid,
                        directory_id=le[0].directory_id,
                        directory_uuid=le[0].directory_uuid,
                        is_active=le[0].is_active,
                        data_id=le[0].data_id,  # FIXME это возможно не стоит возвращать
                        can_be_updated_by_user=le[0].can_be_updated_by_user,
                        mt=le[1],
                        order_access_list=le[0].order_access_list,
                        updated_at=convert_tz(le[0].updated_at.strftime("%d.%m.%Y %H:%M:%S UTC"), tz_city=client_state_data.get("tz")) if le[0].updated_at else None,
                        created_at=convert_tz(le[0].created_at.strftime("%d.%m.%Y %H:%M:%S UTC"), tz_city=client_state_data.get("tz")) if le[0].created_at else None,
                    )
                )
            response_content.count += 1
        
        response_content.total_records = legal_entities["total_records"]
        response_content.total_pages = legal_entities["total_pages"]
        
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
                endpoint="get_legal_entities",
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

@router.put(
    "/change_legal_entities_edit_status",
    description="""
    Изменение статуса возможности Пользователем редактировать данные ЮЛ.
    (Может вызвать только Админ)
    """,
    dependencies=[Depends(check_app_auth)],
)
@limiter.limit("3/second")
async def change_legal_entities_edit_status(
    request: Request,
    legal_entity_uuids: List[Optional[str]] = Query(
        [],
        description="Массив UUID'ов ЮЛ, у которых должен быть изменен статус возможности редактирования Пользователем."
    ),
    
    edit_status: bool = Query(
        ...,
        description="Статус возможности редактирования ЮЛ Пользователем (true-можно/false-нельзя).",
        example=False
    ),
    
    token: str = Depends(UserQaSM.get_current_user_data),
    
    session: AsyncSession = Depends(get_async_session),
) -> JSONResponse:
    try:
        user_data: Dict[str, str|int] = token.model_dump()   # Парсинг данных пользователя
        
        await LegalEntityService.change_legal_entities_edit_status(
            session=session,
            
            requester_user_uuid=user_data["user_uuid"],
            requester_user_privilege=user_data["privilege_id"],
            
            legal_entity_uuids=legal_entity_uuids,
            edit_status=edit_status,
        )
        
        # TODO тут нужно уведомление для 1 и множества лиц (нужна фоновая задача)
        
        return JSONResponse(content={"msg": f"Возможность редактирования ЮЛ изменена на {edit_status}."})
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
                endpoint="change_legal_entities_edit_status",
                params={
                    "legal_entity_uuids": legal_entity_uuids,
                    "edit_status": edit_status,
                },
                msg=f"{error_message}\n{formatted_traceback}",
                user_uuid=user_data["user_uuid"],
            )
            
            response_content = {"msg": f"ОШИБКА! #{log_id}"}
            return JSONResponse(content=response_content)

@router.put(
    "/update_legal_entity",
    description="""
    Обновление основной информации о ЮЛ.
    
    input: UpdateLegalEntitySchema
    """,
    dependencies=[Depends(check_app_auth)],
)
@limiter.limit("3/second")
async def update_legal_entity(
    request: Request,
    data_for_update: UpdateLegalEntitySchema,
    
    legal_entity_uuid: str = Query(
        ...,
        description="UUID ЮЛ, в основной информации которого, планируются изменения.",
        min_length=36,
        max_length=36
    ),
    
    token: str = Depends(UserQaSM.get_current_user_data),
    
    session: AsyncSession = Depends(get_async_session),
) -> JSONResponse:
    try:
        user_data: Dict[str, str|int] = token.model_dump()   # Парсинг данных пользователя
        
        await LegalEntityService.update_legal_entity(
            session=session,
            
            requester_user_uuid=user_data["user_uuid"],
            requester_user_privilege=user_data["privilege_id"],
            
            legal_entity_uuid=legal_entity_uuid,
            
            country=data_for_update.country,
            registration_identifier_type=data_for_update.registration_identifier_type,
            registration_identifier_value=data_for_update.registration_identifier_value,
            tax_identifier=data_for_update.tax_identifier,
            is_active=data_for_update.is_active,
        )
        
        if user_data["privilege_id"] == PRIVILEGE_MAPPING["Admin"]:
            recipient_user_uuid = await LegalEntityQueryAndStatementManager.get_user_uuid_by_legal_entity_uuid(
                session=session,
                
                legal_entity_uuid=legal_entity_uuid,
            )
        await NotificationService.notify(
            session=session,
            
            requester_user_id=user_data["user_id"],
            requester_user_uuid=user_data["user_uuid"],
            requester_user_privilege=user_data["privilege_id"],
            
            subject="ЮЛ",
            subject_uuid=legal_entity_uuid,
            for_admin=True if user_data["privilege_id"] != PRIVILEGE_MAPPING["Admin"] else False,
            data=f'Пользователь "{user_data["user_uuid"]}"' if user_data["privilege_id"] != PRIVILEGE_MAPPING["Admin"] else "Администратор" + f' внес изменения в основную информацию о ЮЛ "{legal_entity_uuid}".',
            recipient_user_uuid=None if user_data["privilege_id"] != PRIVILEGE_MAPPING["Admin"] else recipient_user_uuid,
        )
        
        return JSONResponse(content={"msg": "Основная информация о ЮЛ успешно обновлена."})
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
                endpoint="update_legal_entity",
                params={
                    "data_for_update": data_for_update.model_dump() if data_for_update else data_for_update,
                    "legal_entity_uuid": legal_entity_uuid,
                },
                msg=f"{error_message}\n{formatted_traceback}",
                user_uuid=user_data["user_uuid"],
            )
            
            response_content = {"msg": f"ОШИБКА! #{log_id}"}
            return JSONResponse(content=response_content)

@router.put(
    "/update_order_access_list",
    description="""
    Изменение списка доступных к созданию типов ПР.
    """,
    dependencies=[Depends(check_app_auth)],
)
async def update_order_access_list(
    request: Request,
    
    data_for_update: UpdateOrderAccessList,
    legal_entity_uuid: str = Query(
        ...,
        description="UUID ЮЛ, в котором планируется изменение списка доступных к созданию типов ПР.",
        min_length=36,
        max_length=36
    ),
    
    token: str = Depends(UserQaSM.get_current_user_data),
    
    session: AsyncSession = Depends(get_async_session),
) -> JSONResponse:
    try:
        user_data: Dict[str, str|int] = token.model_dump()   # Парсинг данных пользователя
        
        
        await LegalEntityService.update_order_access_list(
            session=session,
            
            requester_user_privilege=user_data["privilege_id"],
            legal_entity_uuid=legal_entity_uuid,
            
            mt=data_for_update.mt,
            # TODO тут будут другие бизнес процессы
        )
        response_content = {"msg": f'Список доступов к ПР для ЮЛ с UUID - "{legal_entity_uuid}" успешно изменен.'}
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
                endpoint="update_order_access_list",
                params={
                    "data_for_update": data_for_update.model_dump() if data_for_update else data_for_update,
                    "legal_entity_uuid": legal_entity_uuid,
                },
                msg=f"{error_message}\n{formatted_traceback}",
                user_uuid=user_data["user_uuid"],
            )
            
            response_content = {"msg": f"ОШИБКА! #{log_id}"}
            return JSONResponse(content=response_content)

@router.post(
    "/get_legal_entities_data",
    description="""
    Получении подробных данных о ЮЛ.
    
    state: ClientState
    """,
    dependencies=[Depends(check_app_auth)],
)
@limiter.limit("3/second")
async def get_legal_entities_data(
    request: Request,
    legal_entities_uuid_list: List[Optional[str]] = Query(
        [],
        description="(Опционально) Массив UUID'ов ЮЛ, подробные данные которых нужно получить."
    ),
    user_uuid: Optional[str] = Query(
        None,
        description="(Опционально) UUID Пользователя владельца ЮЛ."
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
        
        les_data: List[Optional[LegalEntityData]] = await LegalEntityService.get_legal_enities_data(
            session=session,
            
            requester_user_uuid=user_data["user_uuid"],
            requester_user_privilege=user_data["privilege_id"],
            
            les_uuid_list=legal_entities_uuid_list,
            user_uuid=user_uuid,
        )
        
        response_content = {"data": {}, "count": 0}
        
        for le_data in les_data:
            response_content["count"] += 1
            response_content["data"][le_data.id] = {
                "name_latin": le_data.name_latin,
                "name_national": le_data.name_national,
                "organizational_and_legal_form_latin": le_data.organizational_and_legal_form_latin,
                "organizational_and_legal_form_national": le_data.organizational_and_legal_form_national,
                "site": le_data.site,
                "registration_date": le_data.registration_date.strftime("%d.%m.%Y") if le_data.registration_date else None,
                "legal_address": le_data.legal_address,
                "postal_address": le_data.postal_address,
                "additional_address": le_data.additional_address,
                "updated_at": convert_tz(le_data.updated_at.strftime("%d.%m.%Y %H:%M:%S UTC"), tz_city=client_state_data.get("tz")) if le_data.updated_at else None,
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
                endpoint="get_legal_entities_data",
                params={
                    "legal_entities_uuid_list": legal_entities_uuid_list,
                    "user_uuid": user_uuid,
                },
                msg=f"{error_message}\n{formatted_traceback}",
                user_uuid=user_data["user_uuid"],
            )
            
            response_content = {"msg": f"ОШИБКА! #{log_id}"}
            return JSONResponse(content=response_content)

@router.put(
    "/update_legal_entity_data",
    description="""
    Обновление подробных данных о ЮЛ.
    
    input: UpdateLegalEntityDataSchema
    """,
    dependencies=[Depends(check_app_auth)],
)
@limiter.limit("3/second")
async def update_legal_entity_data(
    request: Request,
    data_for_update: UpdateLegalEntityDataSchema,
    
    legal_entity_uuid: str = Query(
        ...,
        description="UUID ЮЛ, в подробных данных которого предполагаются изменения.",
        min_length=36,
        max_length=36
    ),
    
    token: str = Depends(UserQaSM.get_current_user_data),
    
    session: AsyncSession = Depends(get_async_session),
) -> JSONResponse:
    try:
        user_data: Dict[str, str|int] = token.model_dump()   # Парсинг данных пользователя
        
        await LegalEntityService.update_legal_entity_data(
            session=session,
            
            requester_user_uuid=user_data["user_uuid"],
            requester_user_privilege=user_data["privilege_id"],
            
            legal_entity_uuid=legal_entity_uuid,
            
            name_latin=data_for_update.name_latin,
            name_national=data_for_update.name_national,
            organizational_and_legal_form_latin=data_for_update.organizational_and_legal_form_latin,
            organizational_and_legal_form_national=data_for_update.organizational_and_legal_form_national,
            site=data_for_update.site,
            registration_date=data_for_update.registration_date,
            legal_address=data_for_update.legal_address,
            postal_address=data_for_update.postal_address,
            additional_address=data_for_update.additional_address,
        )
        
        if user_data["privilege_id"] == PRIVILEGE_MAPPING["Admin"]:
            recipient_user_uuid = await LegalEntityQueryAndStatementManager.get_user_uuid_by_legal_entity_uuid(
                session=session,
                
                legal_entity_uuid=legal_entity_uuid,
            )
        await NotificationService.notify(
            session=session,
            
            requester_user_id=user_data["user_id"],
            requester_user_uuid=user_data["user_uuid"],
            requester_user_privilege=user_data["privilege_id"],
            
            subject="ЮЛ",
            subject_uuid=legal_entity_uuid,
            for_admin=True if user_data["privilege_id"] != PRIVILEGE_MAPPING["Admin"] else False,
            data=f'Пользователь "{user_data["user_uuid"]}"' if user_data["privilege_id"] != PRIVILEGE_MAPPING["Admin"] else "Администратор" + f' внес изменения в данные о ЮЛ "{legal_entity_uuid}".',
            recipient_user_uuid=None if user_data["privilege_id"] != PRIVILEGE_MAPPING["Admin"] else recipient_user_uuid,
        )
        
        return JSONResponse(content={"msg": "Данные ЮЛ успешно обновлены."})
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
                endpoint="update_legal_entity_data",
                params={
                    "data_for_update": data_for_update.model_dump() if data_for_update else data_for_update,
                    "legal_entity_uuid": legal_entity_uuid,
                },
                msg=f"{error_message}\n{formatted_traceback}",
                user_uuid=user_data["user_uuid"],
            )
            
            response_content = {"msg": f"ОШИБКА! #{log_id}"}
            return JSONResponse(content=response_content)

@router.delete(
    "/delete_legal_entities",
    description="""
    Удаление ЮЛ.
    """,
    dependencies=[Depends(check_app_auth)],
)
@limiter.limit("3/second")
async def delete_legal_entities(  # TODO Нужно предусмотреть параметр для удаления из хранилища Директорий и Документов (ЮЛ и ПР)
    request: Request,
    legal_entities_uuids: List[str] = Query(
        [],
        description="Массив UUID ЮЛ к удалению."
    ),
    
    token: str = Depends(UserQaSM.get_current_user_data),
    
    session: AsyncSession = Depends(get_async_session),
) -> JSONResponse:
    try:
        user_data: Dict[str, str|int] = token.model_dump()   # Парсинг данных пользователя
        
        await LegalEntityService.delete_legal_entities(
            session=session,
            
            requester_user_id=user_data["user_id"],
            requester_user_uuid=user_data["user_uuid"],
            requester_user_privilege=user_data["privilege_id"],
            
            legal_entities_uuids=legal_entities_uuids,
        )
        
        # TODO тут нужно уведомление для 1 и множества лиц (нужна фоновая задача)
        
        return JSONResponse({"msg": "ЮЛ успешно удалено/ы."})
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
                endpoint="delete_legal_entities",
                params={
                    "legal_entities_uuids": legal_entities_uuids,
                },
                msg=f"{error_message}\n{formatted_traceback}",
                user_uuid=user_data["user_uuid"],
            )
            
            response_content = {"msg": f"ОШИБКА! #{log_id}"}
            return JSONResponse(content=response_content)

@router.post(
    "/create_persons",
    description="""
    Создание записи о ФЛ(которое относится всегда к ЮЛ).
    
    input: CreatePersonsSchema
    """,
    dependencies=[Depends(check_app_auth)],
)
@limiter.limit("3/second")
async def create_persons(
    request: Request,
    new_persons: CreatePersonsSchema,
    
    token: str = Depends(UserQaSM.get_current_user_data),
    
    session: AsyncSession = Depends(get_async_session),
) -> JSONResponse:
    try:
        user_data: Dict[str, str|int] = token.model_dump()   # Парсинг данных пользователя
        
        new_person_ids: List[int] = await LegalEntityService.create_persons(
            session=session,
            
            requester_user_uuid=user_data["user_uuid"],
            requester_user_privilege=user_data["privilege_id"],
            
            new_persons=new_persons,
        )
        
        le_uuid = new_persons.new_persons[0].legal_entity_uuid
        
        # TODO тут нужно уведомление для 1 и множества лиц (нужна фоновая задача) заменить блок снизу
        
        if user_data["privilege_id"] != PRIVILEGE_MAPPING["Admin"]:
            await NotificationService.notify(
                session=session,
                
                requester_user_id=user_data["user_id"],
                requester_user_uuid=user_data["user_uuid"],
                requester_user_privilege=user_data["privilege_id"],
                
                subject="ЮЛ",
                subject_uuid=le_uuid,
                for_admin=True,
                data=f'Пользователь "{user_data["user_uuid"]}" создал новую/ые запись/и о ФЛ с ID: "{", ".join([str(new_person_id) for new_person_id in new_person_ids])}" в ЮЛ "{le_uuid}".',
                recipient_user_uuid=None,
            )
        
        return JSONResponse(content={"msg": "ФЛ для ЮЛ создано/ы."})
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
@limiter.limit("3/second")
async def get_persons(
    request: Request,
    legal_entity_uuid: Optional[str] = Query(
        None,
        description="(Опционально) Фильтр по UUID ЮЛ."
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
        
        persons: Dict[str, List[Optional[Person]]|Optional[int]] = await LegalEntityService.get_persons(
            session=session,
            
            requester_user_uuid=user_data["user_uuid"],
            requester_user_privilege=user_data["privilege_id"],
            
            legal_entity_uuid=legal_entity_uuid,
            
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
                    legal_entity_uuid=person.legal_entity_uuid,
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
                    "legal_entity_uuid": legal_entity_uuid,
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
    "/update_person",
    description="""
    Обновление информации о ФЛ.
    
    input: UpdatePerson
    """,
    dependencies=[Depends(check_app_auth)],
)
@limiter.limit("3/second")
async def update_person(
    request: Request,
    person_id: int,
    data_for_update: UpdatePerson,
    
    token: str = Depends(UserQaSM.get_current_user_data),
    
    session: AsyncSession = Depends(get_async_session),
) -> JSONResponse:
    try:
        user_data: Dict[str, str|int] = token.model_dump()   # Парсинг данных пользователя
        
        le_uuid: str = await LegalEntityService.update_person(
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
            legal_entity_uuid=data_for_update.legal_entity_uuid,
        )
        
        # TODO тут нужно уведомление для 1 и множества лиц (нужна фоновая задача) заменить блок снизу
        
        if user_data["privilege_id"] != PRIVILEGE_MAPPING["Admin"]:
            await NotificationService.notify(
                session=session,
                
                requester_user_id=user_data["user_id"],
                requester_user_uuid=user_data["user_uuid"],
                requester_user_privilege=user_data["privilege_id"],
                
                subject="ЮЛ",
                subject_uuid=le_uuid,
                for_admin=True,
                data=f'Пользователь "{user_data["user_uuid"]}" внес изменения в информацию о ФЛ с ID "{person_id}".',
                recipient_user_uuid=None,
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

@router.delete(
    "/delete_persons",
    description="""
    Удаление информации о ФЛ.
    """,
    dependencies=[Depends(check_app_auth)],
)
@limiter.limit("3/second")
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
        
        le_uuid: Optional[str] = await LegalEntityService.delete_persons(
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
                
                subject="ЮЛ",
                subject_uuid=le_uuid,
                for_admin=True,
                data=f'Пользователь "{user_data["user_uuid"]}" удалил информацию о ФЛ с ID "{", ".join([str(person_id) for person_id in person_ids])}".',
                recipient_user_uuid=None,
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
