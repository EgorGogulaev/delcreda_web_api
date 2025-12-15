import traceback
from typing import Dict, List, Literal, Optional

from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import JSONResponse

from connection_module import get_async_session
from lifespan import limiter
from security import check_app_auth
from src.service.notification_service import NotificationService
from src.service.commercial_proposal_service import CommercialProposalService
from src.service.reference_service import ReferenceService
from src.schemas.commercial_proposal_schema import ResponseGetCommercialProposal
from src.query_and_statement.user_qas_manager import UserQueryAndStatementManager as UserQaSM
from src.utils.reference_mapping_data.user.mapping import PRIVILEGE_MAPPING


router = APIRouter(
    tags=["Commercial proposal"],
)

@router.post(
    "/create_commercial_proposal",
    description="""
    """,
    dependencies=[Depends(check_app_auth)],
)
@limiter.limit("30/second")
async def create_commercial_proposal(
    request: Request,
    
    commercial_proposal_name: Optional[str] = Query(None,),
    type: Literal[
        "MT",
    ] = Query(...,),
    
    target_user_uuid: str = Query(...),
    counterparty_uuid: str = Query(...),
    application_uuid: Optional[str] = Query(None),
    
    document_uuid: Optional[str] = Query(None),
    
    token: str = Depends(UserQaSM.get_current_user_data),
    session: AsyncSession = Depends(get_async_session),
) -> JSONResponse:
    try:
        user_data: Dict[str, str|int] = token.model_dump()   # Парсинг данных пользователя
        new_commercial_proposal_uuid: str = await CommercialProposalService.create_commercial_proposal(
            session=session,
            
            requester_user_uuid=user_data["user_uuid"],
            requester_user_privilege=user_data["privilege_id"],
            
            type=type,
            target_user_uuid=target_user_uuid,
            counterparty_uuid=counterparty_uuid,
            application_uuid=application_uuid,
            document_uuid=document_uuid,
            commercial_proposal_name=commercial_proposal_name,
        )
        request_options = {
            "<user>": {
                "uuid": user_data["user_uuid"],
            },
            "<commercial_proposal>": {
                "uuid": new_commercial_proposal_uuid,
            },
            "<counterparty_uuid>": {
                "uuid": counterparty_uuid,
            },
        } if user_data["privilege_id"] != PRIVILEGE_MAPPING["Admin"] else {
            "<commercial_proposal>": {
                "uuid": new_commercial_proposal_uuid,
            },
            "<counterparty_uuid>": {
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
            
            subject="Заявка по КП",
            subject_uuid=new_commercial_proposal_uuid,
            for_admin=True if user_data["privilege_id"] != PRIVILEGE_MAPPING["Admin"] else False,
            data=(f'Пользователь "<user>" ({user_data["user_uuid"]}) создал новую заявку по КП - "<commercial_proposal>" ({new_commercial_proposal_uuid})' if user_data["privilege_id"] != PRIVILEGE_MAPPING["Admin"] else f'Администратор создал новую заявку на КП "<commercial_proposal>" ({new_commercial_proposal_uuid}), ') + (f'которая относится к Заявке <application> (контрагент - "<counterparty>")' if application_uuid else f'которая относится к Контрагенту - "<counterparty>"'),
            recipient_user_uuid=None if user_data["privilege_id"] != PRIVILEGE_MAPPING["Admin"] else target_user_uuid,
            request_options=request_options,
        )
        
        response_content = {"msg": "Заявка по КП успешно создана."}
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
                endpoint="create_commercial_proposal",
                params={
                    
                },
                msg=f"{error_message}\n{formatted_traceback}",
                user_uuid=user_data["user_uuid"],
            )
            
            response_content = {"msg": f"ОШИБКА! #{log_id}"}
            return JSONResponse(content=response_content)
    finally:
        await session.rollback()

@router.post(
    "/get_commercial_proposals",
    description="""
    """,
    dependencies=[Depends(check_app_auth)],
)
@limiter.limit("30/second")
async def get_commercial_proposals(
    request: Request,
    
    token: str = Depends(UserQaSM.get_current_user_data),
    session: AsyncSession = Depends(get_async_session),
) -> ResponseGetCommercialProposal:
    try:
        user_data: Dict[str, str|int] = token.model_dump()   # Парсинг данных пользователя
        ...  # TODO
        response_content = ResponseGetCommercialProposal(
            # TODO
        )
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
                endpoint="get_commercial_proposals",
                params={
                    
                },
                msg=f"{error_message}\n{formatted_traceback}",
                user_uuid=user_data["user_uuid"],
            )
            
            response_content = {"msg": f"ОШИБКА! #{log_id}"}
            return JSONResponse(content=response_content)
    finally:
        await session.rollback()

