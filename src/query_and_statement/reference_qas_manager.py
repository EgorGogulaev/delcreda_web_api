import datetime
from typing import Any, Dict, List, Literal, Optional

from sqlalchemy import and_, delete, func, insert, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from config import APP_LOGIN, APP_PASSWORD
from connection_module import async_session_maker
from src.schemas.reference_schema import FiltersServiceNote, OrdersServiceNote
from src.models.legal_entity.legal_entity_models import LegalEntity
from src.models.application.application_models import Application
from src.models.notification_models import Notification
from src.models.file_store_models import Document, Directory
from src.models.reference_models import ErrLog, ServiceNote


class ReferenceQueryAndStatementManager:
    @staticmethod
    async def app_auth(
        login: str,
        password: str,
    ) -> bool:
        if all([APP_LOGIN == login, APP_PASSWORD == password]):
            return True
        else:
            return False
    
    @staticmethod
    async def check_uuid(
        session: AsyncSession,
        
        uuid: str,
        object_type: Literal["Directory", "Document", "Notification", "Legal entity", "Application",]
    ) -> bool:
        """Проверка наличия uuid для Файла/Директории/Уведомления/ЮЛ/Заявки. Возвращает Fasle если uuid свободен."""
        match object_type:
            case "Document":
                table = Document
            case "Directory":
                table = Directory
            case "Notification":
                table = Notification
            case "Legal entity":
                table = LegalEntity
            case "Application":
                table = Application
        query = (
            select(table.id)
            .filter(table.uuid == uuid)
        )
        response = await session.execute(query)
        result = response.one_or_none()
        if result is None:
            return False
        else:
            return True
    
    @staticmethod
    async def create_service_note(
        session: AsyncSession,
        
        service_note_data: Dict[str, Any],
    ) -> None:
        stmt = (
            insert(ServiceNote)
            .values(
                subject_id=service_note_data["subject_id"],
                subject_uuid=service_note_data["subject_uuid"],
                creator_id=service_note_data["creator_id"],
                creator_uuid=service_note_data["creator_uuid"],
                title=service_note_data["title"],
                data=service_note_data["data"],
            )
        )
        await session.execute(stmt)
        await session.commit()
    
    @staticmethod
    async def get_service_notes(
        session: AsyncSession,
        
        subject_id: Optional[int]=None,
        subject_uuid: Optional[str]=None,
        
        page: Optional[int]=None,
        page_size: Optional[int]=None,
        
        filter: Optional[FiltersServiceNote] = None,
        order: Optional[OrdersServiceNote] = None,
    ) -> Dict[str, List[Optional[ServiceNote]]|Optional[int]]:
        _filters = []
        if subject_id:
            _filters.append(ServiceNote.subject_id == subject_id)
            if subject_uuid:
                _filters.append(ServiceNote.subject_uuid == subject_uuid)
        
        if filter is not None and filter.filters:
            for filter_item in filter.filters:
                column = getattr(ServiceNote, filter_item.field)
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
                column = getattr(ServiceNote, order_item.field)
                
                # Добавляем условие сортировки в зависимости от направления
                if order_item.direction == "asc":
                    _order_clauses.append(column.asc().nulls_last())
                else:
                    _order_clauses.append(column.desc().nulls_last())
        
        if not _order_clauses:
            _order_clauses.append(ServiceNote.id.asc())
        # ===== КОНЕЦ блока сортировки =====
        
        query = (
            select(ServiceNote)
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
        count_query = select(func.count()).select_from(ServiceNote).filter(and_(*_filters))
        
        total_records = (await session.execute(count_query)).scalar()
        total_pages = (total_records + page_size - 1) // page_size if total_records else 0
        
        response = await session.execute(query)
        data = [item[0] for item in response.fetchall()]
        return {
            "data": data,
            "total_records": total_records,
            "total_pages": total_pages,
        }
    
    @staticmethod
    async def update_service_note(
        session: AsyncSession,
        
        creator_id: int,
        creator_uuid: str,
        service_note_id: int,
        new_title: str,
        new_data: Optional[str],
    ) -> None:
        values_for_update = {
            "creator_id": creator_id,
            "creator_uuid": creator_uuid,
            "title": new_title,
            "data": new_data,
            "updated_at": datetime.datetime.now(tz=datetime.timezone.utc)
        }
        new_values = {k: v for k, v in values_for_update.items() if v != "~"}
        
        stmt = (
            update(ServiceNote)
            .filter(ServiceNote.id == service_note_id)
            .values(
                **new_values
            )
            
        )
        await session.execute(stmt)
        await session.commit()
    
    @staticmethod
    async def delete_service_notes(
        session: AsyncSession,
        
        service_notes_ids: Optional[List[int]],
        subject_id: Optional[int],
        subject_uuid: Optional[str],
    ) -> None:
        _filters = []
        if service_notes_ids and len(service_notes_ids) > 0:
            _filters.append(ServiceNote.id.in_(service_notes_ids))
        if subject_id:
            _filters.append(ServiceNote.subject_id == subject_id)
        if subject_uuid:
            _filters.append(ServiceNote.subject_uuid == subject_uuid)
            
        stmt = (
            delete(ServiceNote)
            .filter(
                and_(
                    *_filters
                )
            )
        )
        await session.execute(stmt)
        await session.commit()
    
    
    @staticmethod
    async def create_errlog(
        endpoint: str,
        
        params: Optional[Dict],
        msg: Optional[str],
        
        user_uuid: str,
    ) -> int:
        async with async_session_maker() as session:
            stmt = (
                insert(ErrLog)
                .values(
                    endpoint=endpoint,
                    params=params,
                    msg=msg,
                    user_uuid=user_uuid,
                ).returning(ErrLog.id)
            )
            
            log_id = await session.execute(stmt)
            await session.commit()
            
            return log_id.scalar()
    
    @staticmethod
    async def _test(
        session: AsyncSession,
    ):
        # FIXME
        ...
