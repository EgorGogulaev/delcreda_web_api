import traceback
from typing import Any, Dict, List, Literal, Optional

from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import APIRouter, Depends, File, HTTPException, Query, Request, UploadFile
from fastapi.responses import JSONResponse, StreamingResponse

from connection_module import get_async_session
from lifespan import limiter
from security import check_app_auth
from src.query_and_statement.file_store_qas_manager import FileStoreQueryAndStatementManager
from src.schemas.user_schema import ClientState
from src.service.user_service import UserService
from src.service.reference_service import ReferenceService
from src.schemas.file_store_schema import (
    AdminDirInfo, AdminFileInfo,
    BaseDirInfo, BaseFileInfo,
    DirInfoFromFS, FileInfoFromFS,
    FiltersUserDirsInfo, FiltersUserFilesInfo,
    OrdersUserDirsInfo, OrdersUserFilesInfo,
    ResponseGetUserDirsInfo, ResponseGetUserFilesInfo,
)
from src.service.notification_service import NotificationService
from src.query_and_statement.user_qas_manager import UserQueryAndStatementManager as UserQaSM
from src.service.file_store_service import FileStoreService
from src.utils.reference_mapping_data.file_store.mapping import DOCUMENT_TYPE_MAPPING, FILE_STORE_SUBJECT_MAPPING
from src.utils.reference_mapping_data.user.mapping import PRIVILEGE_MAPPING 


router = APIRouter(
    tags=["Docs"],
)

@router.get(
    "/download",
    description="""
    Скачивание файла из хранилища.
    """,
    dependencies=[Depends(check_app_auth)],
)
@limiter.limit("3/second")
async def download_file(
    request: Request,
    file_uuid: str = Query(
        ...,
        description="UUID Документа, который который нужно скачать."
    ),
    
    token: str = Depends(UserQaSM.get_current_user_data),
    
    session: AsyncSession = Depends(get_async_session),
) -> StreamingResponse:
    try:
        user_data: Dict[str, str|int] = token.model_dump()   # Парсинг данных пользователя
        
        response: StreamingResponse = await FileStoreService.download(
            session=session,
            
            requester_user_uuid=user_data["user_uuid"],
            requester_user_privilege=user_data["privilege_id"],
            file_uuid=file_uuid,
        )
        
        return response
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
                endpoint="download_file",
                params={
                    "file_uuid": file_uuid,
                },
                msg=f"{error_message}\n{formatted_traceback}",
                user_uuid=user_data["user_uuid"],
            )
            
            response_content = {"msg": f"ОШИБКА! #{log_id}"}
            return JSONResponse(content=response_content)

