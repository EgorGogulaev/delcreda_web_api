import datetime
from typing import Any, Dict, List, Literal, Optional, Tuple

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from connection_module import SignalConnector
from src.query_and_statement.commercial_proposal_qas_manager import CommercialProposalQueryAndStatementManager
from src.service.application.application_service import ApplicationService
from src.models.application.application_models import Application
from src.service.application.mt_application_service import MTApplicationService
from src.schemas.counterparty.counterparty_schema import CreateIndividualDataSchema, CreateLegalEntityDataSchema, FiltersCounterparties, FiltersPersons, OrdersCounterparties, OrdersPersons, CreatePersonsSchema, UpdateCounterpartySchema, UpdateIndividualDataSchema, UpdateLegalEntityDataSchema
from src.service.chat_service import ChatService
from src.service.file_store_service import FileStoreService
from src.models.counterparty.counterparty_models import Counterparty, IndividualData, LegalEntityData, Person
from src.query_and_statement.counterparty.counterparty_qas_manager import CounterpartyQueryAndStatementManager
from src.query_and_statement.user_qas_manager import UserQueryAndStatementManager
from src.utils.reference_mapping_data.user.mapping import PRIVILEGE_MAPPING
from src.utils.reference_mapping_data.file_store.mapping import DIRECTORY_TYPE_MAPPING
from src.utils.reference_mapping_data.app.app_mapping_data import COUNTRY_MAPPING


