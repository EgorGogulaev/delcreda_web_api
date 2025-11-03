import datetime
from typing import Any, Dict, List, Literal, Optional, Tuple

from sqlalchemy.ext.asyncio import AsyncSession

from connection_module import SignalConnector
from src.service.order.order_service import OrderService
from src.models.order.order_models import Order
from src.service.order.mt_order_service import MTOrderService
from src.schemas.legal_entity.legal_entity_schema import FiltersLegalEntities, FiltersPersons, OrdersLegalEntities, OrdersPersons, CreatePersonsSchema
from src.service.chat_service import ChatService
from src.service.file_store_service import FileStoreService
from src.models.legal_entity.legal_entity_models import LegalEntity, LegalEntityData, Person
from src.query_and_statement.legal_entity.legal_entity_qas_manager import LegalEntityQueryAndStatementManager
from src.query_and_statement.user_qas_manager import UserQueryAndStatementManager
from src.utils.reference_mapping_data.user.mapping import PRIVILEGE_MAPPING
from src.utils.reference_mapping_data.file_store.mapping import DIRECTORY_TYPE_MAPPING
from src.utils.reference_mapping_data.app.app_mapping_data import COUNTRY_MAPPING


class LegalEntityService:
    @classmethod
    async def create_legal_entity(
        cls,
        session: AsyncSession,
        
        requester_user_uuid: str,
        requester_user_privilege: int,
        
        owner_user_uuid: str,
        new_directory_uuid: Optional[str],
        
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
    ) -> Tuple[Tuple[LegalEntity, LegalEntityData], Dict[str, int|str]]:
        if requester_user_privilege != PRIVILEGE_MAPPING["Admin"]:
            assert requester_user_uuid == owner_user_uuid, "Вы не можете создать ЮЛ для другого Пользователя!"
        
        assert name_latin or name_national, "Не указано наименование ЮЛ!"
        assert organizational_and_legal_form_latin or organizational_and_legal_form_national, "Не указана организационно-правовая форма ЮЛ!"
        
        owner_user_id: int = await UserQueryAndStatementManager.get_user_id_by_uuid(
            session=session,
            
            uuid=owner_user_uuid,
        )
        owner_s3_login: Optional[str] = await UserQueryAndStatementManager.get_user_s3_login(
            user_id=owner_user_id,
        )
        assert owner_s3_login, "У пользователя отсутствует логин в S3!"
        user_dirs: Dict[str, Any] = await FileStoreService.get_dir_info_from_db(
            session=session,
            
            requester_user_uuid=requester_user_uuid,
            requester_user_privilege=requester_user_privilege,
            owner_user_uuid=owner_user_uuid,
            visible=True,
        )
        assert user_dirs["count"], "Не найдена ни одна директория по указанным данным Пользователя!"
        parent_directory_uuid = None
        for dir_id in user_dirs["data"]:
            if user_dirs["data"][dir_id]["type"] == DIRECTORY_TYPE_MAPPING["Пользовательская директория"]:
                parent_directory_uuid = user_dirs["data"][dir_id]["uuid"]
        assert parent_directory_uuid, "У Пользователя нет пользовательской Директории!"
        new_le_dir_data: Dict[str, Any] = await FileStoreService.create_directory(
            session=session,
            
            requester_user_uuid=requester_user_uuid,
            requester_user_privilege=requester_user_privilege,
            owner_s3_login=owner_s3_login,
            owner_user_uuid=owner_user_uuid,
            directory_type=DIRECTORY_TYPE_MAPPING["Директория ЮЛ"],
            new_directory_uuid=new_directory_uuid,
            parent_directory_uuid=parent_directory_uuid,
        )
        
        new_order_access_list_id: int = await cls.__create_order_access_list(
            session=session,
        )
        
        new_le_uuid_coro = await SignalConnector.generate_identifiers(target="ЮЛ", count=1)
        new_le_uuid = new_le_uuid_coro[0]
        
        new_le_with_data: Tuple[LegalEntity, LegalEntityData] = await LegalEntityQueryAndStatementManager.create_legal_entity(
            session=session,
            
            owner_user_id=owner_user_id,
            owner_user_uuid=owner_user_uuid,
            new_legal_entity_uuid=new_le_uuid,
            directory_id=new_le_dir_data["id"],
            directory_uuid=new_le_dir_data["uuid"],
            order_access_list_id=new_order_access_list_id,
            
            country=country,
            registration_identifier_type=registration_identifier_type,
            registration_identifier_value=registration_identifier_value,
            tax_identifier=tax_identifier,
            
            # LegalEntityData
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
        
        new_chat = await ChatService.create_chat(
            session=session,
            
            chat_subject="ЮЛ",
            subject_uuid=new_le_uuid,
        )
        
        return new_le_with_data, new_chat
    
    @staticmethod
    async def __create_order_access_list(
        session: AsyncSession,
    ) -> int:
        new_order_access_list_id: int = await LegalEntityQueryAndStatementManager.create_order_access_list(
            session=session
        )
        
        return new_order_access_list_id
    
    @staticmethod
    async def get_legal_entities(
        session: AsyncSession,
        
        requester_user_uuid: str,
        requester_user_privilege: int,
        
        user_uuid: Optional[str],
        legal_entity_name_ilike: Optional[str] = None,
        
        extended_output: bool = False,
        
        page: Optional[int] = None,
        page_size: Optional[int] = None,
        
        filter: Optional[FiltersLegalEntities] = None,
        order: Optional[OrdersLegalEntities] = None,
    ) -> Dict[str, List[Optional[LegalEntity|int|bool]] | List[Optional[Tuple[LegalEntity, bool]]]]:
        if page or page_size:
            assert page and page_size and page > 0 and page_size > 0, "Не корректное разделение на страницы, вывода данных!"
        if extended_output is False:
            assert not legal_entity_name_ilike, "Можно искать по названию компании только при расширенном выводе (extended_output=true)!"
        if requester_user_privilege != PRIVILEGE_MAPPING["Admin"]:
            assert user_uuid, "Вы не можете просмотреть все ЮЛ - всех пользователей, не являясь Адмиинистратором!"
            assert user_uuid == requester_user_uuid, "Вы не можете просмотреть ЮЛ других пользователей!"
            
        legal_entities: Dict[str, List[Optional[LegalEntity|int|bool]] | List[Optional[Tuple[LegalEntity, bool]]]] = await LegalEntityQueryAndStatementManager.get_legal_entities(
            session=session,
            
            user_uuid=user_uuid,
            legal_entity_name_ilike=legal_entity_name_ilike,
            
            extended_output=extended_output,
            
            page=page,
            page_size=page_size,
            
            filter=filter,
            order=order,
        )
        
        return  legal_entities
    
    @staticmethod
    async def update_legal_entity(
        session: AsyncSession,
        
        requester_user_uuid: str,
        requester_user_privilege: int,
        
        legal_entity_uuid: str,
        
        country: Literal[*COUNTRY_MAPPING, "~"] = "~", # type: ignore
        registration_identifier_type: Optional[str] = "~",
        registration_identifier_value: str = "~",
        tax_identifier: str = "~",
        is_active: bool|str = "~",
    ) -> None:
        le_check_access_response_object: Optional[Tuple[int, int, str]] = await LegalEntityQueryAndStatementManager.check_access(
            session=session,
            
            requester_user_uuid=requester_user_uuid,
            requester_user_privilege=requester_user_privilege,
            legal_entity_uuid=legal_entity_uuid,
            for_update_or_delete_legal_entity=True,
        )
        assert le_check_access_response_object, "Вы не можете обновлять ЮЛ других Пользователей или же доступ редактирования данного ЮЛ ограничен!"
        assert list(
            filter(
                lambda x: x != "~",
                [
                    country,
                    registration_identifier_type, registration_identifier_value,
                    tax_identifier,
                    is_active,
                ]
            )
        ), "Хотя бы одно поле должно быть изменено для обновления данных о ЮЛ!"
        
        await LegalEntityQueryAndStatementManager.update_legal_entity(
            session=session,
            
            legal_entity_id=le_check_access_response_object[0],
            
            country=country,
            registration_identifier_type=registration_identifier_type,
            registration_identifier_value=registration_identifier_value,
            tax_identifier=tax_identifier,
            is_active=is_active,
        )
    
    @staticmethod
    async def change_legal_entities_edit_status(
        session: AsyncSession,
        
        requester_user_uuid: str,
        requester_user_privilege: int,
        
        legal_entity_uuids: List[str],
        edit_status: bool,
    ) -> None:
        if requester_user_privilege != PRIVILEGE_MAPPING["Admin"]:
            raise AssertionError("У Вас недостаточно прав для изменения статуса возможности редактирования информации о ЮЛ!")
        assert legal_entity_uuids, "Должен быть указан UUID, хотя бы одного ЮЛ!"
        assert isinstance(edit_status, bool), "Статус должен быть булевым значением!"
        
        await LegalEntityQueryAndStatementManager.change_legal_entities_edit_status(
            session=session,
            
            legal_entity_uuids=legal_entity_uuids,
            edit_status=edit_status,
        )
    
    @staticmethod
    async def update_order_access_list(
        session: AsyncSession,
        
    ) -> None:
        ...  # TODO Реализовать
    
    @staticmethod
    async def get_legal_enities_data(
        session: AsyncSession,
        
        requester_user_uuid: str,
        requester_user_privilege: int,
        
        les_uuid_list: List[Optional[str]],
        user_uuid: Optional[str],
    ) -> List[Optional[LegalEntityData]]:
        if requester_user_privilege != PRIVILEGE_MAPPING["Admin"]:
            assert user_uuid, "Вы не можете просмотреть все данные ЮЛ - всех пользователей, не являясь Адмиинистратором!"
            assert user_uuid == requester_user_uuid, "Вы не можете просмотреть данные ЮЛ других пользователей!"
        le_data_ids: List[Optional[int]] = []
        for le_uuid in tuple(set(les_uuid_list)):
            le_check_access_response_object: Optional[Tuple[int, int, str]] = await LegalEntityQueryAndStatementManager.check_access(
                session=session,
                
                requester_user_uuid=user_uuid,
                requester_user_privilege=requester_user_privilege,
                legal_entity_uuid=le_uuid,
            )
            assert le_check_access_response_object, f"Вы не являетесь владельцем ЮЛ с uuid {le_uuid}!"
            le_data_ids.append(le_check_access_response_object[1])
        
        if requester_user_privilege != PRIVILEGE_MAPPING["Admin"] and not le_data_ids:
            return []
        
        legal_entities_data: List[Optional[LegalEntityData]] = await LegalEntityQueryAndStatementManager.get_legal_entities_data(
            session=session,
            
            legal_entity_data_ids=le_data_ids,
        )
        
        return  legal_entities_data
    
    @staticmethod
    async def update_legal_entity_data(
        session: AsyncSession,
        
        requester_user_uuid: str,
        requester_user_privilege: int,
        
        legal_entity_uuid: str,
        
        name_latin: Optional[str],
        name_national: Optional[str],
        organizational_and_legal_form_latin: Optional[str],
        organizational_and_legal_form_national: Optional[str],
        site: Optional[str],
        registration_date: Optional[str],
        legal_address: Optional[str],
        postal_address: Optional[str],
        additional_address: Optional[str],
    ) -> None:
        le_check_access_response_object: Optional[Tuple[int, int, str]] = await LegalEntityQueryAndStatementManager.check_access(
            session=session,
            
            requester_user_uuid=requester_user_uuid,
            requester_user_privilege=requester_user_privilege,
            legal_entity_uuid=legal_entity_uuid,
            for_update_or_delete_legal_entity=True,
        )
        assert le_check_access_response_object, "Вы не можете обновлять ЮЛ других Пользователей или же доступ редактирования данного ЮЛ ограничен!"
        assert list(
            filter(
                lambda x: x != "~",
                [
                    name_latin, name_national,
                    organizational_and_legal_form_latin, organizational_and_legal_form_national,
                    site,
                    registration_date,
                    legal_address, postal_address, additional_address,
                ]
            )
        ), "Хотя бы одно поле должно быть изменено для обновления данных о ЮЛ!"
        
        await LegalEntityQueryAndStatementManager.update_legal_entity_data(
            session=session,
            
            legal_entity_data_id=le_check_access_response_object[1],
            
            name_latin=name_latin,
            name_national=name_national,
            organizational_and_legal_form_latin=organizational_and_legal_form_latin,
            organizational_and_legal_form_national=organizational_and_legal_form_national,
            site=site,
            registration_date=datetime.datetime.strptime(registration_date, "%d.%m.%Y").date() if registration_date and registration_date != "~" else None,
            legal_address=legal_address,
            postal_address=postal_address,
            additional_address=additional_address,
        )
    
    @staticmethod
    async def delete_legal_entities(  # TODO нужно предусмотреть удаление ЧАТОВ и СМС!!!
        session: AsyncSession,
        
        requester_user_id: int,
        requester_user_uuid: str,
        requester_user_privilege: int,
        
        legal_entities_uuids: List[str],
    ) -> None:
        assert legal_entities_uuids, "Для удаления ЮЛ, нужно указать хотя бы 1 ID!"
        # if requester_user_privilege != PRIVILEGE_MAPPING["Admin"]:
        #     raise AssertionError("Вы не можете удалять ЮЛ. Недостаточно прав!")
        
        le_ids_with_le_data_ids_with_dir_uuid: List[Tuple[int, int, str]] = [] # type: ignore
        order_uuids: List[str] = []
        for le_uuid in legal_entities_uuids:
            le_check_access_response_object: Optional[Tuple[int, int, str]] = await LegalEntityQueryAndStatementManager.check_access(
                session=session,
                
                requester_user_uuid=requester_user_uuid,
                requester_user_privilege=requester_user_privilege,
                legal_entity_uuid=le_uuid,
                for_update_or_delete_legal_entity=True,
            )
            assert le_check_access_response_object, "Вы не можете удалять информацию ЮЛ других Пользователей или же доступ к редактирования данного ЮЛ ограничен!"
            le_ids_with_le_data_ids_with_dir_uuid.append(le_check_access_response_object)
            
            le_orders: Dict[str, List[Optional[Order]]|Optional[int]] = await MTOrderService.get_orders(
                session=session,
                
                requester_user_uuid=requester_user_uuid,
                requester_user_privilege=requester_user_privilege,
                user_uuid=requester_user_uuid if requester_user_privilege != PRIVILEGE_MAPPING["Admin"] else None,
                legal_entity_uuid=le_uuid,
            )
            for order in le_orders["data"]:
                if order and order.uuid:
                    order_uuids.append(order.uuid)
        
        for _, _, dir_uuid in le_ids_with_le_data_ids_with_dir_uuid:
            try:
                await FileStoreService.delete_doc_or_dir(
                    session=session,
                    
                    requester_user_id=requester_user_id,
                    requester_user_uuid=requester_user_uuid,
                    requester_user_privilege=requester_user_privilege,
                    
                    uuid=dir_uuid,
                    is_document=False,
                    for_user=True,
                )
            except: ...  # noqa: E722
        try:
            await OrderService.delete_orders(
                session=session,
                
                requester_user_id=requester_user_id,
                requester_user_uuid=requester_user_uuid,
                requester_user_privilege=requester_user_privilege,
                
                orders_uuids=order_uuids,
            )
        except: ...  # noqa: E722
        
        await LegalEntityQueryAndStatementManager.delete_legal_entities(
            session=session,
            
            legal_entities_uuids=legal_entities_uuids,
            le_ids_with_le_data_ids_with_dir_uuid=le_ids_with_le_data_ids_with_dir_uuid,
        )
    
    @staticmethod
    async def __delete_orders_access_lists(
        session: AsyncSession,
        
    ) -> None:
        ...  # TODO Реализовать
    
    @staticmethod
    async def create_persons(
        session: AsyncSession,
        
        requester_user_uuid: str,
        requester_user_privilege: int,
        
        new_persons: CreatePersonsSchema,
    ) -> List[int]:
        if requester_user_privilege != PRIVILEGE_MAPPING["Admin"]:
            le_uuid_tuple = tuple(set([new_person.legal_entity_uuid for new_person in new_persons.new_persons]))
            assert len(le_uuid_tuple) == 1, "Вы не можете добавлять информацию ФЛ к ЮЛ других Пользователей или к нескольким ЮЛ одновременно!"
            le_check_access_response_object: Optional[Tuple[int, int, str]] = await LegalEntityQueryAndStatementManager.check_access(
                session=session,
                
                requester_user_uuid=requester_user_uuid,
                requester_user_privilege=requester_user_privilege,
                legal_entity_uuid=le_uuid_tuple[0],
            )
            assert le_check_access_response_object, "Вы не можете добавлять информацию ФЛ к ЮЛ других Пользователей или же доступ к редактирования данного ЮЛ ограничен!!"
        
        new_person_ids: List[int] = await LegalEntityQueryAndStatementManager.create_persons(
            session=session,
            
            new_persons=new_persons,
        )
        
        return new_person_ids
    
    @staticmethod
    async def get_persons(
        session: AsyncSession,
        
        requester_user_uuid: str,
        requester_user_privilege: int,
        
        legal_entity_uuid: Optional[str],
        person_ids: Optional[List[int]] = None,
        
        page: Optional[int] = None,
        page_size: Optional[int] = None,
        
        filter: Optional[FiltersPersons] = None,
        order: Optional[OrdersPersons] = None,
    ) -> Dict[str, List[Optional[Person]]|Optional[int]]:
        if page or page_size:
            assert page and page_size and page > 0 and page_size > 0, "Не корректное разделение на страницы, вывода данных!"
        if requester_user_privilege != PRIVILEGE_MAPPING["Admin"]:
            assert legal_entity_uuid, "Вы не можете просмотреть информацию о всех ФЛ!"
            le_check_access_response_object: Optional[Tuple[int, int, str]] = await LegalEntityQueryAndStatementManager.check_access(
                session=session,
                
                requester_user_uuid=requester_user_uuid,
                requester_user_privilege=requester_user_privilege,
                legal_entity_uuid=legal_entity_uuid,
            )
            assert le_check_access_response_object, "Вы не можете посмотреть информацию ФЛ других Пользователей!"
        
        persons: Dict[str, List[Optional[Person]]|Optional[int]] = await LegalEntityQueryAndStatementManager.get_persons(
            session=session,
            
            legal_entity_uuid=legal_entity_uuid,
            person_ids=person_ids,
            
            page=page,
            page_size=page_size,
            
            filter=filter,
            order=order,
        )
        
        return persons
    
    @staticmethod
    async def update_person(
        session: AsyncSession,
        
        requester_user_uuid: str,
        requester_user_privilege: int,
        
        person_id: int,
        
        surname: Optional[str],
        name: Optional[str],
        patronymic: Optional[str],
        gender: Optional[str],
        job_title: Optional[str],
        basic_action_signatory: Optional[str],
        power_of_attorney_number: Optional[str],
        power_of_attorney_date: Optional[str],
        email: Optional[str],
        phone: Optional[str],
        contact: Optional[str],
        legal_entity_uuid: Optional[str],
    ) -> str:  # возвращает uuid ЮЛ
        person: List[Optional[Person]] = await LegalEntityQueryAndStatementManager.get_persons(person_ids=[person_id])
        assert person, "Ошибка доступа к записи о ФЛ!"
        
        le_check_access_response_object: Optional[Tuple[int, int, str]] = await LegalEntityQueryAndStatementManager.check_access(
            session=session,
            
            requester_user_uuid=requester_user_uuid,
            requester_user_privilege=requester_user_privilege,
            legal_entity_uuid=person["data"][0].legal_entity_uuid,
            for_update_or_delete_legal_entity=True,
        )
        
        assert le_check_access_response_object, "Вы не можете обновить информацию ФЛ других Пользователей или же доступ к редактирования данного ЮЛ ограничен!" if requester_user_privilege != PRIVILEGE_MAPPING["Admin"] else f'Информация о ЮЛ с uuid "{person[0].legal_entity_uuid}" отсутствует или же доступ к редактирования данного ЮЛ ограничен!'
        assert list(
            filter(
                lambda x: x != "~",
                [
                    surname, name, patronymic, gender,
                    job_title,
                    basic_action_signatory, power_of_attorney_number, power_of_attorney_date,
                    email, phone, contact,
                    legal_entity_uuid,
                ]
            )
        ), "Хотя бы одно поле должно быть изменено для обновления данных о ФЛ!"
        await LegalEntityQueryAndStatementManager.update_person(
            session=session,
            
            person_id=person_id,
            
            surname=surname,
            name=name,
            patronymic=patronymic,
            gender=gender,
            job_title=job_title,
            basic_action_signatory=basic_action_signatory,
            power_of_attorney_number=power_of_attorney_number,
            power_of_attorney_date=datetime.datetime.strptime(power_of_attorney_date, "%d.%m.%Y").date() if power_of_attorney_date and power_of_attorney_date != "~" else None,
            email=email,
            phone=phone,
            contact=contact,
            legal_entity_uuid=legal_entity_uuid,
        )
        
        legal_entitie: List[List[Optional[Tuple[LegalEntity, bool]]]] = await LegalEntityQueryAndStatementManager.get_legal_entities(
            session=session,
            
            user_uuid=None,
            le_id_list=[le_check_access_response_object[0]],
        )
        
        return legal_entitie["data"][0][0].uuid
    
    @staticmethod
    async def delete_persons(
        session: AsyncSession,
        
        requester_user_uuid: str,
        requester_user_privilege: int,
        
        person_ids: List[int],
    ) -> Optional[str]:
        le_uuid_tuple = None
        assert person_ids, "Нужно указать хотя бы один ID ФЛ к удалению!"
        if requester_user_privilege != PRIVILEGE_MAPPING["Admin"]:
            persons: Dict[str, List[Optional[Person]]|Optional[int]] = await LegalEntityQueryAndStatementManager.get_persons(
                session=session,
                
                person_ids=person_ids,
            )
            
            le_uuid_tuple: Tuple[str:] = tuple(set([person.legal_entity_uuid for person in persons["data"]]))
            assert len(le_uuid_tuple) == 1, "Вы не можете удалять информацию о ФЛ других Пользователей!"
            le_check_access_response_object: Optional[Tuple[int, int, str]] = await LegalEntityQueryAndStatementManager.check_access(
                session=session,
                
                requester_user_uuid=requester_user_uuid,
                requester_user_privilege=requester_user_privilege,
                legal_entity_uuid=le_uuid_tuple[0],
                for_update_or_delete_legal_entity=True,
            )
            assert le_check_access_response_object, "Вы не можете удалять информацию о ФЛ других Пользователей или же доступ к редактирования данного ЮЛ ограничен!"
        
        await LegalEntityQueryAndStatementManager.delete_persons(
            session=session,
            
            person_ids=person_ids,
        )
        
        return le_uuid_tuple[0] if le_uuid_tuple else None