@router.put(
    "/update_commercial_proposals_status",
    description="""
    Обновление статуса заявки/ок на КП.
    """,
    dependencies=[Depends(check_app_auth)],
)
@limiter.limit("30/second")
async def update_commercial_proposals_status(
    request: Request,
    
    commercial_proposal_uuids: List[Optional[str]] = Query(
        [],
        description="Массив UUID'ов заявок на КП."),
    
    new_status: Literal[
        "На рассмотрении сторон",
        "Согласовано"
        "Отклонено"
        "Закрыто администратором"
    ] = Query(..., description="На какой статус будем изменять?"),
    
    token: str = Depends(UserQaSM.get_current_user_data),
    session: AsyncSession = Depends(get_async_session),
) -> JSONResponse:
    try:
        user_data: Dict[str, str|int] = token.model_dump()   # Парсинг данных пользователя
        
        await CommercialProposalService.update_commercial_proposals_status(
            session=session,
            requester_user_uuid=user_data["user_uuid"],
            requester_user_privilege=user_data["privilege_id"],
            commercial_proposal_uuids=commercial_proposal_uuids,
            new_status=new_status,
        )
        
        response_content = {"msg": f'Статус/ы КП изменен/ы на "{new_status}".'}
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
                endpoint="update_commercial_proposals_status",
                params={
                    "commercial_proposal_uuids": commercial_proposal_uuids,
                    "new_status": new_status,
                },
                msg=f"{error_message}\n{formatted_traceback}",
                user_uuid=user_data["user_uuid"],
            )
            
            response_content = {"msg": f"ОШИБКА! #{log_id}"}
            return JSONResponse(content=response_content)
    finally:
        await session.rollback()

@router.put(
    "/change_commercial_proposals_edit_status",
    description="""
    Изменение статуса возможности редактировать пользователям заявки на КП.
    """,
    dependencies=[Depends(check_app_auth)],
)
@limiter.limit("30/second")
async def change_commercial_proposals_edit_status(
    request: Request,
    
    commercial_proposal_uuids: List[str] = Query(
        [],
        description="Массив UUID заявок на КП к изменению статуса редактирования.",
    ),
    
    edit_status: bool = Query(
        ...,
        description="На какой статус редактирования будем менять? (true-разрешено/false-запрещено)",
        example=False,
    ),
    
    token: str = Depends(UserQaSM.get_current_user_data),
    session: AsyncSession = Depends(get_async_session),
) -> JSONResponse:
    try:
        user_data: Dict[str, str|int] = token.model_dump()   # Парсинг данных пользователя
        
        await CommercialProposalService.change_commercial_proposals_edit_status(
            session=session,
            requester_user_uuid=user_data["user_uuid"],
            requester_user_privilege=user_data["privilege_id"],
            commercial_proposal_uuids=commercial_proposal_uuids,
            edit_status=edit_status,
        )
        
        response_content  = {"msg": f"Стутс редакирования заявки/ок на КП успешно изменен на {edit_status}."}
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
                endpoint="change_commercial_proposals_edit_status",
                params={
                    "commercial_proposal_uuids": commercial_proposal_uuids,
                    "edit_status": edit_status,
                },
                msg=f"{error_message}\n{formatted_traceback}",
                user_uuid=user_data["user_uuid"],
            )
            
            response_content = {"msg": f"ОШИБКА! #{log_id}"}
            return JSONResponse(content=response_content)
    finally:
        await session.rollback()

@router.delete(
    "/delete_commercial_proposals",
    description="""
    Удаление заявок на КП по UUID.
    """,
    dependencies=[Depends(check_app_auth)],
)
@limiter.limit("30/second")
async def delete_commercial_proposals(
    request: Request,
    
    commercial_proposal_uuids: List[str] = Query(
        [],
        description="Массив UUID заявок на КП к удалению.",
    ),
    
    token: str = Depends(UserQaSM.get_current_user_data),
    session: AsyncSession = Depends(get_async_session),
) -> JSONResponse:
    try:
        user_data: Dict[str, str|int] = token.model_dump()   # Парсинг данных пользователя
        await CommercialProposalService.delete_commercial_proposals(
            session=session,
            requester_user_id=user_data["user_id"],
            requester_user_uuid=user_data["user_uuid"],
            requester_user_privilege=user_data["privilege_id"],
            commercial_proposal_uuids=commercial_proposal_uuids,
        )
        
        response_content = {"msg": "Заявка/и на КП успешно удалена/ы."}
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
                endpoint="delete_commercial_proposals",
                params={
                    "commercial_proposal_uuids": commercial_proposal_uuids,
                },
                msg=f"{error_message}\n{formatted_traceback}",
                user_uuid=user_data["user_uuid"],
            )
            
            response_content = {"msg": f"ОШИБКА! #{log_id}"}
            return JSONResponse(content=response_content)
    finally:
        await session.rollback()