@router.put(
    "/upload",
    description="""
    Загрузка файла в хранилище.
    """,
    dependencies=[Depends(check_app_auth)],
)
@limiter.limit("3/second")
async def upload_file(
    request: Request,
    directory_uuid: str = Query(
        ...,
        description="UUID Директории, куда будет загружен Документ.",
        min_length=36,
        max_length=36
    ),
    # TODO Это нужно отредактировать
    file_type: Optional[Literal[
        "Agency Agreement",                                                      # "Агентский договор",
        "Appendix",                                                              # "Приложение",
        "Signatory Power of Attorney",                                           # "Доверенность подписанта",
        "Principal's Instruction",                                               # "Поручение Принципала",
        "Payment Order for Bank",                                                # "Платежное поручение для банка",
        "Beneficiary's Invoice (editable)",                                      # "Счет на оплату получателя (редактируемый)",
        "Beneficiary's Invoice (non-editable)",                                  # "Счет на оплату получателя (нередактируемый)",
        "Additional Document on the Basis of the Payment Order (editable)",      # "Дополнительный документ об основании платежного поручения (редактируемый)",
        "Additional Document on the Basis of the Payment Order (non-editable)",  # "Дополнительный документ об основании платежного поручения (нередактируемый)",
        "Bank Confirmation",                                                     # "Подтверждение банка",
        "International Interbank System Confirmation",                           # "Подтверждение международной межбанковской системы",
        "Confirmation of Receipt of Items",                                      # "Подтверждение получения вещей",
        "Bank Confirmation of Currency Conversion",                              # "Подтверждение банка о конвертации валют",
        "Confirmation of Transfer of Funds between Subagent Accounts",           # "Подтверждение перемещения средств между счетами субагента",
        "Other Instruction Document",                                            # "Иной документ поручения",
    ]] = Query(
        None,
        description="Тип Документа."
    ),
    new_file_uuid: Optional[str] = Query(
        None,
        description="(Опиционально) Ручное выставление нового UUID для Документа. (нужно для интеграции в другие системы)",
        min_length=36,
        max_length=36
    ),
    owner_user_uuid: Optional[str] = Query(
        None,
        description="UUID владельца Документа.",
        min_length=36,
        max_length=36
    ),
    
    file: UploadFile = File(..., description="Документ."),
    token: str = Depends(UserQaSM.get_current_user_data),
    
    session: AsyncSession = Depends(get_async_session),
) -> JSONResponse:
    try:
        user_data: Dict[str, str|int] = token.model_dump()   # Парсинг данных пользователя
        
        # TODO Это нужно отредактировать
        file_type_local = {
            "Agency Agreement": "Агентский договор",
            "Appendix": "Приложение",
            "Signatory Power of Attorney": "Доверенность подписанта",
            "Principal's Instruction": "Поручение Принципала",
            "Payment Order for Bank": "Платежное поручение для банка",
            "Beneficiary's Invoice (editable)": "Счет на оплату получателя (редактируемый)",
            "Beneficiary's Invoice (non-editable)": "Счет на оплату получателя (нередактируемый)",
            "Additional Document on the Basis of the Payment Order (editable)": "Дополнительный документ об основании платежного поручения (редактируемый)",
            "Additional Document on the Basis of the Payment Order (non-editable)": "Дополнительный документ об основании платежного поручения (нередактируемый)",
            "Bank Confirmation": "Подтверждение банка",
            "International Interbank System Confirmation": "Подтверждение международной межбанковской системы",
            "Confirmation of Receipt of Items": "Подтверждение получения вещей",
            "Bank Confirmation of Currency Conversion": "Подтверждение банка о конвертации валют",
            "Confirmation of Transfer of Funds between Subagent Accounts": "Подтверждение перемещения средств между счетами субагента",
            "Other Instruction Document": "Иной документ поручения",
        }
        
        new_file_uuid: str = await FileStoreService.upload(
            session=session,
            
            file_object=file,
            directory_uuid=directory_uuid,
            requester_user_uuid=user_data["user_uuid"],
            requester_user_privilege=user_data["privilege_id"],
            owner_user_uuid=owner_user_uuid,
            new_file_uuid=new_file_uuid,
            file_type=DOCUMENT_TYPE_MAPPING[file_type_local[file_type]] if file_type else None,
        )
        
        subject_id, subject_uuid = await FileStoreQueryAndStatementManager.get_subject_info_by_directory_uuid(
            session=session,
            
            directory_uuid=directory_uuid,
        )
        
        await NotificationService.notify(
            session=session,
            
            requester_user_id=user_data["user_id"],
            requester_user_uuid=user_data["user_uuid"],
            requester_user_privilege=user_data["privilege_id"],
            
            subject={v:k for k, v in FILE_STORE_SUBJECT_MAPPING.items()}[subject_id],
            subject_uuid=subject_uuid,
            for_admin=True if user_data["privilege_id"] != PRIVILEGE_MAPPING["Admin"] else False,
            data=f'Пользователь "{user_data["user_uuid"]}" загрузил Документ "{new_file_uuid}" в Директорию "{directory_uuid}".' if user_data["privilege_id"] != PRIVILEGE_MAPPING["Admin"] else f'Администратор загрузил новый Документ "{new_file_uuid}".',
            recipient_user_uuid=None if user_data["privilege_id"] != PRIVILEGE_MAPPING["Admin"] else owner_user_uuid,
            
            is_important=True,
        )
        
        return JSONResponse(content={"msg": "Файл успешно загружен."})
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
                endpoint="upload_file",
                params={
                    "directory_uuid": directory_uuid,
                    "file_type": file_type,
                    "new_file_uuid": new_file_uuid,
                    "owner_user_uuid": owner_user_uuid,
                    "file": f"{file.filename} (size: {file.size})" if file else None,
                },
                msg=f"{error_message}\n{formatted_traceback}",
                user_uuid=user_data["user_uuid"],
            )
            
            response_content = {"msg": f"ОШИБКА! #{log_id}"}
            return JSONResponse(content=response_content)

