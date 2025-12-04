import datetime
from typing import Dict, List, Literal, Optional, Tuple

from sqlalchemy import and_, func, or_, select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert

from src.models.application.mt_models import MTApplicationData
from src.models.application.application_models import Application
from src.schemas.counterparty.counterparty_schema import CreateIndividualDataSchema, CreateLegalEntityDataSchema, FiltersCounterparties, OrdersCounterparties, FiltersPersons, OrdersPersons, CreatePersonsSchema, UpdateCounterpartySchema, UpdateIndividualDataSchema, UpdateLegalEntityDataSchema
from src.models.counterparty.bank_details_models import BankDetails
from src.models.counterparty.counterparty_models import Counterparty, IndividualData, LegalEntityData, ApplicationAccessList, Person
from src.utils.reference_mapping_data.user.mapping import PRIVILEGE_MAPPING
from src.utils.reference_mapping_data.app.app_mapping_data import COUNTRY_MAPPING
from src.utils.reference_mapping_data.application.mapping import APPLICATION_TYPE_MAPPING
from src.utils.reference_mapping_data.counterparty.mapping import COUNTERPARTY_TYPE_MAPPING


class CounterpartyQueryAndStatementManager:
    @staticmethod
    async def create_counterparty(
        session: AsyncSession,
        
        counterparty_type: Literal["ФЛ", "ЮЛ"],
        
        owner_user_id: int,
        owner_user_uuid: str,
        new_counterparty_uuid: str,
        directory_id: int,
        directory_uuid: str,
        
        application_access_list_id: int,
        
        country: int,
        identifier_type: str,
        identifier_value: str,
        tax_identifier: str,
        
        counterparty_data: CreateLegalEntityDataSchema|CreateIndividualDataSchema,
    ) -> Tuple[Counterparty, LegalEntityData|IndividualData]:
        if counterparty_type == "ЮЛ":
            # LegalEntityData  # FIXME
            new_counterparty_data = LegalEntityData(
                name_latin=counterparty_data.name_latin,
                name_national=counterparty_data.name_national,
                organizational_and_legal_form_latin=counterparty_data.organizational_and_legal_form_latin,
                organizational_and_legal_form_national=counterparty_data.organizational_and_legal_form_national,
                site=counterparty_data.site,
                registration_date=counterparty_data.registration_date,
                legal_address=counterparty_data.legal_address,
                postal_address=counterparty_data.postal_address,
                additional_address=counterparty_data.additional_address,
            )
        else:
            ...  # TODO тут должна быть логика для ФЛ
        session.add(new_counterparty_data)
        await session.flush()  # Генерируем ID для new_le_data
        
        # Counterparty
        new_counterparty = Counterparty(
            uuid=new_counterparty_uuid,
            type=counterparty_type,
            
            country=country,
            identifier_type=identifier_type,
            identifier_value=identifier_value,
            tax_identifier=tax_identifier,
            
            user_id=owner_user_id,
            user_uuid=owner_user_uuid,
            directory_id=directory_id,
            directory_uuid=directory_uuid,
            application_access_list=application_access_list_id,
            data_id=new_counterparty_data.id,
        )
        session.add(new_counterparty)
        await session.commit()
        
        await session.refresh(new_counterparty)
        await session.refresh(new_counterparty_data)
        
        return (new_counterparty, new_counterparty_data)
    
    @staticmethod
    async def create_application_access_list(
        session: AsyncSession,
    ) -> int:
        stmt = (
            insert(ApplicationAccessList)
            .returning(ApplicationAccessList.id)
        )
        
        response = await session.execute(stmt)
        new_application_list_access_id: int = response.scalar_one()
        
        return new_application_list_access_id
    
    @staticmethod
    async def get_user_uuid_by_counterparty_uuid(
        session: AsyncSession,
        
        counterparty_uuid: str,
    ) -> Optional[str]:
        query = (
            select(Counterparty.user_uuid)
            .filter(Counterparty.uuid == counterparty_uuid)
        )
        
        response = await session.execute(query)
        result = response.scalar_one_or_none()
        
        return result
    
    @staticmethod
    async def get_counterparties(  # FIXME
        session: AsyncSession,
        
        counterparty_type: Optional[Literal["ЮЛ", "ФЛ"]],
        user_uuid: Optional[str],
        legal_entity_name_ilike: Optional[str] = None,
        counterparty_id_list: Optional[List[int]] = None,
        
        extended_output: bool = False,
        
        page: Optional[int] = None,
        page_size: Optional[int] = None,
        
        filter: Optional[FiltersCounterparties] = None,
        order: Optional[OrdersCounterparties] = None,
    ) -> Dict[str, List[Optional[Counterparty|int|bool]] | List[Optional[Tuple[Counterparty, bool]]]]:
        _filters = []
        
        if user_uuid:
            _filters.append(Counterparty.user_uuid == user_uuid)
        
        if counterparty_id_list:
            _filters.append(Counterparty.id.in_(counterparty_id_list))
        
        if filter is not None and filter.filters:
            for filter_item in filter.filters:
                column = getattr(Counterparty, filter_item.field)
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
                column = getattr(Counterparty, order_item.field)
                
                # Добавляем условие сортировки в зависимости от направления
                if order_item.direction == "asc":
                    _order_clauses.append(column.asc().nulls_last())
                else:
                    _order_clauses.append(column.desc().nulls_last())
        
        if not _order_clauses:
            _order_clauses.append(Counterparty.id.asc())
        # ===== КОНЕЦ блока сортировки =====
        
        if extended_output:
            if counterparty_type == "ЮЛ":
                query = (
                    select(
                        Counterparty,
                        
                        LegalEntityData.name_latin,
                        LegalEntityData.name_national,
                        LegalEntityData.organizational_and_legal_form_latin,
                        LegalEntityData.organizational_and_legal_form_national,
                        LegalEntityData.updated_at,
                        # TODO тут можно добавить вывод полей (согласовать с Юрием)
                        
                        ApplicationAccessList.mt,
                    )
                    .outerjoin(LegalEntityData, Counterparty.data_id == LegalEntityData.id)
                    .outerjoin(ApplicationAccessList, Counterparty.application_access_list == ApplicationAccessList.id)
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
            elif counterparty_type == "ФЛ":
                ...  # TODO тут логика для ФЛ
            else:
                ...  # TODO тут логика для комбинированного набора данных
        else:
            query = (
                select(Counterparty)
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
        count_query = select(func.count()).select_from(Counterparty).filter(and_(*_filters))
        
        total_records = (await session.execute(count_query)).scalar()
        total_pages = (total_records + page_size - 1) // page_size if total_records else 0
        
        response = await session.execute(query)
        if extended_output:
            if counterparty_type == "ЮЛ":
                data = [{
                    "counterparty": item[0],
                    
                    "name_latin": item[1],
                    "name_national": item[2],
                    "organizational_and_legal_form_latin": item[3],
                    "organizational_and_legal_form_national": item[4],
                    "updated_at": item[5],
                    # TODO тут можно добавить вывод полей (согласовать с Юрием)
                    
                    "mt": item[6],
                } for item in response.fetchall()]
            elif counterparty_type == "ФЛ":
                ...  # TODO тут логики для
            else:
                ...  # TODO тут логика для комбинированного набора данных
        else:
            data = [(item[0], item[1]) for item in response.fetchall()]  # FIXME при вводе ФЛ тут нужны будут правки
        
        return {
            "data": data,
            "total_records": total_records,
            "total_pages": total_pages,
        }
    
    @staticmethod
    async def get_application_access_list_id_by_counterparty_uuid(
        session: AsyncSession,
        
        counterparty_uuid: str,
    ) -> Optional[int]:
        query = (
            select(Counterparty.application_access_list)
            .filter(Counterparty.uuid == counterparty_uuid)
        )
        response = await session.execute(query)
        application_access_list_id: Optional[int] = response.scalar()
        
        return application_access_list_id
    
    @staticmethod
    async def update_counterparty(
        session: AsyncSession,
        
        counterparty_id: int,
        
        data_for_update: UpdateCounterpartySchema,
    ) -> None:
        values_for_update = {
            "country": COUNTRY_MAPPING[data_for_update.country] if data_for_update.country != "~" else "~",
            "identifier_type": data_for_update.identifier_type,
            "identifier_value": data_for_update.identifier_value,
            "tax_identifier": data_for_update.tax_identifier,
            "is_active": data_for_update.is_active,
            
            "updated_at": datetime.datetime.now(tz=datetime.timezone.utc),
        }
        new_values = {k: v for k, v in values_for_update.items() if v != "~"}
        
        stmt = (
            update(Counterparty)
            .filter(Counterparty.id == counterparty_id)
            .values(**new_values)
        )
        
        await session.execute(stmt)
        await session.commit()
    
    @staticmethod
    async def change_counterparties_edit_status(
        session: AsyncSession,
        
        counterparty_uuids: List[str],
        edit_status: bool,
    ) -> None:
        stmt = (
            update(Counterparty)
            .where(Counterparty.uuid.in_(counterparty_uuids))
            .values(
                can_be_updated_by_user=edit_status,
            )
        )
        await session.execute(stmt)
        await session.commit()
    
    @staticmethod
    async def update_application_access_list(
        session: AsyncSession,
        
        application_access_list_id: int,
        application_type_dict: Dict[str, str|bool],
    ) -> None:
        values_for_update = {
            "mt": application_type_dict["MT"],
            # TODO тут будут другие бизнес процессы
        }
        new_values = {k: v for k, v in values_for_update.items() if v != "~"}
        stmt = (
            update(ApplicationAccessList)
            .filter(ApplicationAccessList.id == application_access_list_id)
            .values(**new_values)
        )
        await session.execute(stmt)
        await session.commit()
        
    @staticmethod
    async def get_counterparties_data(
        session: AsyncSession,
        
        counterparty_type: Literal["ЮЛ", "ФЛ"],
        
        counterparty_data_ids: List[Optional[int]],
    ) -> List[Optional[LegalEntityData|IndividualData]]:
        _filters = []
        
        if counterparty_type == "ЮЛ":
            if counterparty_data_ids:
                _filters.append(LegalEntityData.id.in_(counterparty_data_ids))
            
            query = (
                select(LegalEntityData)
                .filter(
                    and_(
                        *_filters
                    )
                )
            )
        else:
            ...  # TODO тут логика для ФЛ
        
        response = await session.execute(query)
        result = [item[0] for item in response.all()]
        return result
    
    @staticmethod
    async def check_access(
        session: AsyncSession,
        
        requester_user_uuid: str,
        requester_user_privilege: int,
        
        counterparty_uuid: str,
        
        for_create_application: bool = False,
        for_update_or_delete_counterparty: bool = False,
    ) -> Optional[Tuple[int, int, int, str]]:
        _filters = [Counterparty.uuid == counterparty_uuid]
        
        if requester_user_privilege != PRIVILEGE_MAPPING["Admin"]:
            _filters.append(Counterparty.user_uuid == requester_user_uuid)
            if for_update_or_delete_counterparty:
                _filters.append(Counterparty.can_be_updated_by_user == True)  # noqa: E712
        
        if for_create_application:
            _filters.append(Counterparty.is_active == True)  # noqa: E712
        
        
        query = (
            select(Counterparty.id, Counterparty.type, Counterparty.data_id, Counterparty.directory_uuid,)
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
    async def update_counterparty_data(
        session: AsyncSession,
        
        counterparty_data_id: int,
        
        data_for_update: UpdateLegalEntityDataSchema | UpdateIndividualDataSchema,
    ) -> None:
        if isinstance(data_for_update, UpdateLegalEntityDataSchema):
            values_for_update = {
                "name_latin": data_for_update.name_latin,
                "name_national": data_for_update.name_national,
                "organizational_and_legal_form_latin": data_for_update.organizational_and_legal_form_latin,
                "organizational_and_legal_form_national": data_for_update.organizational_and_legal_form_national,
                "site": data_for_update.site,
                "registration_date": data_for_update.registration_date,
                "legal_address": data_for_update.legal_address,
                "postal_address": data_for_update.postal_address,
                "additional_address": data_for_update.additional_address,
                
                "updated_at": datetime.datetime.now(tz=datetime.timezone.utc),
            }
        else:
            ...  # TODO тут будет логика для ФЛ
        
        new_values = {k: v for k, v in values_for_update.items() if v != "~"}
        if isinstance(data_for_update, UpdateLegalEntityDataSchema):
            stmt = (
                update(LegalEntityData)
                .filter(LegalEntityData.id == counterparty_data_id)
                .values(**new_values)
            )
        else:
            ...  # TODO тут будет логика для ФЛ
        
        await session.execute(stmt)
        await session.commit()
    
    @staticmethod
    async def delete_counterparties(
        session: AsyncSession,
        
        counterparty_uuids: List[str],
        counterparty_ids_with_counterparty_type_ids_with_counterparty_data_ids_with_dir_uuid: List[Tuple[int, int, int, str]],
    ) -> None:
        counterparty_ids = [counterparty_id for counterparty_id, _, _, _ in counterparty_ids_with_counterparty_type_ids_with_counterparty_data_ids_with_dir_uuid]
        
        counterparty_ids_with_type_ids = [(counterparty_id, counterparty_type_id) for counterparty_id, counterparty_type_id, _, _ in counterparty_ids_with_counterparty_type_ids_with_counterparty_data_ids_with_dir_uuid]
        counterparty_le_ids = [le_id for le_id, counterparty_type_id in counterparty_ids_with_type_ids if counterparty_type_id == COUNTERPARTY_TYPE_MAPPING["ЮЛ"]]
        counterparty_individual_ids = [individual_id for individual_id, counterparty_type_id in counterparty_ids_with_type_ids if counterparty_type_id == COUNTERPARTY_TYPE_MAPPING["ФЛ"]]
        
        application_ids = []
        
        # MT
        query_application_and_application_data_ids_from_MT = (
            select(Application.id, Application.data_id)
            .where(
                and_(
                    Application.type == APPLICATION_TYPE_MAPPING["MT"],
                    Application.counterparty_id.in_(counterparty_ids),
                )
            )
        )
        # ...  TODO тут будут другие бизнес-направления
        
        # MT
        result_MT = await session.execute(query_application_and_application_data_ids_from_MT)
        # ...  TODO тут будут другие бизнес-направления
        
        # MT
        application_and_application_data_ids_MT: List[Tuple[int, int]] = [ids for ids in result_MT.all()]
        # ...  TODO тут будут другие бизнес-направления
        
        # MT
        application_ids_from_MT = [ids[0] for ids in application_and_application_data_ids_MT]
        application_data_ids_from_MT = [ids[1] for ids in application_and_application_data_ids_MT]
        # ...  TODO тут будут другие бизнес-направления
        
        application_ids.extend(application_ids_from_MT)
        
        stmt_delete_counterparty_bank_details = (
            delete(BankDetails)
            .where(BankDetails.counterparty_uuid.in_(counterparty_uuids))
        )
        
        stmt_delete_counterparty_persons = (
            delete(Person)
            .where(Person.counterparty_uuid.in_(counterparty_uuids))
        )
        
        stmt_delete_applications = (
            delete(Application)
            .where(Application.id.in_(application_ids))
        )
        
        # MT
        if application_data_ids_from_MT:
            stmt_delete_applications_data_from_MT = (
                delete(MTApplicationData)
                .where(MTApplicationData.id.in_(application_data_ids_from_MT))
            )
        # ...  TODO тут будут другие бизнес-направления
        stmt_delete_counterparty_data_le = (
            delete(LegalEntityData)
            .where(LegalEntityData.id.in_(counterparty_le_ids))
        )
        
        stmt_delete_counterparty_data_individual = (
            delete(IndividualData)
            .where(IndividualData.id.in_(counterparty_individual_ids))
        )
        stmt_delete_counterparty = (
            delete(Counterparty)
            .where(Counterparty.id.in_(counterparty_ids))
        )
        
        await session.execute(stmt_delete_counterparty_bank_details)
        await session.execute(stmt_delete_counterparty_persons)
        await session.execute(stmt_delete_applications)
        # MT
        if application_data_ids_from_MT:
            await session.execute(stmt_delete_applications_data_from_MT)
        # ...  TODO тут будут другие бизнес-направления
        await session.execute(stmt_delete_counterparty)
        await session.execute(stmt_delete_counterparty_data_le)
        await session.execute(stmt_delete_counterparty_data_individual)
        
        await session.commit()
    
    @staticmethod
    async def delete_applications_access_lists(
        session: AsyncSession,
        
        applications_access_lists_ids: List[int],
    ) -> None:
        stmt = (
            delete(ApplicationAccessList)
            .filter(ApplicationAccessList.id.in_(applications_access_lists_ids))
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
        counterparty_uuid: Optional[str] = None,
        
        page: Optional[int] = None,
        page_size: Optional[int] = None,
        
        filter: Optional[FiltersPersons] = None,
        order: Optional[OrdersPersons] = None,
    ) -> Dict[str, List[Optional[Person]]|Optional[int]]:
        _filters = []
        
        if counterparty_uuid:
            _filters.append(Person.counterparty_uuid == counterparty_uuid)
        
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
        counterparty_uuid: Optional[str],
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
            "counterparty_uuid": counterparty_uuid,
            
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
