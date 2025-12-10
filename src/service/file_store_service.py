import os
import posixpath
from pathlib import Path
from typing import Any, Dict, List, Optional
import urllib.parse

from fastapi import status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, UploadFile

from connection_module import SignalConnector
from src.schemas.file_store_schema import FiltersUserDirsInfo, FiltersUserFilesInfo, OrdersUserDirsInfo, OrdersUserFilesInfo
from src.models.file_store_models import Directory, Document
from src.query_and_statement.file_store_qas_manager import FileStoreQueryAndStatementManager
from src.utils.reference_mapping_data.user.mapping import PRIVILEGE_MAPPING
from src.utils.tz_converter import convert_tz


class FileStoreService:
    # _____________________________________________________________________________________________________
    @staticmethod
    async def get_dir_info_from_db(
        session: AsyncSession,
        
        requester_user_uuid: str, requester_user_privilege: int,
        owner_user_uuid: Optional[str]=None, uploader_user_uuid: Optional[str]=None,
        directory_uuids: Optional[List[str]]=None,
        visible: Optional[bool]=None,
        
        page: Optional[int]=None,
        page_size: Optional[int]=None,
        
        filter: Optional[FiltersUserDirsInfo] = None,
        order: Optional[OrdersUserDirsInfo] = None,
        
        tz: Optional[str] = None,
    ) -> Dict[str, Any]:
        if page or page_size:
            if (isinstance(page, int) and page <= 0) or (isinstance(page_size, int) and page_size <= 0):
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Не корректное разделение на страницы, запрошенных данных!")
        if requester_user_privilege != PRIVILEGE_MAPPING["Admin"]:  # Проверка если Пользователь не Админ
            if owner_user_uuid:
                if owner_user_uuid != requester_user_uuid:
                    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Вы не можете просмотреть Директорию другого Пользователя!")
            else:
                owner_user_uuid = requester_user_uuid
            if uploader_user_uuid:
                if uploader_user_uuid != requester_user_uuid:
                    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Вы не можете просмотреть Директорию другого Пользователя!")
            if visible is not None:
                if visible is False:
                    raise HTTPException(status_code=status.HTTP_406_NOT_ACCEPTABLE, detail="Вы не можете просмотреть информацию о скрытой Директории!")
        
        result = {
            "data": {},
            "count": 0,
        }
        
        dir_info_dct: Dict[str, List[Optional[Directory]]|Optional[int]] = await FileStoreQueryAndStatementManager.get_dir_info(
            session=session,
            
            owner_user_uuid=owner_user_uuid,
            uploader_user_uuid=uploader_user_uuid,
            directory_uuids=directory_uuids,
            visible=visible,
            
            page=page,
            page_size=page_size,
            
            filter=filter,
            order=order,
        )
        
        for dir_info in dir_info_dct["data"]:
            result["count"] += 1
            result["data"][dir_info.id] = {
                "uuid": dir_info.uuid,
                "parent": dir_info.parent,
                "owner_user_id": dir_info.owner_user_id,
                "owner_user_uuid": dir_info.owner_user_uuid,
                "uploader_user_id": dir_info.uploader_user_id,
                "uploader_user_uuid": dir_info.uploader_user_uuid,
                "path": dir_info.path,
                "type": dir_info.type,
                "visible": dir_info.visible,
                "is_deleted": dir_info.is_deleted,
                "deleted_at": convert_tz(dir_info.deleted_at.strftime("%d.%m.%Y %H:%M:%S UTC"), tz_city=tz) if dir_info.deleted_at else None,
                "created_at": convert_tz(dir_info.created_at.strftime("%d.%m.%Y %H:%M:%S UTC"), tz_city=tz) if dir_info.created_at else None,
            }
            if requester_user_privilege == PRIVILEGE_MAPPING["Admin"]:
                result["data"][dir_info.id]["visibility_off_time"] = convert_tz(dir_info.visibility_off_time.strftime("%d.%m.%Y %H:%M:%S UTC"), tz_city=tz) if dir_info.visibility_off_time else None
                result["data"][dir_info.id]["visibility_off_user_id"] = dir_info.visibility_off_user_id
                result["data"][dir_info.id]["visibility_off_user_uuid"] = dir_info.visibility_off_user_uuid
                
                result["data"][dir_info.id]["deleted_at"] = convert_tz(dir_info.deleted_at.strftime("%d.%m.%Y %H:%M:%S UTC"), tz_city=tz) if dir_info.deleted_at else None
                result["data"][dir_info.id]["deleters_user_id"] = dir_info.deleters_user_id
                result["data"][dir_info.id]["deleters_user_uuid"] = dir_info.deleters_user_uuid
        result.update(
            {
                "total_records": dir_info_dct["total_records"],
                "total_pages": dir_info_dct["total_pages"],
            }
        )
        return result
    
    @staticmethod
    async def get_dir_info_from_fs(
        dir_path: str,
    ) -> Dict[str, str]:
        data: Dict[str, str] = await SignalConnector.get_object_info_s3(
            path=dir_path if dir_path.endswith("/") else dir_path + "/"
        )
        
        return data
    
    @staticmethod
    async def get_doc_info_from_db(
        session: AsyncSession,
        
        requester_user_uuid: str, requester_user_privilege: int,
        owner_user_uuid: Optional[str] = None, uploader_user_uuid: Optional[str] = None,
        directory_uuid: Optional[str] = None,
        file_uuids: Optional[List[str]] = None,
        visible: Optional[bool] = None,
        
        page: Optional[int] = None,
        page_size: Optional[int] = None,
        
        filter: Optional[FiltersUserFilesInfo] = None,
        order: Optional[OrdersUserFilesInfo] = None,
        
        tz: Optional[str] = None,
    ) -> Dict[str, Any]:
        if page or page_size:
            if (isinstance(page, int) and page <= 0) or (isinstance(page_size, int) and page_size <= 0):
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Не корректное разделение на страницы, запрошенных данных!")
        
        if requester_user_privilege != PRIVILEGE_MAPPING["Admin"]:  # Проверка если Пользователь не Админ
            if owner_user_uuid:
                if owner_user_uuid != requester_user_uuid:
                    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Вы не можете получить данные Докуметов других Пользователей!")
            else:
                owner_user_uuid = requester_user_uuid
            if uploader_user_uuid:
                if uploader_user_uuid != requester_user_uuid:
                    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Вы не можете получить данные Докуметов других Пользователей!")
            if visible is not None:
                if visible is False:
                    raise HTTPException(status_code=status.HTTP_406_NOT_ACCEPTABLE, detail="Вы не можете просмотреть информацию о скрытых Файлах!")
            if directory_uuid:
                if await FileStoreQueryAndStatementManager.check_access(  # FIXME
                    session=session,
                    
                    requester_user_uuid=requester_user_uuid,
                    requester_user_privilege=requester_user_privilege,
                    directory_uuid=directory_uuid,
                ) is None:
                    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="У Вас нет доступа к Директории!")
            if file_uuids:
                for file_uuid in file_uuids:
                    if await FileStoreQueryAndStatementManager.check_access(
                        session=session,
                        
                        requester_user_uuid=requester_user_uuid,
                        requester_user_privilege=requester_user_privilege,
                        file_uuid=file_uuid,
                    ) is None:
                        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f'У Вас нет доступа к Файлу с UUID - "{file_uuid}"!')
        
        result = {
            "data": {},
            "count": 0,
        }
        
        doc_info_dct: Dict[str, List[Optional[Document]]|Optional[int]] = await FileStoreQueryAndStatementManager.get_doc_info(
            session=session,
            
            owner_user_uuid=owner_user_uuid,
            uploader_user_uuid=uploader_user_uuid,
            directory_uuid=directory_uuid,
            file_uuids=file_uuids,
            visible=visible,
            
            page=page,
            page_size=page_size,
            
            filter=filter,
            order=order,
        )
        
        for doc_info in doc_info_dct["data"]:
            result["count"] += 1
            result["data"][doc_info.id] = {
                "uuid": doc_info.uuid,
                "name": doc_info.name,
                "extansion": doc_info.extansion,
                "type": doc_info.type,
                "directory_id": doc_info.directory_id,
                "directory_uuid": doc_info.directory_uuid,
                "path": doc_info.path,
                "owner_user_id": doc_info.owner_user_id,
                "owner_user_uuid": doc_info.owner_user_uuid,
                "uploader_user_id": doc_info.uploader_user_id,
                "uploader_user_uuid": doc_info.uploader_user_uuid,
                "visible": doc_info.visible,
                "is_deleted": doc_info.is_deleted,
                "deleted_at": convert_tz(doc_info.deleted_at.strftime("%d.%m.%Y %H:%M:%S UTC"), tz_city=tz) if doc_info.deleted_at else None,
                "created_at": convert_tz(doc_info.created_at.strftime("%d.%m.%Y %H:%M:%S UTC"), tz_city=tz) if doc_info.created_at else None,
            }
            if requester_user_privilege == PRIVILEGE_MAPPING["Admin"]:
                result["data"][doc_info.id]["visibility_off_time"] = convert_tz(doc_info.visibility_off_time.strftime("%d.%m.%Y %H:%M:%S UTC"), tz_city=tz) if doc_info.visibility_off_time else None
                result["data"][doc_info.id]["visibility_off_user_id"] = doc_info.visibility_off_user_id
                result["data"][doc_info.id]["visibility_off_user_uuid"] = doc_info.visibility_off_user_uuid
                
                result["data"][doc_info.id]["deleted_at"] = convert_tz(doc_info.deleted_at.strftime("%d.%m.%Y %H:%M:%S UTC"), tz_city=tz) if doc_info.deleted_at else None
                result["data"][doc_info.id]["deleters_user_id"] = doc_info.deleters_user_id
                result["data"][doc_info.id]["deleters_user_uuid"] = doc_info.deleters_user_uuid
        result.update(
            {
                "total_records": doc_info_dct["total_records"],
                "total_pages": doc_info_dct["total_pages"],
            }
        )
        return result
    
    @staticmethod
    async def get_doc_info_from_fs(
        doc_path: str,
    ) -> Dict[str, str|int]:
        data: Dict[str, str|int] = await SignalConnector.get_object_info_s3(
            path=doc_path if not doc_path.endswith("/") else doc_path[:-1]
        )
        
        return data
    # _____________________________________________________________________________________________________
    
    
    # _____________________________________________________________________________________________________
    @staticmethod
    async def download(
        session: AsyncSession,
        
        requester_user_uuid: str, requester_user_privilege: int,
        file_uuid: str,
    ) -> StreamingResponse:
        doc_info_dct: Dict[str, List[Optional[Document]]|Optional[int]] = await FileStoreQueryAndStatementManager.get_doc_info(
            session=session,
            
            file_uuids=[file_uuid],
        )
        if doc_info_dct["data"] and len(doc_info_dct["data"]) < 2:
            document = doc_info_dct["data"][0]
            if requester_user_privilege != PRIVILEGE_MAPPING["Admin"]:  # Проверка если Пользователь не Админ
                if document.owner_user_uuid != requester_user_uuid:
                    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Вы не можете скачать Документ другого Пользователя!")
                if document.visible is False:
                    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Вы не можете скачать скрытый Документ!")
            
            if document.is_deleted is True:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Вы не можете скачать удаленный Документ!")
            
            data: StreamingResponse = await SignalConnector.download_s3(
                path=document.path,
            )
            
            return data
        
        else:
            if not doc_info_dct["data"]:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f'Файл с UUID - "{file_uuid}" не найден!')
            else:
                raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f'Целостность данных нарушена, существует более 1 записи о файле с UUID - "{file_uuid}"!')
    
    @classmethod
    async def upload(
        cls,
        
        session: AsyncSession,
        
        file_object: UploadFile,
        directory_uuid: str,
        requester_user_uuid: str, requester_user_privilege: int,
        
        owner_user_uuid: Optional[str]=None,
        new_file_uuid: Optional[str]=None,
        file_type: Optional[str]=None,
    ) -> str:
        if not directory_uuid:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Нужно указать uuid директории для загрузки!")
        
        if file_object.size >= 20 * 1024 * 1024:
            raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="Файл должен быть менее 20 мб!")
        
        if requester_user_privilege != PRIVILEGE_MAPPING["Admin"]:  # Проверка если Пользователь не Админ
            if owner_user_uuid:
                if owner_user_uuid != requester_user_uuid:
                    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Вы не можете загружать Файл для другого Пользователя!")
        
        dir_data: Dict[str, Any] = await FileStoreService.get_dir_info_from_db(
            session=session,
            
            requester_user_uuid=requester_user_uuid, requester_user_privilege=requester_user_privilege,
            owner_user_uuid=None if requester_user_privilege == PRIVILEGE_MAPPING["Admin"] else owner_user_uuid,
            directory_uuids=[directory_uuid],
        )
        if dir_data["count"] == 1:  # Если родительская директория (для записи) найдена
            if new_file_uuid is None:
                new_file_uuid_coro = await SignalConnector.generate_identifiers(target="Документ", count=1)
                new_file_uuid = new_file_uuid_coro[0]
            else:
                if await SignalConnector.check_identifier(
                    target="Документ",
                    uuid=new_file_uuid,
                ) is not False:  # Если uuid занят
                    raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Документ с данным UUID уже используется!")
            
            if len(file_object.filename.split(".")) > 1:
                file_name = ".".join(file_object.filename.split(".")[:-1])
                extension = file_object.filename.split(".")[-1]
            else:
                file_name = file_object.filename
                extension = ""
            correct_name = urllib.parse.unquote(file_name)
            correct_name_with_extansion = correct_name + "." + extension
            new_file_path = posixpath.normpath(posixpath.join(dir_data["data"][list(dir_data["data"])[0]]["path"], correct_name_with_extansion))
            new_file_path_without_filename = posixpath.normpath(posixpath.join(dir_data["data"][list(dir_data["data"])[0]]["path"]))
            
            original_path = new_file_path
            counter = 1
            while True:
                try:
                    object_info: Dict[str, str|int] = await SignalConnector.get_object_info_s3(path=new_file_path)
                    if object_info.get("size") is None:
                        break
                    else:
                        raise
                except:  # noqa: E722
                    # Разбираем путь
                    directory = os.path.dirname(original_path)
                    filename = os.path.basename(original_path)
                    name, ext = os.path.splitext(filename)
                    
                    # Формируем новое имя с номером
                    correct_name_with_extansion = f"{name} ({counter}){ext}"
                    new_file_path = posixpath.join(directory, correct_name_with_extansion)
                    counter += 1
            
            await SignalConnector.upload_s3(
                path=new_file_path_without_filename,  # путь должен быть без префикса filestore/ (!)
                filenames=[correct_name_with_extansion],
                files=[file_object],
            )
            
            await FileStoreQueryAndStatementManager.create_doc_info(
                session=session,
                
                doc_info_data={
                    "uuid": new_file_uuid,
                    "name": correct_name_with_extansion,
                    "extansion": Path(correct_name_with_extansion).suffix,
                    "size": file_object.size,
                    "type": file_type,
                    "directory_uuid": directory_uuid,
                    "path": new_file_path,
                    "owner_user_uuid": owner_user_uuid,
                    "uploader_user_uuid": requester_user_uuid,
                }
            )
        else:  # Если родительская директория (для записи) не найдена или нарушена целостность данных и записей о данной папке в БД более 1
            if dir_data["count"] == 0:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f'Директория "{directory_uuid}" либо отсутствует, либо у Вас недостаточно прав!')
            else:
                raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f'Целостность данных нарушена, существует более 1 записи о Директории с UUID - "{directory_uuid}"!')
        
        return new_file_uuid
    # _____________________________________________________________________________________________________
    
    @staticmethod
    async def create_directory(
        session: AsyncSession,
        
        requester_user_uuid: str, requester_user_privilege: int,
        
        owner_s3_login: str,
        owner_user_uuid: Optional[str]=None,
        directory_type: Optional[int]=None,
        new_directory_uuid: Optional[str]=None,
        
        parent_directory_uuid: Optional[str]=None,
    ) -> Dict[str, Any]:
        """Создает директорию и возвращает uuid и id нововой директории"""
        if requester_user_privilege != PRIVILEGE_MAPPING["Admin"]:  # Проверка если Пользователь не Админ
            if directory_type is None:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Вам нужно обязательно указать Тип Директории при создании!")
            if owner_user_uuid:
                if owner_user_uuid != requester_user_uuid:
                    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Вы не можете создать Директорию для другого Пользователя!")
        
        if parent_directory_uuid is not None:
            parent_dir_data: Dict[str, Any] = await FileStoreService.get_dir_info_from_db(
                session=session,
                
                requester_user_uuid=requester_user_uuid, requester_user_privilege=requester_user_privilege,
                owner_user_uuid=None if requester_user_privilege == PRIVILEGE_MAPPING["Admin"] else owner_user_uuid,
                directory_uuids=[parent_directory_uuid],
            )
            
            if parent_dir_data["count"] == 1:  # Если родительская директория (для записи) найдена
                if new_directory_uuid is None:
                    new_directory_uuid_coro = await SignalConnector.generate_identifiers(target="Директория", count=1)
                    new_directory_uuid = new_directory_uuid_coro[0]
                else:
                    if await SignalConnector.check_identifier(
                        target="Директория",
                        uuid=new_directory_uuid,
                    ) is not False:  # Если uuid занят
                        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Директория с данным UUID уже используется!")
                new_directory_path = posixpath.normpath(posixpath.join(parent_dir_data["data"][list(parent_dir_data["data"])[0]]["path"], new_directory_uuid))
                
                dir_id: int = await FileStoreQueryAndStatementManager.create_dir_info(
                    session=session,
                    
                    dir_info_data={
                        "uuid": new_directory_uuid,
                        "parent_directory_uuid": parent_directory_uuid,
                        "owner_user_uuid": owner_user_uuid,
                        "uploader_user_uuid": requester_user_uuid,
                        "path": new_directory_path,
                        "type": directory_type,
                    }
                )
            
            else:  # Если родительская директория (для записи) не найдена или нарушена целостность данных и записей о данной папке в БД более 1
                if parent_dir_data["count"] == 0:
                    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f'Родительская директория "{parent_directory_uuid}" либо отсутствует, либо у Вас недостаточно прав!')
                else:
                    raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f'Целостность данных нарушена, существует более 1 записи о папке с UUID - "{parent_directory_uuid}"!')
        
        else:
            if new_directory_uuid is None:
                new_directory_uuid_coro = await SignalConnector.generate_identifiers(target="Директория", count=1)
                new_directory_uuid = new_directory_uuid_coro[0]
            else:
                if await SignalConnector.check_identifier(
                    target="Директория",
                    uuid=new_directory_uuid,
                ) is not False:  # Если uuid занят
                    raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Директория с данным UUID уже используется!")
            
            new_directory_path = posixpath.normpath(posixpath.join(owner_s3_login, new_directory_uuid))
            
            dir_id: int = await FileStoreQueryAndStatementManager.create_dir_info(
                session=session,
                
                dir_info_data={
                    "uuid": new_directory_uuid,
                    "parent_directory_uuid": parent_directory_uuid,
                    "owner_user_uuid": owner_user_uuid,
                    "uploader_user_uuid": requester_user_uuid,
                    "path": new_directory_path,
                    "type": directory_type,
                }
            )
        
        return {
            "id": dir_id,
            "uuid": new_directory_uuid,
            "parent_uuid": parent_directory_uuid,
        }
    
    @staticmethod
    async def change_visibility(
        session: AsyncSession,
        
        requester_user_id: int, requester_user_uuid: str, requester_user_privilege: int,
        
        visibility_status: bool,
        uuids: List[Optional[str]],
        is_document: bool,
    ) -> None:
        if requester_user_privilege != PRIVILEGE_MAPPING["Admin"]:
            if visibility_status is True:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Вы не можете изменить статус видимости Документа на видимый!")
        if not uuids:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Для изменения видимости Файлов/Директорий нужно указать хотя бы один uuid!")
        
        if is_document:
            object_info = await FileStoreService.get_doc_info_from_db(
                session=session,
                
                requester_user_uuid=requester_user_uuid,
                requester_user_privilege=requester_user_privilege,
                file_uuids=uuids,
                owner_user_uuid=requester_user_uuid if requester_user_privilege != PRIVILEGE_MAPPING["Admin"] else None,
            )
        else:
            object_info = await FileStoreService.get_dir_info_from_db(
                session=session,
                
                requester_user_uuid=requester_user_uuid,
                requester_user_privilege=requester_user_privilege,
                directory_uuids=uuids,
                owner_user_uuid=requester_user_uuid if requester_user_privilege != PRIVILEGE_MAPPING["Admin"] else None,
            )
        
        if object_info["count"] < 1:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f'{"Файл/ы" if is_document else "Директория/ии"} c UUID "{", ".join(uuids)}" либо отсутствует/ют, либо у Вас недостаточно прав!')
        if object_info["data"][list(object_info["data"])[0]]["is_deleted"] is True:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"{'Документ удален' if is_document else 'Директория удалена'}!")
        if requester_user_privilege != PRIVILEGE_MAPPING["Admin"]:
            if object_info["data"][list(object_info["data"])[0]]["owner_user_uuid"] != requester_user_uuid:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"Вы не можете изменить видимость не своe{"го/их Файла/ов" if is_document else "ей/их Директории/ий"}!")
        
        visible = object_info["data"][list(object_info["data"])[0]]["visible"]
        if visible == visibility_status:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f'Видимость {"Файла/ов" if is_document else "Директории/ий"} c uuid "{", ".join(uuids)}" уже в статусе {visibility_status}!')
        else:
            await FileStoreQueryAndStatementManager.change_visibility(
                session=session,
                
                requester_user_id=requester_user_id, requester_user_uuid=requester_user_uuid,
                visibility_status=visibility_status,
                uuids=uuids,
                is_document=is_document,
            )
    
    @staticmethod
    async def delete_doc_or_dir(
        session: AsyncSession,
        
        requester_user_id: int, requester_user_uuid: str, requester_user_privilege: int,
        
        is_document: bool,
        
        uuid: str,
        for_user: bool = False,
    ) -> None:
        if for_user is False:
            if requester_user_privilege != PRIVILEGE_MAPPING["Admin"]:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Не достаточно прав!")
        
        if is_document:
            object_info = await FileStoreService.get_doc_info_from_db(
                session=session,
                
                requester_user_uuid=requester_user_uuid,
                requester_user_privilege=requester_user_privilege,
                file_uuids=[uuid],
                owner_user_uuid=requester_user_uuid if requester_user_privilege != PRIVILEGE_MAPPING["Admin"] else None,
            )
        else:
            object_info = await FileStoreService.get_dir_info_from_db(
                session=session,
                
                requester_user_uuid=requester_user_uuid,
                requester_user_privilege=requester_user_privilege,
                directory_uuids=[uuid],
                owner_user_uuid=requester_user_uuid if requester_user_privilege != PRIVILEGE_MAPPING["Admin"] else None,
            )
        
        if object_info["count"] == 0:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f'{"Файл" if is_document else "Директория"} c UUID "{uuid}" либо отсутствует, либо у Вас недостаточно прав!')
        if object_info["count"] > 1:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f'Целостность данных нарушена, существует более 1 записи о {"Файле" if is_document else "Директории"} с UUID - "{uuid}"!')
        
        is_deleted = object_info["data"][list(object_info["data"])[0]]["is_deleted"]
        if is_deleted:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f'{"Файл" if is_document else "Директория"} c UUID "{uuid}" уже удален{"" if is_document else "а"}!')
        else:
            path: str = object_info["data"][list(object_info["data"])[0]]["path"]
            try:
                await SignalConnector.delete_s3(
                    path=path.replace("filestore/", ""),
                )
            except: pass  # noqa: E701, E722
            
            await FileStoreQueryAndStatementManager.change_deletion_status(
                session=session,
                
                requester_user_id=requester_user_id, requester_user_uuid=requester_user_uuid,
                uuid=uuid,
                is_document=is_document,
            )
