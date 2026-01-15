import traceback
from typing import Dict, Literal, Optional

from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import JSONResponse

from connection_module import get_async_session
from lifespan import limiter
from security import check_app_auth
from src.service.contract_service import ContractService
from src.service.reference_service import ReferenceService
from src.query_and_statement.user_qas_manager import UserQueryAndStatementManager as UserQaSM



router = APIRouter(
    tags=["Contract"],
)

@router.post(
    "/create_contract",
    description="""
    """,
    dependencies=[Depends(check_app_auth)],
)
@limiter.limit("30/second")
async def create_contract(
    request: Request,
    
    document_uuid: str = Query(
        str,
        description="UUID документа Договора (Используется, если в системе уже есть Документ КП, иначе использовать null).",
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
        
        await ContractService.create_contract(
            session=session,
            
            requester_user_uuid=user_data["user_uuid"],
            requester_user_privilege=user_data["privilege_id"],
            
            document_uuid=document_uuid,
            type=type,
            
            start_date=start_date,
            expiration_date=expiration_date,
        )
        
        # TODO нужно уведомление
        
        response_content = {"msg": f'На основании документа с UUID: "{document_uuid}" создана карточка Договора с типом "{type}".'}
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
                    # TODO
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
    """,
    dependencies=[Depends(check_app_auth)],
)
@limiter.limit("30/second")
async def get_contracts(
    request: Request,
    
    token: str = Depends(UserQaSM.get_current_user_data),
    session: AsyncSession = Depends(get_async_session),
):  # TODO тут нужен свой класс с типизацией
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
                endpoint="get_contracts",
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

@router.put(
    "/update_contract",
    description="""
    """,
    dependencies=[Depends(check_app_auth)],
)
@limiter.limit("30/second")
async def update_contract(
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
                endpoint="update_contract",
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
