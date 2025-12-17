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
from src.schemas.commercial_proposal_schema import CommercialProposal, FiltersCommercialProposals, OrdersCommercialProposals, ResponseGetCommercialProposals
from src.query_and_statement.user_qas_manager import UserQueryAndStatementManager as UserQaSM
from src.utils.reference_mapping_data.user.mapping import PRIVILEGE_MAPPING
from src.utils.tz_converter import convert_tz


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
    
    commercial_proposal_name: Optional[str] = Query(
        None,
        description="Название КП (используется если уже известно название Документа, иначе использовать null)",
    ),
    document_uuid: Optional[str] = Query(
        None,
        description="UUID документа КП (Используется, если в системе уже есть Документ КП, иначе использовать null).",
        min_length=36,
        max_length=36,
    ),
    
    type: Literal[
        "MT",
    ] = Query(
        ...,
        description="Тип заявки на КП.",
    ),
    
    target_user_uuid: str = Query(
        ...,
        description="Целевой пользователь для кого создается заявка на КП.",
        min_length=36,
        max_length=36,
    ),
    counterparty_uuid: str = Query(
        ...,
        description="UUID карточки Контрагента к котомору будет прикреплена заявка на КП.",
        min_length=36,
        max_length=36,
    ),
    application_uuid: Optional[str] = Query(
        None,
        description="UUID Заявки к которому будет прикреплена заявка на КП.",
        min_length=36,
        max_length=36,
    ),
    
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
            
            subject="Заявка на КП",
            subject_uuid=new_commercial_proposal_uuid,
            for_admin=True if user_data["privilege_id"] != PRIVILEGE_MAPPING["Admin"] else False,
            data=(f'Пользователь "<user>" ({user_data["user_uuid"]}) создал новую заявку по КП - "<commercial_proposal>" ({new_commercial_proposal_uuid})' if user_data["privilege_id"] != PRIVILEGE_MAPPING["Admin"] else f'Администратор создал новую заявку на КП "<commercial_proposal>" ({new_commercial_proposal_uuid}), ') + (f'которая относится к Заявке <application> (контрагент - "<counterparty>")' if application_uuid else f'которая относится к Контрагенту - "<counterparty>"'),
            recipient_user_uuid=None if user_data["privilege_id"] != PRIVILEGE_MAPPING["Admin"] else target_user_uuid,
            request_options=request_options,
        )
        
        response_content = {"msg": "Заявка на КП успешно создана."}
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
                    "commercial_proposal_name": commercial_proposal_name,
                    "document_uuid": document_uuid,
                    "type": type,
                    "target_user_uuid": target_user_uuid,
                    "counterparty_uuid": counterparty_uuid,
                    "application_uuid": application_uuid,
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
    Получение заявок по КП
    
    filter: FiltersCommercialProposals
    order: OrdersCommercialProposals
    output: ResponseGetCommercialProposal
    """,
    dependencies=[Depends(check_app_auth)],
)
@limiter.limit("30/second")
async def get_commercial_proposals(
    request: Request,
    
    user_uuid: Optional[str] = Query(
        None,
        description="(Опционально) Фильтр по UUID Пользователя (точное совпадение).",
        min_length=36,
        max_length=36
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
    
    filter: Optional[FiltersCommercialProposals] = None,
    order: Optional[OrdersCommercialProposals] = None,
    
    token: str = Depends(UserQaSM.get_current_user_data),
    session: AsyncSession = Depends(get_async_session),
) -> ResponseGetCommercialProposals:
    try:
        user_data: Dict[str, str|int] = token.model_dump()   # Парсинг данных пользователя
        
        commercial_proposals = await CommercialProposalService.get_commercial_proposals(
            session=session,
            
            requester_user_uuid=user_data["user_uuid"],
            requester_user_privilege=user_data["privilege_id"],
            
            user_uuid=user_uuid,
            
            page=page,
            page_size=page_size,
            
            filter=filter,
            order=order,
        )
        
        response_content = ResponseGetCommercialProposals(
            data=[],
            count=0,
            total_records=None,
            total_pages=None,
        )
        for commercial_proposal in commercial_proposals["data"]:
            response_content.data.append(
                CommercialProposal(
                    uuid=commercial_proposal.uuid,
                    appliaction_name=commercial_proposal.appliaction_name,
                    commercial_proposal_name=commercial_proposal.commercial_proposal_name,
                    type=commercial_proposal.type,
                    user_id=commercial_proposal.user_id,
                    user_uuid=commercial_proposal.user_uuid,
                    counterparty_id=commercial_proposal.counterparty_id,
                    counterparty_uuid=commercial_proposal.counterparty_uuid,
                    application_id=commercial_proposal.application_id,
                    application_uuid=commercial_proposal.application_uuid,
                    directory_id=commercial_proposal.directory_id,
                    directory_uuid=commercial_proposal.directory_uuid,
                    document_uuid=commercial_proposal.document_uuid,
                    status=commercial_proposal.status,
                    can_be_updated_by_user=commercial_proposal.can_be_updated_by_user,
                    updated_at=convert_tz(commercial_proposal.updated_at.strftime("%d.%m.%Y %H:%M:%S UTC")) if commercial_proposal.updated_at else None,
                    created_at=convert_tz(commercial_proposal.created_at.strftime("%d.%m.%Y %H:%M:%S UTC")) if commercial_proposal.created_at else None,
                )
            )
            response_content.count += 1
        
        response_content.total_records = commercial_proposals["total_records"]
        response_content.total_pages = commercial_proposals["total_pages"]
        
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
        description="Массив UUID'ов заявок на КП."
    ),
    
    new_status: Literal[
        "На рассмотрении сторон",
        "Согласовано"
        "Отклонено"
        "Закрыто администратором"
    ] = Query(
        ...,
        description="На какой статус будем изменять?",
    ),
    
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
        
        # TODO Реализовать уведомление
        
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
    "/change_commercial_proposal_document_uuid",
    description="""
    Обновление Документа КП.
    """,
    dependencies=[Depends(check_app_auth)],
)
@limiter.limit("30/second")
async def change_commercial_proposal_document_uuid(
    request: Request,
    
    commercial_proposal_uuid: str = Query(
        ...,
        description="UUID заявки на КП.",
        min_length=36,
        max_length=36,
    ),
    
    document_uuid: str = Query(
        ...,
        description="UUID документа КП.",
        min_length=36,
        max_length=36,
    ),
    
    token: str = Depends(UserQaSM.get_current_user_data),
    session: AsyncSession = Depends(get_async_session),
) -> JSONResponse:
    try:
        user_data: Dict[str, str|int] = token.model_dump()   # Парсинг данных пользователя
        
        user_uuid, counterparty_uuid, application_uuid = await CommercialProposalService.change_commercial_proposal_document_uuid(
            session=session,
            requester_user_uuid=user_data["user_uuid"],
            requester_user_privilege=user_data["privilege_id"],
            commercial_proposal_uuid=commercial_proposal_uuid,
            document_uuid=document_uuid,
        )
        
        msg = f'Администратор сменил документ КП для заявки на КП "<commercial_proposal>", относящейся: к карточке Контрагента - "<counterparty>"'
        request_options = {
            "<counterparty>": {
                "uuid": counterparty_uuid,
            },
            "<commercial_proposal>": {
                "uuid": commercial_proposal_uuid,
            },
        }
        if application_uuid:
            request_options.update({"<application>": {"uuid": application_uuid}})
            msg += ', заявке на поручение - "<application>".'
        else:
            msg += "."
        
        await NotificationService.notify(
            session=session,
            requester_user_id=user_data["user_id"],
            requester_user_uuid=user_data["user_uuid"],
            requester_user_privilege=user_data["privilege_id"],
            
            subject="Заявка на КП",
            subject_uuid=commercial_proposal_uuid,
            for_admin=False,
            data=msg,
            recipient_user_uuid=user_uuid,
            request_options=request_options,
        )
        
        response_content = {"msg": "Новый Документ прикреплен к заявке на КП."}
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
                endpoint="change_commercial_proposal_uuid",
                params={
                    "commercial_proposal_uuid": commercial_proposal_uuid,
                    "document_uuid": document_uuid,
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
