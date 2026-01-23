import traceback
from typing import Dict, Literal, Optional, Tuple

from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import JSONResponse

from connection_module import get_async_session
from lifespan import limiter
from security import check_app_auth
from src.schemas.contract_schema import Contract, FiltersContracts, OrdersContracts, ResponseGetContracts
from src.service.notification_service import NotificationService
from src.service.contract_service import ContractService
from src.service.reference_service import ReferenceService
from src.query_and_statement.user_qas_manager import UserQueryAndStatementManager as UserQaSM
from src.utils.tz_converter import convert_tz



router = APIRouter(
    tags=["Contract"],
)

@router.post(
    "/create_contract",
    description="""
    Создание карточки Договора
    """,
    dependencies=[Depends(check_app_auth)],
)
@limiter.limit("30/second")
async def create_contract(
    request: Request,
    
    file_uuid: str = Query(
        str,
        description="UUID документа Договора.",
        min_length=36,
        max_length=36,
    ),
    type: Literal[
        "MT",
        # TODO тут будут другие типы Договоров
    ] = Query(
        str,
        description="Тип Договора.",
    ),
    
    start_date: Optional[str] = Query(
        None,
        description="Дата, когда Договор вступает в действие. (Формат: 'dd.mm.YYYY')",
    ),
    expiration_date: Optional[str] = Query(
        None,
        description="Дата, когда действие Договора истекает. (Формат: 'dd.mm.YYYY')",
    ),
    
    token: str = Depends(UserQaSM.get_current_user_data),
    session: AsyncSession = Depends(get_async_session),
) -> JSONResponse:
    try:
        user_data: Dict[str, str|int] = token.model_dump()   # Парсинг данных пользователя
        
        counterparty_uuid, application_uuid, new_contract_uuid, owner_user_uuid, contract_name = Tuple[str, Optional[str], str, str, str] = await ContractService.create_contract(
            session=session,
            
            requester_user_uuid=user_data["user_uuid"],
            requester_user_privilege=user_data["privilege_id"],
            
            file_uuid=file_uuid,
            type=type,
            
            start_date=start_date,
            expiration_date=expiration_date,
        )
        
        request_options = {
            "<counterparty>": {
                "uuid": counterparty_uuid,
            },
        }
        if application_uuid:
            request_options.update({"<application>": {"uuid": application_uuid}})
        
        await NotificationService.notify(
            session=session,
            requester_user_id=user_data["user_id"],
            requester_user_uuid=user_data["user_uuid"],
            requester_user_privilege=user_data["privilege_id"],
            
            subject="Договор",
            subject_uuid=new_contract_uuid,
            for_admin=False,
            data=(
                f'Администратор прикрепил карточку Договора "{contract_name}" к Заявке на ПР - <application> (UUID: "{application_uuid}"), которая относится к карточке Контрагента - <counterparty> (UUID: "{counterparty_uuid}").'
                if application_uuid is not None else
                f'Администратор прикрепил карточку Договора "{contract_name}" к карточке Контрагента - <counterparty> (UUID: "{counterparty_uuid}").'
            ),
            recipient_user_uuid=owner_user_uuid,
            request_options=request_options,
        )
        
        response_content = {"msg": f'На основании документа с UUID: "{file_uuid}" создана карточка Договора с типом "{type}".'}
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
                endpoint="create_contract",
                params={
                    "file_uuid": file_uuid,
                    "type": type,
                    "start_date": start_date,
                    "expiration_date": expiration_date,
                },
                msg=f"{error_message}\n{formatted_traceback}",
                user_uuid=user_data["user_uuid"],
            )
            
            response_content = {"msg": f"ОШИБКА! #{log_id}"}
            return JSONResponse(content=response_content)
    finally:
        await session.rollback()


