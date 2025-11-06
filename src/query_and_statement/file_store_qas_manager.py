import datetime
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import and_, func, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.legal_entity.legal_entity_models import LegalEntity
from src.models.application.application_models import Application
from src.schemas.file_store_schema import FiltersUserDirsInfo, FiltersUserFilesInfo, OrdersUserDirsInfo, OrdersUserFilesInfo
from src.models.file_store_models import Document, Directory
from src.query_and_statement.user_qas_manager import UserQueryAndStatementManager
from src.utils.reference_mapping_data.user.mapping import PRIVILEGE_MAPPING
from src.utils.reference_mapping_data.file_store.mapping import FILE_STORE_SUBJECT_MAPPING



class FileStoreQueryAndStatementManager:
    @staticmethod
    async def get_subject_info_by_directory_uuid(
        session: AsyncSession,
        
        directory_uuid: str,
    ) -> Tuple[int, str]:
        assert directory_uuid, "Для получения информации о субъекте по директории должен быть указан uuid директории!"
        
        query_legal_entity = (
            select(LegalEntity.uuid)
            .filter(LegalEntity.directory_uuid == directory_uuid)
        )
        response_legal_entity = await session.execute(query_legal_entity)
        subject_uuid = response_legal_entity.scalar_one_or_none()
        
        if subject_uuid:
            return FILE_STORE_SUBJECT_MAPPING["ЮЛ"], subject_uuid
        
        query_application = (
            select(Application.uuid)
            .filter(Application.directory_uuid == directory_uuid)
        )
        response_application = await session.execute(query_application)
        subject_uuid = response_application.scalar_one_or_none()
        
        if subject_uuid:
            return FILE_STORE_SUBJECT_MAPPING["Заявка"], subject_uuid
        
        raise AssertionError("По данному UUID-директории не найдены субъекты!")
    
    @staticmethod
    async def check_access(
        session: AsyncSession,
        
        requester_user_uuid: str,
        requester_user_privilege: str,
        
        directory_uuid: Optional[str] = None,
        file_uuid: Optional[str] = None,
    ) -> Optional[int]:
        # FIXME блок проверок должен быть вынесен в service
        assert any([file_uuid, directory_uuid]), "Для проверки должен быть указан uuid файла или директории!"
        assert not all([file_uuid, directory_uuid]), "Для проверки должен быть указан uuid файла или директории (что-то одно)!"
        
        table = Document if file_uuid else Directory
        
        _filters = []
        if file_uuid:
            _filters.append(table.uuid == file_uuid)
        else:
            _filters.append(table.uuid == directory_uuid)
        
        if requester_user_privilege != PRIVILEGE_MAPPING["Admin"]:
            _filters.append(table.owner_user_uuid == requester_user_uuid)
        
        query = (
            select(table.id)
            .filter(
                and_(
                    *_filters
                )
                
            )
        )
        response = await session.execute(query)
        result = response.scalar()
        return result
    
    @staticmethod
    async def get_dir_or_doc_id_by_uuid(
        session: AsyncSession,
        
        uuid: str,
        is_document: bool,
    ) -> Optional[int]:
        query = (
            select(Document.id if is_document else Directory.id)
            .filter((Document.uuid if is_document else Directory.uuid) == uuid)
        )
        
        response = await session.execute(query)
        result = response.scalar()
        return result
    
    # _____________________________________________________________________________________________________
    @staticmethod
    async def create_dir_info(
        session: AsyncSession,
        
        dir_info_data: Dict[str, Any]
    ) -> int:
        """Создает запись в БД о директории и возвращает её id"""
        owner_user_id = await UserQueryAndStatementManager.get_user_id_by_uuid(session=session, uuid=dir_info_data["owner_user_uuid"]) if dir_info_data.get("owner_user_uuid") else None
        uploader_user_id = await UserQueryAndStatementManager.get_user_id_by_uuid(session=session, uuid=dir_info_data["uploader_user_uuid"]) if dir_info_data.get("uploader_user_uuid") else None
        parent_dir_id = await FileStoreQueryAndStatementManager.get_dir_or_doc_id_by_uuid(session=session, uuid=dir_info_data["parent_directory_uuid"], is_document=False) if dir_info_data.get("parent_directory_uuid") else None
        
        
        stmt = (
            insert(Directory)
            .values(
                uuid=dir_info_data.get("uuid"),
                parent=parent_dir_id,
                path=dir_info_data.get("path"),
                type=dir_info_data.get("type"),
                owner_user_id=owner_user_id,
                owner_user_uuid=dir_info_data.get("owner_user_uuid"),
                uploader_user_id=uploader_user_id,
                uploader_user_uuid=dir_info_data.get("uploader_user_uuid"),
                visible=True,
            )
            .returning(Directory.id)
        )
        dir_id = await session.execute(stmt)
        await session.commit()
        
        return dir_id.scalar()
    
    @staticmethod
    async def get_dir_info(
        session: AsyncSession,
        
        owner_user_uuid: Optional[str] = None,
        uploader_user_uuid: Optional[str] = None,
        directory_uuids: Optional[List[str]] = None,
        visible: Optional[bool] = None,
        
        page: Optional[int] = None,
        page_size: Optional[int] = None,
        
        filter: Optional[FiltersUserDirsInfo] = None,
        order: Optional[OrdersUserDirsInfo] = None,
    ) -> Dict[str, List[Optional[Directory]]|Optional[int]]:
        _filters = []
        if owner_user_uuid:
            _filters.append(Directory.owner_user_uuid == owner_user_uuid)
        if uploader_user_uuid:
            _filters.append(Directory.uploader_user_uuid == uploader_user_uuid)
        if directory_uuids:
            _filters.append(Directory.uuid.in_(directory_uuids))
        if visible is not None:
            _filters.append(Directory.visible == visible)
        
        if filter is not None and filter.filters:
            for filter_item in filter.filters:
                column = getattr(Directory, filter_item.field)
                if filter_item.operator == "eq":
                    cond = column == filter_item.value
                elif filter_item.operator == "ne":
                    cond = column != filter_item.value
                elif filter_item.operator == "gt":
                    cond = column > filter_item.value
                elif filter_item.operator == "lt":
                    cond = column < filter_item.value
                elif filter_item.operator == "ge":
                    cond = column >= filter_item.value
                elif filter_item.operator == "le":
                    cond = column <= filter_item.value
                elif filter_item.operator == "like":
                    value = f"%{filter_item.value}%"
                    cond = column.ilike(value)
                elif filter_item.operator == "in":
                    if isinstance(filter_item.value, str):
                        values = [v.strip() for v in filter_item.value.split(",")]
                    else:
                        values = filter_item.value
                    cond = column.in_(values)
                else:
                    continue
                
                _filters.append(cond)
        
        # ===== сортировка =====
        _order_clauses = []
        if order is not None and order.orders:
            for order_item in order.orders:
                # Получаем атрибут модели для сортировки
                column = getattr(Directory, order_item.field)
                
                # Добавляем условие сортировки в зависимости от направления
                if order_item.direction == "asc":
                    _order_clauses.append(column.asc().nulls_last())
                else:
                    _order_clauses.append(column.desc().nulls_last())
        
        if not _order_clauses:
            _order_clauses.append(Directory.id.asc())
        # ===== КОНЕЦ блока сортировки =====
        
        query = (
            select(Directory)
            .filter(and_(*_filters))
            .order_by(*_order_clauses)
        )
        
        total_records = None
        total_pages = None
        
        if page is None or (page is not None and page < 1):
            page = 1
        if page_size is None or (page is not None and page_size < 1):
            page_size = 50
        
        query = query.limit(page_size).offset((page - 1) * page_size)
        count_query = select(func.count()).select_from(Directory).filter(and_(*_filters))
        
        total_records = (await session.execute(count_query)).scalar()
        total_pages = (total_records + page_size - 1) // page_size if total_records else 0
        
        response = await session.execute(query)
        data = [item[0] for item in response.fetchall()]
        return {
            "data": data,
            "total_records": total_records,
            "total_pages": total_pages,
        }
    
    # _____________________________________________________________________________________________________
    
    # _____________________________________________________________________________________________________
    @staticmethod
    async def create_doc_info(
        session: AsyncSession,
        
        doc_info_data: Dict[str, Any]
    ) -> None:
        owner_user_id = await UserQueryAndStatementManager.get_user_id_by_uuid(session=session, uuid=doc_info_data["owner_user_uuid"]) if doc_info_data.get("owner_user_uuid") else None
        uploader_user_id = await UserQueryAndStatementManager.get_user_id_by_uuid(session=session, uuid=doc_info_data["uploader_user_uuid"]) if doc_info_data.get("uploader_user_uuid") else None
        dir_id = await FileStoreQueryAndStatementManager.get_dir_or_doc_id_by_uuid(session=session, uuid=doc_info_data["directory_uuid"], is_document=False) if doc_info_data.get("directory_uuid") else None
        
        stmt = (
            insert(Document)
            .values(
                uuid=doc_info_data.get("uuid"),
                name=doc_info_data.get("name"),
                extansion=doc_info_data.get("extansion"),
                size=doc_info_data.get("size"),
                type=doc_info_data.get("type"),
                directory_id=dir_id,
                directory_uuid=doc_info_data["directory_uuid"],
                path=doc_info_data.get("path"),
                owner_user_id=owner_user_id,
                owner_user_uuid=doc_info_data.get("owner_user_uuid"),
                uploader_user_id=uploader_user_id,
                uploader_user_uuid=doc_info_data.get("uploader_user_uuid"),
            )
        )
        await session.execute(stmt)
        await session.commit()
    
    @staticmethod
    async def get_doc_info(
        session: AsyncSession,
        
        owner_user_uuid: Optional[str] = None,
        uploader_user_uuid: Optional[str] = None,
        directory_uuid: Optional[str] = None,
        file_uuids: Optional[List[str]] = None,
        visible: Optional[bool] = None,
        
        page: Optional[int] = None,
        page_size: Optional[int] = None,
        
        filter: Optional[FiltersUserFilesInfo] = None,
        order: Optional[OrdersUserFilesInfo] = None,
    ) -> Dict[str, List[Optional[Document]]|Optional[int]]:
        _filters = []
        if owner_user_uuid:
            _filters.append(Document.owner_user_uuid == owner_user_uuid)
        if directory_uuid:
            _filters.append(Document.directory_uuid == directory_uuid)
        if uploader_user_uuid:
            _filters.append(Document.uploader_user_uuid == uploader_user_uuid)
        if file_uuids:
            _filters.append(Document.uuid.in_(file_uuids))
        if visible is not None:
            _filters.append(Document.visible == visible)
        
        if filter is not None and filter.filters:
            for filter_item in filter.filters:
                column = getattr(Document, filter_item.field)
                if filter_item.operator == "eq":
                    cond = column == filter_item.value
                elif filter_item.operator == "ne":
                    cond = column != filter_item.value
                elif filter_item.operator == "gt":
                    cond = column > filter_item.value
                elif filter_item.operator == "lt":
                    cond = column < filter_item.value
                elif filter_item.operator == "ge":
                    cond = column >= filter_item.value
                elif filter_item.operator == "le":
                    cond = column <= filter_item.value
                elif filter_item.operator == "like":
                    value = f"%{filter_item.value}%"
                    cond = column.ilike(value)
                elif filter_item.operator == "in":
                    if isinstance(filter_item.value, str):
                        values = [v.strip() for v in filter_item.value.split(",")]
                    else:
                        values = filter_item.value
                    cond = column.in_(values)
                else:
                    continue
                
                _filters.append(cond)
        
        # ===== сортировка =====
        _order_clauses = []
        if order is not None and order.orders:
            for order_item in order.orders:
                # Получаем атрибут модели для сортировки
                column = getattr(Document, order_item.field)
                
                # Добавляем условие сортировки в зависимости от направления
                if order_item.direction == "asc":
                    _order_clauses.append(column.asc().nulls_last())
                else:
                    _order_clauses.append(column.desc().nulls_last())
        
        if not _order_clauses:
            _order_clauses.append(Document.id.asc())
        # ===== КОНЕЦ блока сортировки =====
        
        query = (
            select(Document)
            .filter(and_(*_filters))
            .order_by(*_order_clauses)
        )
        
        total_records = None
        total_pages = None
        
        if page is None or (page is not None and page < 1):
            page = 1
        if page_size is None or (page is not None and page_size < 1):
            page_size = 50
        
        query = query.limit(page_size).offset((page - 1) * page_size)
        count_query = select(func.count()).select_from(Document).filter(and_(*_filters))
        
        total_records = (await session.execute(count_query)).scalar()
        total_pages = (total_records + page_size - 1) // page_size if total_records else 0
        
        response = await session.execute(query)
        data = [item[0] for item in response.fetchall()]
        return {
            "data": data,
            "total_records": total_records,
            "total_pages": total_pages,
        }
    
    # _____________________________________________________________________________________________________
    
    @staticmethod
    async def change_visibility(
        session: AsyncSession,
        
        requester_user_id: int, requester_user_uuid: str,
        
        visibility_status: bool,
        uuids: List[str],
        is_document: bool,
    ) -> None:
        table = Document if is_document else Directory
        stmt = (
            update(table)
            .filter(
                table.uuid.in_(uuids)
            )
            .values(
                visible=visibility_status,
                visibility_off_time=datetime.datetime.now(tz=datetime.timezone.utc) if visibility_status is False else None,
                visibility_off_user_id=requester_user_id if visibility_status is False else None,
                visibility_off_user_uuid=requester_user_uuid if visibility_status is False else None,
            )
        )
        
        await session.execute(stmt)
        await session.commit()
    
    @staticmethod
    async def change_deletion_status(
        session: AsyncSession,
        
        requester_user_id: int, requester_user_uuid: str,
        
        uuid: str,
        is_document: bool,
    ) -> None:
        table = Document if is_document else Directory
        stmt = (
            update(table)
            .filter(
                table.uuid == uuid
            )
            .values(
                is_deleted = True,
                deleted_at = datetime.datetime.now(tz=datetime.timezone.utc),
                deleters_user_id = requester_user_id,
                deleters_user_uuid = requester_user_uuid,
            )
        )
        
        await session.execute(stmt)
        await session.commit()
