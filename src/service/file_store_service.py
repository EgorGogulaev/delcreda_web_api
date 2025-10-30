import os
import magic
import olefile
import zipfile
import tempfile
import posixpath
from pathlib import Path
from typing import Any, Dict, List, Optional
import urllib.parse

from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, UploadFile
import pyclamd

from config import SFTP_BASE_PATH
from connection_module import AsyncSFTPClient, SignalConnector
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
            assert page and page_size and page > 0 and page_size > 0, "Не корректное разделение на страницы, вывода данных!"
        if requester_user_privilege != PRIVILEGE_MAPPING["Admin"]:  # Проверка если Пользователь не Админ
            if owner_user_uuid:
                assert owner_user_uuid == requester_user_uuid, "Вы не можете просмотреть Директорию другого Пользователя!"
            else:
                owner_user_uuid = requester_user_uuid
            if uploader_user_uuid:
                assert uploader_user_uuid == requester_user_uuid, "Вы не можете просмотреть Директорию другого Пользователя!"
            if visible is not None:
                assert visible, "Вы не можете просмотреть информацию о скрытой Директории!"
        
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
    ) -> Dict[str, Any]:
        async with AsyncSFTPClient.get_client() as storage_client:
            data = await storage_client.get_directory_info(dir_path=dir_path)
        
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
            assert page and page_size and page > 0 and page_size > 0, "Не корректное разделение на страницы, вывода данных!"
        
        if requester_user_privilege != PRIVILEGE_MAPPING["Admin"]:  # Проверка если Пользователь не Админ
            if owner_user_uuid:
                assert owner_user_uuid == requester_user_uuid, "Вы не можете получить данные Докуметов других Пользователей!"
            else:
                owner_user_uuid = requester_user_uuid
            if uploader_user_uuid:
                assert uploader_user_uuid == requester_user_uuid, "Вы не можете получить данные Докуметов других Пользователей!"
            if visible is not None:
                assert visible, "Вы не можете просмотреть информацию о скрытых Файлах!"
            if directory_uuid:
                assert await FileStoreQueryAndStatementManager.check_access(
                    session=session,
                    
                    requester_user_uuid=requester_user_uuid,
                    requester_user_privilege=requester_user_privilege,
                    directory_uuid=directory_uuid,
                ), "У Вас нет доступа к Директории!"
            if file_uuids:
                for file_uuid in file_uuids:
                    assert await FileStoreQueryAndStatementManager.check_access(
                        session=session,
                        
                        requester_user_uuid=requester_user_uuid,
                        requester_user_privilege=requester_user_privilege,
                        file_uuid=file_uuid,
                    ), f'У Вас нет доступа к Файлу с uuid - "{file_uuid}"!'
        
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
    ) -> Dict[str, Any]:
        async with AsyncSFTPClient.get_client() as storage_client:
            data = await storage_client.get_file_info(file_path=doc_path)
        
        return data
    # _____________________________________________________________________________________________________
    
    
    # _____________________________________________________________________________________________________
    @staticmethod
    async def download(
        session: AsyncSession,
        
        requester_user_uuid: str, requester_user_privilege: int,
        file_uuid: str,
    ) -> Dict[str, Any]:
        doc_info_dct: Dict[str, List[Optional[Document]]|Optional[int]] = await FileStoreQueryAndStatementManager.get_doc_info(
            session=session,
            
            file_uuids=[file_uuid],
        )
        if doc_info_dct["data"] and len(doc_info_dct["data"]) < 2:
            document = doc_info_dct["data"][0]
            if requester_user_privilege != PRIVILEGE_MAPPING["Admin"]:  # Проверка если Пользователь не Админ
                assert document.owner_user_uuid == requester_user_uuid, "Вы не можете скачать Документ другого Пользователя!"
                assert document.visible is True, "Вы не можете скачать скрытый Документ!"
            assert not document.is_deleted, "Вы не можете скачать удаленный Документ!"
            
            async with AsyncSFTPClient.get_client() as storage_client:
                data: bytes = await storage_client.read_file(path=document.path)
            
            return {
                "data": data,
                "filename": document.name,
            }
        
        else:
            raise AssertionError(f'Файл с uuid - "{file_uuid}" не найден!' if not doc_info_dct["data"] else f'Целостность данных нарушена, существует более 1 записи о файле с uuid - "{file_uuid}"')
    
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
        assert directory_uuid, "Нужно указать uuid директории для загрузки!"
        assert file_object.size <= 20 * 1024 * 1024, "Файл не должен превышать 20 мб!"
        if requester_user_privilege != PRIVILEGE_MAPPING["Admin"]:  # Проверка если Пользователь не Админ
            if owner_user_uuid:
                assert owner_user_uuid == requester_user_uuid, "Не будучи Админом, Вы не можете загружать Файл для другого Пользователя!"
        
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
                    raise AssertionError("Директория с данным uuid уже используется!")
            
            await cls.__validate_file(file=file_object)
            if len(file_object.filename.split(".")) > 1:
                file_name = file_object.filename.split(".")[0]
                extension = file_object.filename.split(".")[1]
            else:
                file_name = file_object.filename
                extension = ""
            correct_name = urllib.parse.unquote(file_name)
            correct_name_with_extansion = correct_name + "." + extension
            new_file_path = posixpath.normpath(posixpath.join(dir_data["data"][list(dir_data["data"])[0]]["path"], correct_name_with_extansion))
            
            async with AsyncSFTPClient.get_client() as storage_client:
                original_path = new_file_path
                counter = 1
                while True:
                    result = await storage_client.get_file_info(file_path=new_file_path)
                    if not result["is_exist"]:
                        break
                        
                    # Разбираем путь
                    directory = os.path.dirname(original_path)
                    filename = os.path.basename(original_path)
                    name, ext = os.path.splitext(filename)
                    
                    # Формируем новое имя с номером
                    correct_name_with_extansion = f"{name} ({counter}){ext}"
                    new_file_path = posixpath.join(directory, correct_name_with_extansion)
                    counter += 1
                
                await storage_client.write_file(file_path=new_file_path, file_object=file_object)
            
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
            raise AssertionError(f'Директория "{directory_uuid}" либо отсутствует, либо у Вас недостаточно прав!' if dir_data["count"] == 0 else f'Целостность данных нарушена, существует более 1 записи о папке с uuid - "{directory_uuid}"!')
        
        return new_file_uuid
    # _____________________________________________________________________________________________________
    
    @staticmethod
    async def create_directory(
        session: AsyncSession,
        
        requester_user_uuid: str, requester_user_privilege: int,
        
        owner_user_uuid: Optional[str]=None,
        directory_type: Optional[int]=None,
        new_directory_uuid: Optional[str]=None,
        
        parent_directory_uuid: Optional[str]=None,
    ) -> Dict[str, Any]:
        """Создает директорию и возвращает uuid и id нововой директории"""
        if requester_user_privilege != PRIVILEGE_MAPPING["Admin"]:  # Проверка если Пользователь не Админ
            
            assert directory_type, "Вам обязательно нужно указать Тип Директории при создании!"
            if owner_user_uuid:
                assert owner_user_uuid == requester_user_uuid, "Вы не можете создать Директорию для другого Пользователя!"
        
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
                        raise AssertionError("Директория с данным uuid уже используется!")
                new_directory_path = posixpath.normpath(posixpath.join(parent_dir_data["data"][list(parent_dir_data["data"])[0]]["path"], new_directory_uuid))
                async with AsyncSFTPClient.get_client() as storage_client:
                    await storage_client.create_directory(new_directory_path)
                
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
                raise AssertionError(f'Родительская директория "{parent_directory_uuid}" либо отсутствует, либо у Вас недостаточно прав!' if parent_dir_data["count"] == 0 else f'Целостность данных нарушена, существует более 1 записи о папке с uuid - "{parent_directory_uuid}"!')
        
        else:
            if new_directory_uuid is None:
                new_directory_uuid_coro = await SignalConnector.generate_identifiers(target="Директория", count=1)
                new_directory_uuid = new_directory_uuid_coro[0]
            else:
                if await SignalConnector.check_identifier(
                    target="Директория",
                    uuid=new_directory_uuid,
                ) is not False:  # Если uuid занят
                    raise AssertionError("Директория с данным uuid уже используется!")
            new_directory_path = posixpath.normpath(posixpath.join(SFTP_BASE_PATH, new_directory_uuid))
            async with AsyncSFTPClient.get_client() as storage_client:
                await storage_client.create_directory(new_directory_path)
            
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
                raise AssertionError("Вы не можете изменить статус видимости Документа на видимый!")
        assert uuids, "Для изменения видимости Файлов/Директорий нужно указать хотя бы один uuid!"
        
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
        
        assert object_info["count"] >= 1, f'{"Файл/ы" if is_document else "Директория/ии"} c uuid "{", ".join(uuids)}" либо отсутствует/ют, либо у Вас недостаточно прав!'
        assert not object_info["data"][list(object_info["data"])[0]]["is_deleted"], f"{'Документ удален' if is_document else 'Директория удалена'}!"
        if requester_user_privilege != PRIVILEGE_MAPPING["Admin"]:
            assert object_info["data"][list(object_info["data"])[0]]["owner_user_uuid"] == requester_user_uuid, f"Вы не можете изменить видимость не своe{"го/их Файла/ов" if is_document else "ей/их Директории/ий"}!"
        
        visible = object_info["data"][list(object_info["data"])[0]]["visible"]
        if visible == visibility_status:
            raise AssertionError(f'Видимость {"Файла/ов" if is_document else "Директории/ий"} c uuid "{", ".join(uuids)}" уже в статусе {visibility_status}!')
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
            assert requester_user_privilege == PRIVILEGE_MAPPING["Admin"], "Не достаточно прав!"
        
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
        
        assert object_info["count"] == 1, f'{"Файл" if is_document else "Директория"} c uuid "{uuid}" либо отсутствует, либо у Вас недостаточно прав!' if object_info["count"] == 0 else f'Целостность данных нарушена, существует более 1 записи о {"Файле" if is_document else "Директории"} с uuid - "{uuid}"!'
        is_deleted = object_info["data"][list(object_info["data"])[0]]["is_deleted"]
        if is_deleted:
            raise AssertionError(f'{"Файл" if is_document else "Директория"} c uuid "{uuid}" уже удален{"" if is_document else "а"}!')
        else:
            path = object_info["data"][list(object_info["data"])[0]]["path"]
            async with AsyncSFTPClient.get_client() as storage_client:
                await storage_client.remove(path=path, is_document=is_document)
            
            await FileStoreQueryAndStatementManager.change_deletion_status(
                session=session,
                
                requester_user_id=requester_user_id, requester_user_uuid=requester_user_uuid,
                uuid=uuid,
                is_document=is_document,
            )
    
    @staticmethod
    def __check_office_file(file_path: str) -> None:
        if file_path.endswith(('.docx', '.xlsx')):
            with zipfile.ZipFile(file_path, 'r') as z:
                if 'word/vbaProject.bin' in z.namelist():
                    raise HTTPException(status_code=400, detail="Макросы обнаружены в файле Office!")
        elif file_path.endswith(('.doc', '.xls')):
            if olefile.isOleFile(file_path):
                ole = olefile.OleFileIO(file_path)
                if ole.exists('Macros'):
                    raise HTTPException(status_code=400, detail="Макросы обнаружены в файле Office!")
    
    @classmethod
    async def __validate_file(
        cls,
        file: UploadFile
    ) -> None:
        # 1. Проверка MIME-типа
        ALLOWED_MIME_TYPES = {
                'application/pdf',
                'image/jpeg',
                'image/png',
                'application/msword',
                'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                'application/vnd.ms-excel',
                'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        }
        if file.content_type not in ALLOWED_MIME_TYPES:
            raise HTTPException(status_code=415, detail="Неподдерживаемый тип файла")
        
        # 2. Сохранение во временный файл
        with tempfile.NamedTemporaryFile(delete=False) as temp:
            content = await file.read()
            temp.write(content)
            temp_path = temp.name
            
            try:
                # 3. Проверка реального типа (magic)
                real_file_type = magic.from_file(temp_path, mime=True)
                if real_file_type not in ALLOWED_MIME_TYPES:
                    raise HTTPException(status_code=415, detail="Неподдерживаемый тип файла!")
                
                # 4. Проверка на PHP/JS
                if b'<?php' in content or b'<script' in content.lower():
                    raise HTTPException(status_code=400, detail="Потенциально вредоносный контент!")
                
                # 5. Проверка антивирусом (опционально)
                try:
                    cd = pyclamd.ClamdUnixSocket()
                    scan_result = cd.scan_file(temp_path)
                    if scan_result is not None:
                        raise HTTPException(status_code=400, detail="Обнаружен вредоносный файл!")
                except pyclamd.ConnectionError: ...
                
                # 6. Проверка макросов в Office (если нужно)
                if file.filename.endswith(('.docx', '.xlsx', '.doc', '.xls')):
                    cls.__check_office_file(temp_path)
            except: ...  # noqa: E722