@router.post(
    "/get_contracts",
    description="""
    Получение карточек Договоров
    
    filter: FiltersContracts
    order: OrdersContracts
    output: ResponseGetContracts
    """,
    dependencies=[Depends(check_app_auth)],
)
@limiter.limit("30/second")
async def get_contracts(
    request: Request,
    
    user_uuid: Optional[str] = Query(
        None,
        description="(Опционально) Фильтр по UUID Пользователя (точное совпадение).",
        min_length=36,
        max_length=36,
    ),
    
    page: Optional[int] = Query(
        None,
        description="Пагинация (По умолчанию - 1).",
        example=1
    ),
    page_size: Optional[int] = Query(
        None,
        description="Размер страницы (По умолчанию - 50).",
        example=50
    ),
    
    filter: Optional[FiltersContracts] = None,
    order: Optional[OrdersContracts] = None,
    
    token: str = Depends(UserQaSM.get_current_user_data),
    session: AsyncSession = Depends(get_async_session),
) -> ResponseGetContracts:
    try:
        user_data: Dict[str, str|int] = token.model_dump()   # Парсинг данных пользователя
        
        contracts = await ContractService.get_contracts(
            session=session,
            
            requester_user_uuid=user_data["user_uuid"],
            requester_user_privilege=user_data["privilege_id"],
            
            user_uuid=user_uuid,
            
            page=page,
            page_size=page_size,
            
            filter=filter,
            order=order,
        )
        
        response_content = ResponseGetContracts(
            data=[],
            count=0,
            total_records=None,
            total_pages=None,
        )
        for contract in contracts["data"]:
            response_content.data.append(
                Contract(
                    uuid=contract.uuid,
                    name=contract.name,
                    type=contract.type,
                    user_id=contract.user_id,
                    user_uuid=contract.user_uuid,
                    counterparty_id=contract.counterparty_id,
                    counterparty_uuid=contract.counterparty_uuid,
                    application_id=contract.application_id,
                    application_uuid=contract.application_uuid,
                    file_uuid=contract.file_uuid,
                    start_date=contract.start_date.strftime("%d.%m.%Y") if contract.start_date else None,
                    expiration_date=contract.expiration_date.strftime("%d.%m.%Y") if contract.expiration_date else None,
                    updated_at=convert_tz(contract.updated_at.strftime("%d.%m.%Y %H:%M:%S UTC")) if contract.updated_at else None,
                    created_at=convert_tz(contract.created_at.strftime("%d.%m.%Y %H:%M:%S UTC")) if contract.created_at else None,
                )
            )
            response_content.count += 1
        
        response_content.total_records = contract["total_records"]
        response_content.total_pages = contract["total_pages"]
        
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
                endpoint="get_contracts",
                params={
                    "user_uuid": user_uuid,
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
    "/update_contract_date_range",
    description="""
    Обновление диапазона действия контракта
    """,
    dependencies=[Depends(check_app_auth)],
)
@limiter.limit("30/second")
async def update_contract_date_range(
    request: Request,
    
    contract_uuid: str = Query(
        ...,
        description="Карточка Договора к редактированию.",
        min_length=36,
        max_length=36,
    ),
    
    new_start_date: Optional[str] = Query(
        "~",
        description="Новая дата, когда Договор вступает в действие ('~' - оставляет текущее значение). (Формат: 'dd.mm.YYYY')",
    ),
    new_expiration_date: Optional[str] = Query(
        "~",
        description="Новая дата, когда действие Договора истекает ('~' - оставляет текущее значение). (Формат: 'dd.mm.YYYY')",
    ),
    
    token: str = Depends(UserQaSM.get_current_user_data),
    session: AsyncSession = Depends(get_async_session),
) -> JSONResponse:
    try:
        user_data: Dict[str, str|int] = token.model_dump()   # Парсинг данных пользователя
        
        await ContractService.update_contract_date_range(
            session=session,
            
            contract_uuid=contract_uuid,
            new_start_date=new_start_date,
            new_expiration_date=new_expiration_date,
        )
        
        response_content = {"msg": f'Временной диапазон действия Договра ("{contract_uuid}") успешно изменен'}
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
                endpoint="update_contract_date_range",
                params={
                    "contract_uuid": contract_uuid,
                    "new_start_date": new_start_date,
                    "new_expiration_date": new_expiration_date,
                },
                msg=f"{error_message}\n{formatted_traceback}",
                user_uuid=user_data["user_uuid"],
            )
            
            response_content = {"msg": f"ОШИБКА! #{log_id}"}
            return JSONResponse(content=response_content)
    finally:
        await session.rollback()

@router.put(
    "/change_contract_file",
    description="""
    Прикрепление нового Документа к карточке Договора
    """,
    dependencies=[Depends(check_app_auth)],
)
@limiter.limit("30/second")
async def change_contract_file(
    request: Request,
    
    contract_uuid: str = Query(
        ...,
        description="Карточка Договора к которой будет прикреплен новый Документ.",
        min_length=36,
        max_length=36,
    ),
    new_file_uuid: str = Query(
        ...,
        description="Новый Документ Договора к прикреплению.",
        min_length=36,
        max_length=36,
    ),
    
    token: str = Depends(UserQaSM.get_current_user_data),
    session: AsyncSession = Depends(get_async_session),
) -> JSONResponse:
    try:
        user_data: Dict[str, str|int] = token.model_dump()   # Парсинг данных пользователя
        
        await ContractService.change_contract_file(
            session=session,
            requester_user_uuid=user_data["user_uuid"],
            requester_user_privilege=user_data["privilege_id"],
            contract_uuid=contract_uuid,
            new_file_uuid=new_file_uuid,
        )
        
        return JSONResponse(content=f'Новый Документ "{new_file_uuid}" усешно прикреплен к карточке Договора "{contract_uuid}".')
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
                endpoint="change_contract_file",
                params={
                    # TODO
                },
                msg=f"{error_message}\n{formatted_traceback}",
                user_uuid=user_data["user_uuid"],
            )
            
            response_content = {"msg": f"ОШИБКА! #{log_id}"}
            return JSONResponse(content=response_content)
    finally:
        await session.rollback()


@router.delete(
    "/delete_contracts",
    description="""
    Удаление карточек Договоров
    """,
    dependencies=[Depends(check_app_auth)],
)
@limiter.limit("30/second")
async def delete_contracts(
    request: Request,
    
    token: str = Depends(UserQaSM.get_current_user_data),
    session: AsyncSession = Depends(get_async_session),
) -> JSONResponse:
    try:
        user_data: Dict[str, str|int] = token.model_dump()   # Парсинг данных пользователя
        ...  # TODO
        
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
                endpoint="delete_contracts",
                params={
                    # TODO
                },
                msg=f"{error_message}\n{formatted_traceback}",
                user_uuid=user_data["user_uuid"],
            )
            
            response_content = {"msg": f"ОШИБКА! #{log_id}"}
            return JSONResponse(content=response_content)
    finally:
        await session.rollback()