@router.post(
    "/get_user_files_info",
    description="""
    Получение информации о файлах.
    Пользователь может запросить только информацию о своих файлах.
    Админ может получить информацию о всех файлах, всех пользователей.
    
    filter: FiltersUserFilesInfo
    order: OrdersUserFilesInfo
    state: ClientState
    output: ResponseGetUserFilesInfo
    """,
    dependencies=[Depends(check_app_auth)],
)
@limiter.limit("3/second")
async def get_user_files_info(
    request: Request,
    visible: Literal["visible", "invisible", "all"] = Query(
        "all",
        description="Фильтр по статусу видимости."
    ),
    owner_user_uuid: Optional[str] = Query(
        None,
        description="(Опиционально) Фильтр по UUID владельца (точное совпадение).",
        min_length=36,
        max_length=36
    ),
    uploader_user_uuid: Optional[str] = Query(
        None,
        description="(Опиционально) Фильтр по UUID пользователя загрузившего файл (точное совпадение).",
        min_length=36,
        max_length=36
    ),
    directory_uuid: Optional[str] = Query(
        None,
        description="(Опиционально) Фильтр по UUID Директории (точное совпадение).",
        min_length=36,
        max_length=36
    ),
    file_uuid: Optional[str] = Query(
        None,
        description="(Опиционально) Фильтр по UUID Документа (точное совпадение).",
        min_length=36,
        max_length=36
    ),
    
    with_data_from_fs: Optional[bool] = Query(
        None,
        description="С данными из файловой системы?(true(null)-да/false-нет)"
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
    
    filter: Optional[FiltersUserFilesInfo] = None,
    order: Optional[OrdersUserFilesInfo] = None,
    
    token: str = Depends(UserQaSM.get_current_user_data),
    
    session: AsyncSession = Depends(get_async_session),
    
    client_state: Optional[ClientState] = None,
) -> ResponseGetUserFilesInfo:
    try:
        user_data: Dict[str, str|int] = token.model_dump()   # Парсинг данных пользователя
        
        if client_state is None:
            client_state: ClientState = await UserService.get_client_state(
                requester_user_uuid=user_data["user_uuid"],
                requester_user_privilege=user_data["privilege_id"],
                user_uuid=user_data["user_uuid"],
            )
        client_state_data: Dict[str, Any] = client_state.model_dump()["data"]
        
        response_content = ResponseGetUserFilesInfo(
            data_from_db=[],
            data_from_fs=[],
            count=0,
            total_records=None,
            total_pages=None,
        )
        
        data_from_db: Dict[str, Any] = await FileStoreService.get_doc_info_from_db(
            session=session,
            
            requester_user_uuid=user_data["user_uuid"],
            requester_user_privilege=user_data["privilege_id"],
            owner_user_uuid=owner_user_uuid,
            uploader_user_uuid=uploader_user_uuid,
            directory_uuid=directory_uuid,
            file_uuids=[file_uuid] if file_uuid else None,
            visible=True if visible == "visible" else False if visible == "invisible" else None,
            
            page=page,
            page_size=page_size,
            
            filter=filter,
            order=order,
            
            tz=client_state_data.get("tz"),
        )
        
        # Обработка данных из БД
        for doc_id, row in data_from_db["data"].items():
            if user_data["privilege_id"] == PRIVILEGE_MAPPING["Admin"]:
                response_content.data_from_db.append(AdminFileInfo(**row))
            else:
                response_content.data_from_db.append(BaseFileInfo(**row))
        
        # Обработка данных из файловой системы (для админов)
        if user_data["privilege_id"] == PRIVILEGE_MAPPING["Admin"] and with_data_from_fs is not False:
            for doc_id in data_from_db["data"]:
                row = data_from_db["data"][doc_id]
                fs_info = await FileStoreService.get_doc_info_from_fs(row["path"])
                response_content.data_from_fs.append(FileInfoFromFS(**fs_info))
        
        response_content.count = data_from_db["count"]
        response_content.total_records = data_from_db["total_records"]
        response_content.total_pages = data_from_db["total_pages"]
        
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
                endpoint="get_user_files_info",
                params={
                    "visible": visible,
                    "owner_user_uuid": owner_user_uuid,
                    "uploader_user_uuid": uploader_user_uuid,
                    "directory_uuid": directory_uuid,
                    "file_uuid": file_uuid,
                    "with_data_from_fs": with_data_from_fs,
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
    "/get_user_dirs_info",
    description="""
    Получение информации о директориях.
    Пользователь может запросить только информацию о своих директориях.
    Админ может получить информацию о всех директориях, всех пользователей.
    
    filter: FiltersUserDirsInfo
    order: OrdersUserDirsInfo
    state: ClientState
    output: ResponseGetUserDirsInfo
    """,
    dependencies=[Depends(check_app_auth)],
)
@limiter.limit("3/second")
async def get_user_dirs_info(
    request: Request,
    visible: Literal["visible", "invisible", "all"] = Query(
        "all",
        description="Фильтр по статусу видимости."
    ),
    owner_user_uuid: Optional[str] = Query(
        None,
        description="(Опиционально) Фильтр по UUID владельца (точное совпадение).",
        min_length=36,
        max_length=36
    ),
    uploader_user_uuid: Optional[str] = Query(
        None,
        description="(Опиционально) Фильтр по UUID пользователя загрузившего файл (точное совпадение).",
        min_length=36,
        max_length=36
    ),
    directory_uuid: Optional[str] = Query(
        None,
        description="(Опиционально) Фильтр по UUID Директории (точное совпадение).",
        min_length=36,
        max_length=36
    ),
    
    with_data_from_fs: Optional[bool] = Query(
        None,
        description="С данными из файловой системы?(true(null)-да/false-нет)"
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
    
    filter: Optional[FiltersUserDirsInfo] = None,
    order: Optional[OrdersUserDirsInfo] = None,
    
    token: str = Depends(UserQaSM.get_current_user_data),
    
    session: AsyncSession = Depends(get_async_session),
    
    client_state: Optional[ClientState] = None,
) -> ResponseGetUserDirsInfo:
    try:
        user_data: Dict[str, str|int] = token.model_dump()   # Парсинг данных пользователя
        
        if client_state is None:
            client_state: ClientState = await UserService.get_client_state(
                requester_user_uuid=user_data["user_uuid"],
                requester_user_privilege=user_data["privilege_id"],
                user_uuid=user_data["user_uuid"],
            )
        client_state_data: Dict[str, Any] = client_state.model_dump()["data"]
        
        response_content = ResponseGetUserDirsInfo(
            data_from_db=[],
            data_from_fs=[],
            count=0,
            total_records=None,
            total_pages=None,
        )
        
        data_from_db: Dict[str, Any] = await FileStoreService.get_dir_info_from_db(
            session=session,
            
            requester_user_uuid=user_data["user_uuid"],
            requester_user_privilege=user_data["privilege_id"],
            owner_user_uuid=owner_user_uuid,
            uploader_user_uuid=uploader_user_uuid,
            directory_uuids=[directory_uuid] if directory_uuid else None,
            visible=True if visible == "visible" else False if visible == "invisible" else None,
            
            page=page,
            page_size=page_size,
            
            filter=filter,
            order=order,
            
            tz=client_state_data.get("tz"),
        )
        
        # Обработка данных из БД
        for dir_id, row in data_from_db["data"].items():
            if user_data["privilege_id"] == PRIVILEGE_MAPPING["Admin"]:  # Admin
                response_content.data_from_db.append(AdminDirInfo(**row))
            else:
                response_content.data_from_db.append(BaseDirInfo(**row))
        
        # Обработка данных из файловой системы (для админов)
        if user_data["privilege_id"] == PRIVILEGE_MAPPING["Admin"] and with_data_from_fs is not False:
            for dir_id in data_from_db["data"]:
                row = data_from_db["data"][dir_id]
                fs_info = await FileStoreService.get_dir_info_from_fs(row["path"])
                response_content.data_from_fs.append(DirInfoFromFS(**fs_info))
        
        response_content.count = data_from_db["count"]
        response_content.total_records = data_from_db["total_records"]
        response_content.total_pages = data_from_db["total_pages"]
        
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
                endpoint="get_user_dirs_info",
                params={
                    "visible": visible,
                    "owner_user_uuid": owner_user_uuid,
                    "uploader_user_uuid": uploader_user_uuid,
                    "directory_uuid": directory_uuid,
                    "with_data_from_fs": with_data_from_fs,
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
    "/change_visibility",
    description="""
    Изменить статус видимости файла/директории.
    (Используется вместо удаления со стороны Пользователя)
    """,
    dependencies=[Depends(check_app_auth)],
)
@limiter.limit("3/second")
async def change_visibility(
    request: Request,
    visibility_status: bool = Query(
        False,
        description="Значение, которое будет выставлено в статусе видимости."
    ),
    uuids: List[str] = Query(
        [],
        description="Массив UUID'ов Документов/Директорий."
    ),
    is_document: bool = Query(
        True,
        description="Это Документ?(то, для чего меняем статус видимости. true-да/false-нет)"
    ),
    
    token: str = Depends(UserQaSM.get_current_user_data),
    
    session: AsyncSession = Depends(get_async_session),
) -> JSONResponse:
    try:
        user_data: Dict[str, str|int] = token.model_dump()   # Парсинг данных пользователя
        
        await FileStoreService.change_visibility(
            session=session,
            
            requester_user_id=user_data["user_id"],
            requester_user_uuid=user_data["user_uuid"],
            requester_user_privilege=user_data["privilege_id"],
            
            visibility_status=visibility_status,
            uuids=uuids,
            is_document=is_document,
        )
        
        return JSONResponse(content={"msg": f'Видимость {"Файла" if is_document else "Директории"} изменена на {visibility_status}.'})
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
                endpoint="change_visibility",
                params={
                    "visibility_status": visibility_status,
                    "uuids": uuids,
                    "is_document": is_document,
                },
                msg=f"{error_message}\n{formatted_traceback}",
                user_uuid=user_data["user_uuid"],
            )
            
            response_content = {"msg": f"ОШИБКА! #{log_id}"}
            return JSONResponse(content=response_content)

@router.delete(
    "/delete_doc_or_dir",
    description="""
    Удаление файла/директории.
    (Может делать только Админ)
    """,
    dependencies=[Depends(check_app_auth)],
)
@limiter.limit("3/second")
async def delete_doc_or_dir(
    request: Request,
    uuid: str = Query(
        ...,
        description="UUID Документа/Директории.",
        min_length=36,
        max_length=36
    ),
    is_document: bool = Query(
        True,
        description="Это Документ?(то, что хотим удалить. true-да/false-нет)"
    ),
    
    token: str = Depends(UserQaSM.get_current_user_data),
    
    session: AsyncSession = Depends(get_async_session),
) -> JSONResponse:
    try:
        user_data: Dict[str, str|int] = token.model_dump()   # Парсинг данных пользователя
        
        await FileStoreService.delete_doc_or_dir(
            session=session,
            
            requester_user_id=user_data["user_id"],
            requester_user_uuid=user_data["user_uuid"],
            requester_user_privilege=user_data["privilege_id"],
            
            uuid=uuid,
            is_document=is_document,
        )
        
        # TODO тут нужно сделать уведомление
        
        return JSONResponse(content={"msg": f'{"Файл" if is_document else "Директория"} с uuid "{uuid}" удален{"" if is_document else "а"}.'})
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
                endpoint="delete_doc_or_dir",
                params={
                    "uuid": uuid,
                    "is_document": is_document,
                },
                msg=f"{error_message}\n{formatted_traceback}",
                user_uuid=user_data["user_uuid"],
            )
            
            response_content = {"msg": f"ОШИБКА! #{log_id}"}
            return JSONResponse(content=response_content)