class CounterpartyService:
    @classmethod
    async def create_counterparty(
        cls,
        session: AsyncSession,
        
        counterparty_type: Literal["ЮЛ", "ФЛ"],
        
        requester_user_uuid: str,
        requester_user_privilege: int,
        
        owner_user_uuid: str,
        new_directory_uuid: Optional[str],
        
        country: int,
        identifier_type: str,
        identifier_value: str,
        tax_identifier: str,
        
        # LegalEntityData|IndividualData
        counterparty_data: CreateLegalEntityDataSchema|CreateIndividualDataSchema,
    ) -> Tuple[Tuple[Counterparty, LegalEntityData], Dict[str, int|str]]:
        if requester_user_privilege != PRIVILEGE_MAPPING["Admin"]:
            if requester_user_uuid != owner_user_uuid:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Вы не можете создать карточку Контрагента для другого Пользователя!")
        
        if counterparty_type == "ЮЛ":
            if not counterparty_data.name_latin and not counterparty_data.name_national:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Не указано наименование Контрагента!")
            if not counterparty_data.organizational_and_legal_form_latin and not counterparty_data.organizational_and_legal_form_national:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Не указана организационно-правовая форма Контрагента!")
        else:
            ...  # TODO тут должна быть предусмотрена логика создания ФЛ
        
        owner_user_id: int = await UserQueryAndStatementManager.get_user_id_by_uuid(
            session=session,
            
            uuid=owner_user_uuid,
        )
        owner_s3_login: Optional[str] = await UserQueryAndStatementManager.get_user_s3_login(
            session=session,
            
            user_id=owner_user_id,
        )
        if not owner_s3_login:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="У пользователя отсутствует логин в S3!")
        
        user_dirs: Dict[str, Any] = await FileStoreService.get_dir_info_from_db(
            session=session,
            
            requester_user_uuid=requester_user_uuid,
            requester_user_privilege=requester_user_privilege,
            owner_user_uuid=owner_user_uuid,
            visible=True,
        )
        if not user_dirs["count"]:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Не найдена ни одна директория по указанным данным Пользователя!")
        
        parent_directory_uuid = None
        for dir_id in user_dirs["data"]:
            if user_dirs["data"][dir_id]["type"] == DIRECTORY_TYPE_MAPPING["Пользовательская директория"]:
                parent_directory_uuid = user_dirs["data"][dir_id]["uuid"]
        if not parent_directory_uuid:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="У Пользователя нет пользовательской Директории!") 
        
        new_counterparty_dir_data: Dict[str, Any] = await FileStoreService.create_directory(
            session=session,
            
            requester_user_uuid=requester_user_uuid,
            requester_user_privilege=requester_user_privilege,
            owner_s3_login=owner_s3_login,
            owner_user_uuid=owner_user_uuid,
            directory_type=DIRECTORY_TYPE_MAPPING["Директория контрагента"],
            new_directory_uuid=new_directory_uuid,
            parent_directory_uuid=parent_directory_uuid,
        )
        
        new_application_access_list_id: int = await cls.__create_application_access_list(
            session=session,
        )
        new_counter_party_with_data = None
        if counterparty_type == "ЮЛ":
            new_uuid_coro = await SignalConnector.generate_identifiers(target="ЮЛ", count=1)
            new_uuid = new_uuid_coro[0]
            
            new_le_with_data: Tuple[Counterparty, LegalEntityData] = await CounterpartyQueryAndStatementManager.create_counterparty(
                session=session,
                
                counterparty_type=counterparty_type,
                
                owner_user_id=owner_user_id,
                owner_user_uuid=owner_user_uuid,
                new_counterparty_uuid=new_uuid,
                directory_id=new_counterparty_dir_data["id"],
                directory_uuid=new_counterparty_dir_data["uuid"],
                application_access_list_id=new_application_access_list_id,
                
                country=country,
                identifier_type=identifier_type,
                identifier_value=identifier_value,
                tax_identifier=tax_identifier,
                
                # CounterpartyData
                counterparty_data=counterparty_data,
            )
            new_counter_party_with_data = new_le_with_data
        else:
            ...  # TODO предусмотреть uuid для ФЛ
        
        
        
        new_chat = await ChatService.create_chat(
            session=session,
            
            chat_subject="Контрагент",
            subject_uuid=new_uuid,
        )
        
        return new_counter_party_with_data, new_chat
    
    @staticmethod
    async def __create_application_access_list(
        session: AsyncSession,
    ) -> int:
        new_application_access_list_id: int = await CounterpartyQueryAndStatementManager.create_application_access_list(
            session=session
        )
        
        return new_application_access_list_id
    
    @staticmethod
    async def get_counterparties(
        session: AsyncSession,
        
        requester_user_uuid: str,
        requester_user_privilege: int,
        
        counterparty_type: Optional[Literal["ЮЛ", "ФЛ"]],
        user_uuid: Optional[str],
        legal_entity_name_ilike: Optional[str] = None,
        
        extended_output: bool = False,
        
        page: Optional[int] = None,
        page_size: Optional[int] = None,
        
        filter: Optional[FiltersCounterparties] = None,
        order: Optional[OrdersCounterparties] = None,
    ) -> Dict[str, List[Optional[Counterparty|int|bool]] | List[Optional[Tuple[Counterparty, bool]]]]:
        if page or page_size:
            if (isinstance(page, int) and page <= 0) or (isinstance(page_size, int) and page_size <= 0):
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Не корректное разделение на страницы, запрошенных данных!")
        if extended_output is False:
            if legal_entity_name_ilike:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Можно искать по названию компании только при расширенном выводе (extended_output=true)!")
        if requester_user_privilege != PRIVILEGE_MAPPING["Admin"]:
            if not user_uuid:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Вы не можете просмотреть все карточки Контрагентов - всех пользователей!")
            if user_uuid != requester_user_uuid:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Вы не можете просмотреть карточки Контрагентов других пользователей!")
        
        counterparties: Dict[str, List[Optional[Counterparty|int|bool]] | List[Optional[Tuple[Counterparty, bool]]]] = await CounterpartyQueryAndStatementManager.get_counterparties(
            session=session,
            
            counterparty_type=counterparty_type,
            user_uuid=user_uuid,
            legal_entity_name_ilike=legal_entity_name_ilike,
            
            extended_output=extended_output,
            
            page=page,
            page_size=page_size,
            
            filter=filter,
            order=order,
        )
        
        return counterparties
    
    @staticmethod
    async def update_counterparty(
        session: AsyncSession,
        
        requester_user_uuid: str,
        requester_user_privilege: int,
        
        counterparty_uuid: str,
        
        data_for_update: UpdateCounterpartySchema,
    ) -> None:
        counterparty_check_access_response_object: Optional[Tuple[int, int, int, str]] = await CounterpartyQueryAndStatementManager.check_access(
            session=session,
            
            requester_user_uuid=requester_user_uuid,
            requester_user_privilege=requester_user_privilege,
            counterparty_uuid=counterparty_uuid,
            for_update_or_delete_counterparty=True,
        )
        if counterparty_check_access_response_object is None:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Вы не можете обновлять карточки Контрагентов других Пользователей или же доступ редактирования данной карточки Контрагента ограничен!")
        
        
        if all(field == "~" for field in [
                data_for_update.country,
                data_for_update.identifier_type, data_for_update.identifier_value,
                data_for_update.tax_identifier,
                data_for_update.is_active,
            ]
        ):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Хотя бы одно поле должно быть изменено для обновления данных в карточке Контрагента!")
        
        await CounterpartyQueryAndStatementManager.update_counterparty(
            session=session,
            
            counterparty_id=counterparty_check_access_response_object[0],
            
            data_for_update=data_for_update,
        )
    
    @staticmethod
    async def change_counterparties_edit_status(
        session: AsyncSession,
        
        requester_user_uuid: str,
        requester_user_privilege: int,
        
        counterparty_uuids: List[str],
        edit_status: bool,
    ) -> None:
        if requester_user_privilege != PRIVILEGE_MAPPING["Admin"]:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="У Вас недостаточно прав для изменения статуса возможности редактирования информации о Контрагенте!")
        if not counterparty_uuids:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Должен быть указан UUID, хотя бы одного Контрагента!")
        if not isinstance(edit_status, bool):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Статус должен быть булевым значением!")
        
        await CounterpartyQueryAndStatementManager.change_counterparties_edit_status(
            session=session,
            
            counterparty_uuids=counterparty_uuids,
            edit_status=edit_status,
        )
    
    @staticmethod
    async def update_application_access_list(
        session: AsyncSession,
        
        requester_user_privilege: int,
        
        counterparty_uuid: str,
        
        mt: str|bool,
        # TODO тут будут иные бизнес процессы
    ) -> None:
        if requester_user_privilege != PRIVILEGE_MAPPING["Admin"]:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="У Вас недостаточно прав для изменения списка доступных типов Заявок!")
        application_type_dict: Dict[str, str|bool] = {
            "MT": mt,
            # TODO тут будут иные бизнес процессы
        }
        
        if all([application_type_dict[o_t] == "~" for o_t in application_type_dict]):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Для изменения списка доступных типов Заявок, нужно указать хотя бы одно значение к изменению!")
        
        application_access_list_id: Optional[int] = await CounterpartyQueryAndStatementManager.get_application_access_list_id_by_counterparty_uuid(
            session=session,
            counterparty_uuid=counterparty_uuid,
        )
        if application_access_list_id is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Список доступных типов Заявок не был найден!")
        
        await CounterpartyQueryAndStatementManager.update_application_access_list(
            session=session,
            application_access_list_id=application_access_list_id,
            application_type_dict=application_type_dict,
        )
    
    @staticmethod
    async def get_counterparties_data(
        session: AsyncSession,
        
        counterparty_type: Literal["ЮЛ", "ФЛ"],
        
        requester_user_uuid: str,
        requester_user_privilege: int,
        
        counterparty_uuid_list: List[Optional[str]],
        user_uuid: Optional[str],
    ) -> List[Optional[LegalEntityData|IndividualData]]:
        if requester_user_privilege != PRIVILEGE_MAPPING["Admin"]:
            if not user_uuid:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Вы не можете просмотреть все данные карточек Контрагентов - всех пользователей!")
            if user_uuid != requester_user_uuid:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Вы не можете просмотреть данные карточек Контрагента других пользователей!")
        
        counterparty_data_ids: List[Optional[int]] = []
        for counterparty_uuid in tuple(set(counterparty_uuid_list)):
            counterparty_check_access_response_object: Optional[Tuple[int, int, int, str]] = await CounterpartyQueryAndStatementManager.check_access(
                session=session,
                
                requester_user_uuid=user_uuid,
                requester_user_privilege=requester_user_privilege,
                counterparty_uuid=counterparty_uuid,
            )
            if counterparty_check_access_response_object is None:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f'Вы не являетесь владельцем карточки Контрагента с UUID "{counterparty_uuid}"!')
            
            counterparty_data_ids.append(counterparty_check_access_response_object[2])
        
        if requester_user_privilege != PRIVILEGE_MAPPING["Admin"] and not counterparty_data_ids:
            return []
        
        counterparties_data: List[Optional[LegalEntityData]] = await CounterpartyQueryAndStatementManager.get_counterparties_data(
            session=session,
            
            counterparty_type=counterparty_type,
            counterparty_data_ids=counterparty_data_ids,
        )
        
        return counterparties_data
    
    @staticmethod
    async def update_counterparty_data(
        session: AsyncSession,
        
        requester_user_uuid: str,
        requester_user_privilege: int,
        
        counterparty_uuid: str,
        
        data_for_update: UpdateLegalEntityDataSchema | UpdateIndividualDataSchema,
    ) -> None:
        counterparty_check_access_response_object: Optional[Tuple[int, int, int, str]] = await CounterpartyQueryAndStatementManager.check_access(
            session=session,
            
            requester_user_uuid=requester_user_uuid,
            requester_user_privilege=requester_user_privilege,
            counterparty_uuid=counterparty_uuid,
            for_update_or_delete_counterparty=True,
        )
        if counterparty_check_access_response_object is None:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Вы не можете обновлять карточку Контрагента других Пользователей или же доступ редактирования данного Контрагента ограничен!")
        
        if isinstance(data_for_update, UpdateLegalEntityDataSchema):
            if all(field == "~" for field in [
                    data_for_update.name_latin, data_for_update.name_national,
                    data_for_update.organizational_and_legal_form_latin, data_for_update.organizational_and_legal_form_national,
                    data_for_update.site,
                    data_for_update.registration_date,
                    data_for_update.legal_address, data_for_update.postal_address, data_for_update.additional_address,
                ]
            ):
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Хотя бы одно поле должно быть изменено для обновления данных Контрагента!")
        else:
            ...  # TODO тут будет логика для ФЛ
        
        await CounterpartyQueryAndStatementManager.update_counterparty_data(
            session=session,
            
            counterparty_data_id=counterparty_check_access_response_object[2],
            
            data_for_update=data_for_update,
        )
    
    @classmethod
    async def delete_counterparties(  # TODO нужно предусмотреть удаление ЧАТОВ и СМС!!!
        cls,
        session: AsyncSession,
        
        requester_user_id: int,
        requester_user_uuid: str,
        requester_user_privilege: int,
        
        counterparty_uuids: List[str],
    ) -> None:
        if not counterparty_uuids:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Для удаления карточек Контрагента, нужно указать хотя бы 1 UUID!")
        
        # if requester_user_privilege != PRIVILEGE_MAPPING["Admin"]:
            # raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Вы не можете удалять карточки Контрагента. Недостаточно прав!")
        
        counterparty_ids_with_counterparty_type_ids_with_counterparty_data_ids_with_dir_uuid: List[Tuple[int, int, int, str]] = [] # type: ignore
        application_uuids: List[str] = []
        applications_access_lists_ids: List[int] = []
        for counterparty_uuid in counterparty_uuids:
            counterparty_check_access_response_object: Optional[Tuple[int, int, int, str]] = await CounterpartyQueryAndStatementManager.check_access(
                session=session,
                
                requester_user_uuid=requester_user_uuid,
                requester_user_privilege=requester_user_privilege,
                counterparty_uuid=counterparty_uuid,
                for_update_or_delete_counterparty=True,
            )
            if counterparty_check_access_response_object is None:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Вы не можете удалять информацию карточек Контрагента других Пользователей или же доступ к редактирования Контрагента ограничен!")
            
            counterparty_ids_with_counterparty_type_ids_with_counterparty_data_ids_with_dir_uuid.append(counterparty_check_access_response_object)
            
            application_access_list_id: Optional[int] = await CounterpartyQueryAndStatementManager.get_application_access_list_id_by_counterparty_uuid(
                session=session,
                counterparty_uuid=counterparty_uuid,
            )
            if application_access_list_id is not None:
                applications_access_lists_ids.append(application_access_list_id)
            
            counterparty_applications: Dict[str, List[Optional[Application]]|Optional[int]] = await MTApplicationService.get_applications(
                session=session,
                
                requester_user_uuid=requester_user_uuid,
                requester_user_privilege=requester_user_privilege,
                user_uuid=requester_user_uuid if requester_user_privilege != PRIVILEGE_MAPPING["Admin"] else None,
                counterparty_uuid=counterparty_uuid,
            )
            for application in counterparty_applications["data"]:
                if application and application.uuid:
                    application_uuids.append(application.uuid)
        
        for _, _, _, dir_uuid in counterparty_ids_with_counterparty_type_ids_with_counterparty_data_ids_with_dir_uuid:
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
            await ApplicationService.delete_applications(
                session=session,
                
                requester_user_id=requester_user_id,
                requester_user_uuid=requester_user_uuid,
                requester_user_privilege=requester_user_privilege,
                
                applications_uuids=application_uuids,
            )
        except: ...  # noqa: E722
        await cls.__delete_applications_access_lists(
            session=session,
            applications_access_lists_ids=applications_access_lists_ids,
        )
        
        await CommercialProposalQueryAndStatementManager.delete_commercial_proposals(
            session=session,
            
            counterparty_uuid=counterparty_uuid,
        )
        
        await CounterpartyQueryAndStatementManager.delete_counterparties(
            session=session,
            
            counterparty_uuids=counterparty_uuids,
            counterparty_ids_with_counterparty_type_ids_with_counterparty_data_ids_with_dir_uuid=counterparty_ids_with_counterparty_type_ids_with_counterparty_data_ids_with_dir_uuid,
        )
    
    @staticmethod
    async def __delete_applications_access_lists(
        session: AsyncSession,
        
        applications_access_lists_ids: List[int],
    ) -> None:
        await CounterpartyQueryAndStatementManager.delete_applications_access_lists(
            session=session,
            applications_access_lists_ids=applications_access_lists_ids,
        )
    
    @staticmethod
    async def create_persons(
        session: AsyncSession,
        
        requester_user_uuid: str,
        requester_user_privilege: int,
        
        new_persons: CreatePersonsSchema,
    ) -> List[int]:
        if requester_user_privilege != PRIVILEGE_MAPPING["Admin"]:
            counterparty_uuid_tuple = tuple(set([new_person.counterparty_uuid for new_person in new_persons.new_persons]))
            if len(counterparty_uuid_tuple) != 1:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Вы не можете добавлять информацию ФЛ к карточке Контрагента других Пользователей или к нескольким карточкам Контрагента одновременно!")
            
            counterparty_check_access_response_object: Optional[Tuple[int, int, int, str]] = await CounterpartyQueryAndStatementManager.check_access(
                session=session,
                
                requester_user_uuid=requester_user_uuid,
                requester_user_privilege=requester_user_privilege,
                counterparty_uuid=counterparty_uuid_tuple[0],
            )
            if counterparty_check_access_response_object is None:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Вы не можете добавлять информацию ФЛ к карточкам Контрагента других Пользователей или же доступ к редактирования данного Контрагента ограничен!")
        
        new_person_ids: List[int] = await CounterpartyQueryAndStatementManager.create_persons(
            session=session,
            
            new_persons=new_persons,
        )
        
        return new_person_ids
    
    @staticmethod
    async def get_persons(
        session: AsyncSession,
        
        requester_user_uuid: str,
        requester_user_privilege: int,
        
        counterparty_uuid: Optional[str],
        person_ids: Optional[List[int]] = None,
        
        page: Optional[int] = None,
        page_size: Optional[int] = None,
        
        filter: Optional[FiltersPersons] = None,
        order: Optional[OrdersPersons] = None,
    ) -> Dict[str, List[Optional[Person]]|Optional[int]]:
        if page or page_size:
            if (isinstance(page, int) and page <= 0) or (isinstance(page_size, int) and page_size <= 0):
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Не корректное разделение на страницы, запрошенных данных!")
        if requester_user_privilege != PRIVILEGE_MAPPING["Admin"]:
            if not counterparty_uuid:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Вы не можете просмотреть информацию о всех ФЛ!")
            
            counterparty_check_access_response_object: Optional[Tuple[int, int, int, str]] = await CounterpartyQueryAndStatementManager.check_access(
                session=session,
                
                requester_user_uuid=requester_user_uuid,
                requester_user_privilege=requester_user_privilege,
                counterparty_uuid=counterparty_uuid,
            )
            if counterparty_check_access_response_object is None:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Вы не можете посмотреть информацию ФЛ других Пользователей!")
        
        persons: Dict[str, List[Optional[Person]]|Optional[int]] = await CounterpartyQueryAndStatementManager.get_persons(
            session=session,
            
            counterparty_uuid=counterparty_uuid,
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
        counterparty_uuid: Optional[str],
    ) -> str:  # возвращает UUID-Контрагента
        person: List[Optional[Person]] = await CounterpartyQueryAndStatementManager.get_persons(
            session=session,
            
            person_ids=[person_id],
        )
        if not person:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="ФЛ с указанным ID не был найден!")
        
        counterparty_check_access_response_object: Optional[Tuple[int, int, int, str]] = await CounterpartyQueryAndStatementManager.check_access(
            session=session,
            
            requester_user_uuid=requester_user_uuid,
            requester_user_privilege=requester_user_privilege,
            counterparty_uuid=person["data"][0].counterparty_uuid,
            for_update_or_delete_counterparty=True,
        )
        if counterparty_check_access_response_object is None:
            if requester_user_privilege != PRIVILEGE_MAPPING["Admin"]:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Вы не можете обновить информацию ФЛ других Пользователей или же доступ к редактированию данного Контрагента ограничен!")
            else:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f'Информация о Контрагенте с UUID "{person[0].counterparty_uuid}" отсутствует или же доступ к редактирования данного Контрагента ограничен!')
        
        if all(field == "~" for field in [
                surname, name, patronymic, gender,
                job_title,
                basic_action_signatory, power_of_attorney_number, power_of_attorney_date,
                email, phone, contact,
                counterparty_uuid,
            ]
        ):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Хотя бы одно поле должно быть изменено для обновления данных о ФЛ!")
        
        await CounterpartyQueryAndStatementManager.update_person(
            session=session,
            
            person_id=person_id,
            
            surname=surname,
            name=name,
            patronymic=patronymic,
            gender=gender,
            job_title=job_title,
            basic_action_signatory=basic_action_signatory,
            power_of_attorney_number=power_of_attorney_number,
            power_of_attorney_date=datetime.datetime.strptime(power_of_attorney_date, "%d.%m.%Y").date() if power_of_attorney_date and power_of_attorney_date != "~" else "~" if power_of_attorney_date == "~" else None,
            email=email,
            phone=phone,
            contact=contact,
            counterparty_uuid=counterparty_uuid,
        )
        
        counterparty: List[List[Optional[Tuple[Counterparty, bool]]]] = await CounterpartyQueryAndStatementManager.get_counterparties(  
            session=session,
            
            counterparty_type="ЮЛ", # TODO (это нужно исправить (унифицировать)!)
            
            user_uuid=None,
            counterparty_id_list=[counterparty_check_access_response_object[0]],
        )
        
        return counterparty["data"][0][0].uuid
    
    @staticmethod
    async def delete_persons(
        session: AsyncSession,
        
        requester_user_uuid: str,
        requester_user_privilege: int,
        
        person_ids: List[int],
    ) -> Optional[str]:
        counterparty_uuid_tuple = None
        if not person_ids:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Нужно указать хотя бы один ID ФЛ к удалению!")
        
        if requester_user_privilege != PRIVILEGE_MAPPING["Admin"]:
            persons: Dict[str, List[Optional[Person]]|Optional[int]] = await CounterpartyQueryAndStatementManager.get_persons(
                session=session,
                
                person_ids=person_ids,
            )
            
            counterparty_uuid_tuple: Tuple[str:] = tuple(set([person.counterparty_uuid for person in persons["data"]]))
            if len(counterparty_uuid_tuple) != 1:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Вы не можете удалять информацию о ФЛ других Пользователей!")
            
            counterparty_check_access_response_object: Optional[Tuple[int, int, int, str]] = await CounterpartyQueryAndStatementManager.check_access(
                session=session,
                
                requester_user_uuid=requester_user_uuid,
                requester_user_privilege=requester_user_privilege,
                counterparty_uuid=counterparty_uuid_tuple[0],
                for_update_or_delete_counterparty=True,
            )
            if counterparty_check_access_response_object is None:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Вы не можете удалять информацию о ФЛ других Пользователей или же доступ к редактированию данного Контрагента ограничен!")
        
        await CounterpartyQueryAndStatementManager.delete_persons(
            session=session,
            
            person_ids=person_ids,
        )
        
        return counterparty_uuid_tuple[0] if counterparty_uuid_tuple else None
