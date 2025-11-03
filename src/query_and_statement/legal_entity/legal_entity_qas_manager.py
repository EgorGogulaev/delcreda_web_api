import datetime
from typing import Dict, List, Literal, Optional, Tuple

from sqlalchemy import and_, func, or_, select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert

from src.models.order.mt_models import MTOrderData
from src.models.order.order_models import Order
from src.schemas.legal_entity.legal_entity_schema import FiltersLegalEntities, OrdersLegalEntities, FiltersPersons, OrdersPersons, CreatePersonsSchema
from src.models.legal_entity.bank_details_models import BankDetails
from src.models.legal_entity.legal_entity_models import LegalEntity, LegalEntityData, OrderAccessList, Person
from src.utils.reference_mapping_data.user.mapping import PRIVILEGE_MAPPING
from src.utils.reference_mapping_data.app.app_mapping_data import COUNTRY_MAPPING
from src.utils.reference_mapping_data.order.mapping import ORDER_TYPE_MAPPING


class LegalEntityQueryAndStatementManager:
    @staticmethod
    async def create_legal_entity(
        session: AsyncSession,
        
        owner_user_id: int,
        owner_user_uuid: str,
        new_legal_entity_uuid: str,
        directory_id: int,
        directory_uuid: str,
        
        order_access_list_id: int,
        
        country: int,
        registration_identifier_type: str,
        registration_identifier_value: str,
        tax_identifier: str,
        
        # LegalEntityData
        name_latin: Optional[str],
        name_national: Optional[str],
        organizational_and_legal_form_latin: Optional[str],
        organizational_and_legal_form_national: Optional[str],
        site: Optional[str],
        registration_date: datetime.date,
        legal_address: str,
        postal_address: Optional[str],
        additional_address: Optional[str],
    ) -> Tuple[LegalEntity, LegalEntityData]:
        # LegalEntityData
        new_le_data = LegalEntityData(
            name_latin=name_latin,
            name_national=name_national,
            organizational_and_legal_form_latin=organizational_and_legal_form_latin,
            organizational_and_legal_form_national=organizational_and_legal_form_national,
            site=site,
            registration_date=registration_date,
            legal_address=legal_address,
            postal_address=postal_address,
            additional_address=additional_address,
        )
        session.add(new_le_data)
        await session.flush()  # Генерируем ID для new_le_data
        
        # LegalEntity
        new_le = LegalEntity(
            uuid=new_legal_entity_uuid,
            
            country=country,
            registration_identifier_type=registration_identifier_type,
            registration_identifier_value=registration_identifier_value,
            tax_identifier=tax_identifier,
            
            user_id=owner_user_id,
            user_uuid=owner_user_uuid,
            directory_id=directory_id,
            directory_uuid=directory_uuid,
            order_access_list_id=order_access_list_id,
            data_id=new_le_data.id,
        )
        session.add(new_le)
        await session.commit()
        
        await session.refresh(new_le)
        await session.refresh(new_le_data)
        
        return (new_le, new_le_data)
    
    @staticmethod
    async def create_order_access_list(
        session: AsyncSession,
    ) -> int:
        stmt = (
            insert(OrderAccessList)
            .returning(OrderAccessList.id)
        )
        
        response = await session.execute(stmt)
        new_order_list_access_id: int = response.scalar_one()
        
        return new_order_list_access_id
    
    @staticmethod
    async def get_user_uuid_by_legal_entity_uuid(
        session: AsyncSession,
        
        legal_entity_uuid: str,
    ) -> Optional[str]:
        query = (
            select(LegalEntity.user_uuid)
            .filter(LegalEntity.uuid == legal_entity_uuid)
        )
        
        response = await session.execute(query)
        result = response.scalar_one_or_none()
        
        return result
    
    @staticmethod
    async def get_legal_entities(
        session: AsyncSession,
        
        user_uuid: Optional[str],
        legal_entity_name_ilike: Optional[str] = None,
        le_id_list: Optional[List[int]] = None,
        
        extended_output: bool = False,
        
        page: Optional[int] = None,
        page_size: Optional[int] = None,
        
        filter: Optional[FiltersLegalEntities] = None,
        order: Optional[OrdersLegalEntities] = None,
    ) -> Dict[str, List[Optional[LegalEntity|int|bool]] | List[Optional[Tuple[LegalEntity, bool]]]]:
        _filters = []
        
        if user_uuid:
            _filters.append(LegalEntity.user_uuid == user_uuid)
        
        if le_id_list:
            _filters.append(LegalEntity.id.in_(le_id_list))
        
        if filter is not None and filter.filters:
            for filter_item in filter.filters:
                column = getattr(LegalEntity, filter_item.field)
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
                column = getattr(LegalEntity, order_item.field)
                
                # Добавляем условие сортировки в зависимости от направления
                if order_item.direction == "asc":
                    _order_clauses.append(column.asc().nulls_last())
                else:
                    _order_clauses.append(column.desc().nulls_last())
        
        if not _order_clauses:
            _order_clauses.append(LegalEntity.id.asc())
        # ===== КОНЕЦ блока сортировки =====
        
        if extended_output:
            query = (
                select(
                    LegalEntity,
                    
                    LegalEntityData.name_latin,
                    LegalEntityData.name_national,
                    LegalEntityData.organizational_and_legal_form_latin,
                    LegalEntityData.organizational_and_legal_form_national,
                    LegalEntityData.updated_at,
                    # TODO тут можно добавить вывод полей (согласовать с Юрием)
                    
                    OrderAccessList.mt,
                )
                .outerjoin(LegalEntityData, LegalEntity.data_id == LegalEntityData.id)
                .outerjoin(OrderAccessList, LegalEntity.order_access_list == OrderAccessList.id)
                .filter(and_(*_filters))
            )
            if legal_entity_name_ilike:
                query = query.filter(
                    or_(
                        LegalEntityData.name_national.ilike(f"%{legal_entity_name_ilike}%"),
                        LegalEntityData.name_latin.ilike(f"%{legal_entity_name_ilike}%"),
                    )
                )
            query = query.order_by(*_order_clauses)
        else:
            query = (
                select(LegalEntity)
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
        count_query = select(func.count()).select_from(LegalEntity).filter(and_(*_filters))
        
        total_records = (await session.execute(count_query)).scalar()
        total_pages = (total_records + page_size - 1) // page_size if total_records else 0
        
        response = await session.execute(query)
        if extended_output:
            data = [{
                "legal_entity": item[0],
                
                "name_latin": item[1],
                "name_national": item[2],
                "organizational_and_legal_form_latin": item[3],
                "organizational_and_legal_form_national": item[4],
                "updated_at": item[5],
                # TODO тут можно добавить вывод полей (согласовать с Юрием)
                
                "mt": item[6],
            } for item in response.fetchall()]
        else:
            data = [(item[0], item[1]) for item in response.fetchall()]
        
        return {
            "data": data,
            "total_records": total_records,
            "total_pages": total_pages,
        }
    
    @staticmethod
    async def get_order_access_list_id_by_legal_entity_uuid(
        session: AsyncSession,
        
        legal_entity_uuid: str,
    ) -> Optional[int]:
        query = (
            select(LegalEntity.order_access_list)
            .filter(LegalEntity.uuid == legal_entity_uuid)
        )
        response = await session.execute(query)
        order_access_list_id: Optional[int] = response.scalar()
        
        return order_access_list_id
    
    @staticmethod
    async def update_legal_entity(
        session: AsyncSession,
        
        legal_entity_id: int,
        
        country: Literal[*COUNTRY_MAPPING, "~"], # type: ignore
        registration_identifier_type: Optional[str],
        registration_identifier_value: str,
        tax_identifier: str,
        is_active: bool|str,
    ) -> None:
        values_for_update = {
            "country": COUNTRY_MAPPING[country] if country != "~" else "~",
            "registration_identifier_type": registration_identifier_type,
            "registration_identifier_value": registration_identifier_value,
            "tax_identifier": tax_identifier,
            "is_active": is_active,
            
            "updated_at": datetime.datetime.now(tz=datetime.timezone.utc),
        }
        new_values = {k: v for k, v in values_for_update.items() if v != "~"}
        
        stmt = (
            update(LegalEntity)
            .filter(LegalEntity.id == legal_entity_id)
            .values(**new_values)
        )
        
        await session.execute(stmt)
        await session.commit()
    
    @staticmethod
    async def change_legal_entities_edit_status(
        session: AsyncSession,
        
        legal_entity_uuids: List[str],
        edit_status: bool,
    ) -> None:
        stmt = (
            update(LegalEntity)
            .where(LegalEntity.uuid.in_(legal_entity_uuids))
            .values(
                can_be_updated_by_user=edit_status,
            )
        )
        await session.execute(stmt)
        await session.commit()
    
    @staticmethod
    async def update_order_access_list(
        session: AsyncSession,
        
        order_access_list_id: int,
        order_type_dict: Dict[str, str|bool],
    ) -> None:
        values_for_update = {
            "mt": order_type_dict["MT"],
            # TODO тут будут другие бизнес процессы
        }
        new_values = {k: v for k, v in values_for_update.items() if v != "~"}
        stmt = (
            update(OrderAccessList)
            .filter(OrderAccessList.id == order_access_list_id)
            .values(**new_values)
        )
        await session.execute(stmt)
        await session.commit()
        
    @staticmethod
    async def get_legal_entities_data(
        session: AsyncSession,
        
        legal_entity_data_ids: List[Optional[int]],
    ) -> List[Optional[LegalEntityData]]:
        _filters = []
        
        if legal_entity_data_ids:
            _filters.append(LegalEntityData.id.in_(legal_entity_data_ids))
        
        query = (
            select(LegalEntityData)
            .filter(
                and_(
                    *_filters
                )
            )
        )
        
        response = await session.execute(query)
        result = [item[0] for item in response.all()]
        return result
    
    @staticmethod
    async def check_access(
        session: AsyncSession,
        
        requester_user_uuid: str,
        requester_user_privilege: int,
        
        legal_entity_uuid: str,
        
        for_create_order: bool = False,
        for_update_or_delete_legal_entity: bool = False,
    ) -> Optional[Tuple[int, int, str]]:
        _filters = [LegalEntity.uuid == legal_entity_uuid]
        
        if requester_user_privilege != PRIVILEGE_MAPPING["Admin"]:
            _filters.append(LegalEntity.user_uuid == requester_user_uuid)
            if for_update_or_delete_legal_entity:
                _filters.append(LegalEntity.can_be_updated_by_user == True)  # noqa: E712
        
        if for_create_order:
            _filters.append(LegalEntity.is_active == True)  # noqa: E712
        
        
        
        query = (
            select(LegalEntity.id, LegalEntity.data_id, LegalEntity.directory_uuid,)
            .filter(
                and_(
                    *_filters
                )
            )
        )
        
        response = await session.execute(query)
        result = response.one_or_none()
        
        return result
    
    @staticmethod
    async def update_legal_entity_data(
        session: AsyncSession,
        
        legal_entity_data_id: int,
        
        name_latin: Optional[str],
        name_national: Optional[str],
        organizational_and_legal_form_latin: Optional[str],
        organizational_and_legal_form_national: Optional[str],
        site: Optional[str],
        registration_date: Optional[datetime.date],
        legal_address: Optional[str],
        postal_address: Optional[str],
        additional_address: Optional[str],
    ) -> None:
        values_for_update = {
            "name_latin": name_latin,
            "name_national": name_national,
            "organizational_and_legal_form_latin": organizational_and_legal_form_latin,
            "organizational_and_legal_form_national": organizational_and_legal_form_national,
            "site": site,
            "registration_date": registration_date,
            "legal_address": legal_address,
            "postal_address": postal_address,
            "additional_address": additional_address,
            
            "updated_at": datetime.datetime.now(tz=datetime.timezone.utc),
        }
        new_values = {k: v for k, v in values_for_update.items() if v != "~"}
        
        stmt = (
            update(LegalEntityData)
            .filter(LegalEntityData.id == legal_entity_data_id)
            .values(**new_values)
        )
        
        await session.execute(stmt)
        await session.commit()
    
    @staticmethod
    async def delete_legal_entities(
        session: AsyncSession,
        
        legal_entities_uuids: List[str],
        le_ids_with_le_data_ids_with_dir_uuid: List[Tuple[int, int, str]],
    ) -> None:
        le_ids = [le_id for le_id, _, _ in le_ids_with_le_data_ids_with_dir_uuid]
        le_data_ids = [le_data_id for _, le_data_id, _ in le_ids_with_le_data_ids_with_dir_uuid]
        
        order_ids = []
        
        # MT
        query_order_and_order_data_ids_from_MT = (
            select(Order.id, Order.data_id)
            .where(
                and_(
                    Order.type == ORDER_TYPE_MAPPING["MT"],
                    Order.legal_entity_id.in_(le_ids),
                )
            )
        )
        # ...  TODO тут будут другие бизнес-направления
        
        # MT
        result_MT = await session.execute(query_order_and_order_data_ids_from_MT)
        # ...  TODO тут будут другие бизнес-направления
        
        # MT
        order_and_order_data_ids_MT: List[Tuple[int, int]] = [ids for ids in result_MT.all()]
        # ...  TODO тут будут другие бизнес-направления
        
        # MT
        order_ids_from_MT = [ids[0] for ids in order_and_order_data_ids_MT]
        order_data_ids_from_MT = [ids[1] for ids in order_and_order_data_ids_MT]
        # ...  TODO тут будут другие бизнес-направления
        
        order_ids.extend(order_ids_from_MT)
        
        stmt_delete_le_bank_details = (
            delete(BankDetails)
            .where(BankDetails.legal_entity_uuid.in_(legal_entities_uuids))
        )
        
        stmt_delete_le_persons = (
            delete(Person)
            .where(Person.legal_entity_uuid.in_(legal_entities_uuids))
        )
        
        stmt_delete_orders = (
            delete(Order)
            .where(Order.id.in_(order_ids))
        )
        
        # MT
        if order_data_ids_from_MT:
            stmt_delete_orders_data_from_MT = (
                delete(MTOrderData)
                .where(MTOrderData.id.in_(order_data_ids_from_MT))
            )
        # ...  TODO тут будут другие бизнес-направления
        
        stmt_delete_le_data = (
            delete(LegalEntityData)
            .where(LegalEntityData.id.in_(le_data_ids))
        )
        stmt_delete_le = (
            delete(LegalEntity)
            .where(LegalEntity.id.in_(le_ids))
        )
        
        await session.execute(stmt_delete_le_bank_details)
        await session.execute(stmt_delete_le_persons)
        await session.execute(stmt_delete_orders)
        # MT
        if order_data_ids_from_MT:
            await session.execute(stmt_delete_orders_data_from_MT)
        # ...  TODO тут будут другие бизнес-направления
        await session.execute(stmt_delete_le)
        await session.execute(stmt_delete_le_data)
        
        await session.commit()
    
    @staticmethod
    async def delete_orders_access_lists(
        session: AsyncSession,
        
        orders_access_lists_ids: List[int],
    ) -> None:
        stmt = (
            delete(OrderAccessList)
            .filter(OrderAccessList.id.in_(orders_access_lists_ids))
        )
        
        await session.execute(stmt)
        await session.commit()
    
    @staticmethod
    async def create_persons(
        session: AsyncSession,
        
        new_persons: CreatePersonsSchema,
    ) -> List[int]:
        new_person_objects = []
        
        for new_person in new_persons.new_persons:
            data = new_person.model_dump()
            if data["power_of_attorney_date"]:
                data["power_of_attorney_date"] = datetime.datetime.strptime(data["power_of_attorney_date"], "%d.%m.%Y").date()
            new_person_objects.append(data)
        
        stmt = (
            insert(Person)
            .values(new_person_objects)
            .returning(Person.id)
        )
        result = await session.execute(stmt)
        await session.commit()
        
        created_ids = result.scalars().all()
        
        return list(created_ids)
    
    @staticmethod
    async def get_persons(
        session: AsyncSession,
        
        person_ids: Optional[List[int]],
        legal_entity_uuid: Optional[str] = None,
        
        page: Optional[int] = None,
        page_size: Optional[int] = None,
        
        filter: Optional[FiltersPersons] = None,
        order: Optional[OrdersPersons] = None,
    ) -> Dict[str, List[Optional[Person]]|Optional[int]]:
        _filters = []
        
        if legal_entity_uuid:
            _filters.append(Person.legal_entity_uuid == legal_entity_uuid)
        
        if person_ids:
            _filters.append(Person.id.in_(person_ids))
        
        if filter is not None and filter.filters:
            for filter_item in filter.filters:
                column = getattr(Person, filter_item.field)
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
                column = getattr(Person, order_item.field)
                
                # Добавляем условие сортировки в зависимости от направления
                if order_item.direction == "asc":
                    _order_clauses.append(column.asc().nulls_last())
                else:
                    _order_clauses.append(column.desc().nulls_last())
        
        if not _order_clauses:
            _order_clauses.append(Person.id.asc())
        # ===== КОНЕЦ блока сортировки =====
        
        query = (
            select(Person)
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
        count_query = select(func.count()).select_from(Person).filter(and_(*_filters))
        
        total_records = (await session.execute(count_query)).scalar()
        total_pages = (total_records + page_size - 1) // page_size if total_records else 0
        
        response = await session.execute(query)
        data = [item[0] for item in response.all()]
        return {
            "data": data,
            "total_records": total_records,
            "total_pages": total_pages,
        }
    
    @staticmethod
    async def update_person(
        session: AsyncSession,
        
        person_id: int,
        
        surname: Optional[str],
        name: Optional[str],
        patronymic: Optional[str],
        gender: Optional[str],
        job_title: Optional[str],
        basic_action_signatory: Optional[str],
        power_of_attorney_number: Optional[str],
        power_of_attorney_date: Optional[datetime.date],
        email: Optional[str],
        phone: Optional[str],
        contact: Optional[str],
        legal_entity_uuid: Optional[str],
    ) -> None:
        values_for_update = {
            "surname": surname,
            "name": name,
            "patronymic": patronymic,
            "gender": gender,
            "job_title": job_title,
            "basic_action_signatory": basic_action_signatory,
            "power_of_attorney_number": power_of_attorney_number,
            "power_of_attorney_date": power_of_attorney_date,
            "email": email,
            "phone": phone,
            "contact": contact,
            "legal_entity_uuid": legal_entity_uuid,
            
            "updated_at": datetime.datetime.now(tz=datetime.timezone.utc),
        }
        new_values = {k: v for k, v in values_for_update.items() if v != "~"}
        
        stmt = (
            update(Person)
            .filter(Person.id == person_id)
            .values(**new_values)
        )
        
        await session.execute(stmt)
        await session.commit()
    
    @staticmethod
    async def delete_persons(
        session: AsyncSession,
        
        person_ids: List[int],
    ) -> None:
        stmt = (
            delete(Person)
            .filter(Person.id.in_(person_ids))
        )
        
        await session.execute(stmt)
        await session.commit()
