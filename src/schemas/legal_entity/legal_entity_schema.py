from typing import List, Literal, Optional, Union
from pydantic import BaseModel, Field

from src.utils.reference_mapping_data.legal_entity.mapping import LegalEntityPersonRole, PersonGender
from src.utils.reference_mapping_data.app.app_mapping_data import COUNTRY_MAPPING


RegistrationIdentifierType: type = Literal["OGRN"]


class CreateLegalEntityDataSchema(BaseModel):
    name_latin: Optional[str] = Field(None, description="Наименование латиницей.")
    name_national: Optional[str] = Field(None, description="Наименование в национальном написании.")
    organizational_and_legal_form_latin: Optional[str] = Field(None, description="ОПФ латиницей.")
    organizational_and_legal_form_national: Optional[str] = Field(None, description="ОПФ в национальном написании.")
    site: Optional[str] = Field(None, description="Сайт ЮЛ.")
    registration_date: str = Field(..., description="Дата регистрации ЮЛ (Формат: 'dd.mm.YYYY').")
    legal_address: str = Field(..., description="Юридический адрес.")
    postal_address: Optional[str] = Field(None, description="Почтовый адрес.")
    additional_address: Optional[str] = Field(None, description="Дополнительный адрес.")

class UpdateLegalEntitySchema(BaseModel):
    country: Literal[*COUNTRY_MAPPING, "~"] = Field("~", description="Страна регистрации ЮЛ. (значение '~' == оставить без изменений)") # type: ignore
    registration_identifier_type: str = Field("~", description="Тип регистрационного идентификатора ЮЛ. (значение '~' == оставить без изменений)")
    registration_identifier_value: str = Field("~", description="Значение регистрационного идентификатора ЮЛ. (значение '~' == оставить без изменений)")
    tax_identifier: str = Field("~", description="Значение налогового идентификатора ЮЛ. (значение '~' == оставить без изменений)")
    is_active: bool|str = Field("~", description="Флаг возможности создания Заявки по данному ЮЛ (true-можно/false-нельзя). (значение '~' == оставить без изменений)")

class UpdateLegalEntityDataSchema(BaseModel):
    name_latin: Optional[str] = Field("~", description="Наименование латиницей. (значение '~' == оставить без изменений)")
    name_national: Optional[str] = Field("~", description="Наименование в национальном написании. (значение '~' == оставить без изменений)")
    organizational_and_legal_form_latin: Optional[str] = Field("~", description="ОПФ латиницей. (значение '~' == оставить без изменений)")
    organizational_and_legal_form_national: Optional[str] = Field("~", description="ОПФ в национальном написании. (значение '~' == оставить без изменений)")
    site: Optional[str] = Field("~", description="Сайт ЮЛ. (значение '~' == оставить без изменений)")
    registration_date: Optional[str] = Field("~", description="Дата регистрации ЮЛ (Формат: 'dd.mm.YYYY'). (значение '~' == оставить без изменений)")
    legal_address: Optional[str] = Field("~", description="Юридический адрес. (значение '~' == оставить без изменений)")
    postal_address: Optional[str] = Field("~", description="Почтовый адрес. (значение '~' == оставить без изменений)")
    additional_address: Optional[str] = Field("~", description="Дополнительный адрес. (значение '~' == оставить без изменений)")

class UpdateApplicationAccessList(BaseModel):
    mt: str|bool = Field("~", description="Доступ к переводам денежных средств (MT). (значение '~' == оставить без изменений)")
    # TODO ... тут будут иные бизнес направления

class CreatePersonSchema(BaseModel):
    surname: str = Field(..., description="Фамилия.")
    name: str = Field(..., description="Имя.")
    patronymic: str = Field(..., description="Отчество.")
    gender: PersonGender = Field(..., description="Пол ('m'/'w').") # type: ignore
    job_title: str = Field(..., description="Должность.")
    basic_action_signatory: str = Field(..., description="Роль ФЛ ('На основании чего ФЛ является подписантом').")
    power_of_attorney_number: Optional[str] = Field(None, description="(Если есть доверенность) Номер доверенности.")
    power_of_attorney_date: Optional[str] = Field(None, description="(Если есть доверенность) Дата доверенности (Формат: 'dd.mm.YYYY').")
    email: str = Field(..., description="E-mail")
    phone: str = Field(..., description="Телефон.")
    contact: Optional[str] = Field(None, description="Номер контракта.")
    legal_entity_uuid: str = Field(..., description="UUID ЮЛ, к которому будет привязано ФЛ.")

class CreatePersonsSchema(BaseModel):
    new_persons: List[CreatePersonSchema] = Field(..., description="Массив информаций ФЛ.")

class UpdatePerson(BaseModel):
    surname: Optional[str] = Field("~", description="Фамилия. (значение '~' == оставить без изменений)")
    name: Optional[str] = Field("~", description="Имя. (значение '~' == оставить без изменений)")
    patronymic: Optional[str] = Field("~", description="Отчество. (значение '~' == оставить без изменений)")
    gender: Optional[str] = Field("~", description="Пол ('m'/'w'). (значение '~' == оставить без изменений)")
    job_title: Optional[str] = Field("~", description="Должность. (значение '~' == оставить без изменений)")
    basic_action_signatory: Optional[str] = Field("~", description="Роль ФЛ ('Подписант'/'Администратор контракта'/'Финансовый специалист'). (значение '~' == оставить без изменений)")
    power_of_attorney_number: Optional[str] = Field("~", description="(Если есть доверенность) Номер доверенности. (значение '~' == оставить без изменений)")
    power_of_attorney_date: Optional[str] = Field("~", description="(Если есть доверенность) Дата доверенности (Формат: 'dd.mm.YYYY'). (значение '~' == оставить без изменений)")
    email: Optional[str] = Field("~", description="E-mail. (значение '~' == оставить без изменений)")
    phone: Optional[str] = Field("~", description="Телефон. (значение '~' == оставить без изменений)")
    contact: Optional[str] = Field("~", description="Номер контракта. (значение '~' == оставить без изменений)")
    legal_entity_uuid: str = Field("~", description="UUID ЮЛ, к которому будет привязано ФЛ. (значение '~' == оставить без изменений)")


# FILTERS
class FilterLegalEntities(BaseModel):
    field: Literal[
        "id", "uuid", "country", "registration_identifier_type", "registration_identifier_value", "tax_identifier", "user_id", "user_uuid", "directory_id", "directory_uuid", "is_active", "data_id", "updated_at", "created_at",
    ] = Field(..., description="Поля доступные для фильтрации.")
    operator: Literal["eq", "ne", "gt", "lt", "ge", "le", "like", "in"] = Field(
        ...,
        description="""
        Операторы сравнения для фильтрации:
        - eq (equal) — равно (=)  
        - ne (not equal) — не равно (!=)  
        - gt (greater than) — больше (>)  
        - lt (less than) — меньше (<)  
        - ge (greater or equal) — больше или равно (>=)  
        - le (less or equal) — меньше или равно (<=)  
        - like — поиск по части строки (аналог LIKE в SQL)  
        - in — проверка вхождения в список (значение должно быть строкой с элементами, разделёнными запятыми, например "1,2,3")  
        """
    )
    value: Optional[str|bool|int|float] = Field(..., description="Значения для логических операций фильтра.")

class FiltersLegalEntities(BaseModel):
    filters: List[FilterLegalEntities] = Field(..., description="Массив фильтров-объектов.")

class OrderLegalEntities(BaseModel):
    field: Literal[
        "id", "uuid", "country", "registration_identifier_type", "registration_identifier_value", "tax_identifier", "user_id", "user_uuid", "directory_id", "directory_uuid", "is_active", "data_id", "updated_at", "created_at",
    ] = Field(
        ...,
        description="Поля по которым можно сортировать записи."
    )
    direction: Literal["asc", "desc"] = Field(
        ...,
        description="""
        Направление сортировки:
        - asc (ascending) — по возрастанию (от меньшего к большему, A→Z)
        - desc (descending) — по убыванию (от большего к меньшему, Z→A)
        """
    )

class OrdersLegalEntities(BaseModel):
    orders: List[OrderLegalEntities] = Field(..., description="Массив объектов, описывающих сотировку.")


class FilterPersons(BaseModel):
    field: Literal[
        "id", "surname", "name", "patronymic", "gender", "job_title", "basic_action_signatory", "power_of_attorney_number", "power_of_attorney_date", "email", "phone", "contact", "legal_entity_uuid", "updated_at", "created_at",
    ] = Field(..., description="Поля доступные для фильтрации.")
    operator: Literal["eq", "ne", "gt", "lt", "ge", "le", "like", "in"] = Field(
        ...,
        description="""
        Операторы сравнения для фильтрации:
        - eq (equal) — равно (=)  
        - ne (not equal) — не равно (!=)  
        - gt (greater than) — больше (>)  
        - lt (less than) — меньше (<)  
        - ge (greater or equal) — больше или равно (>=)  
        - le (less or equal) — меньше или равно (<=)  
        - like — поиск по части строки (аналог LIKE в SQL)  
        - in — проверка вхождения в список (значение должно быть строкой с элементами, разделёнными запятыми, например "1,2,3")  
        """
    )
    value: Optional[str|bool|int|float] = Field(..., description="Значения для логических операций фильтра.")

class FiltersPersons(BaseModel):
    filters: List[FilterPersons] = Field(..., description="Массив фильтров-объектов.")

class OrderPersons(BaseModel):
    field: Literal[
        "id", "surname", "name", "patronymic", "gender", "job_title", "basic_action_signatory", "power_of_attorney_number", "power_of_attorney_date", "email", "phone", "contact", "legal_entity_uuid", "updated_at", "created_at",
    ] = Field(
        ...,
        description="Поля по которым можно сортировать записи."
    )
    direction: Literal["asc", "desc"] = Field(
        ...,
        description="""
        Направление сортировки:
        - asc (ascending) — по возрастанию (от меньшего к большему, A→Z)
        - desc (descending) — по убыванию (от большего к меньшему, Z→A)
        """
    )

class OrdersPersons(BaseModel):
    orders: List[OrderPersons] = Field(..., description="Массив объектов, описывающих сотировку.")


# RESPONSES
# legal entity
class BaseLegalEntity(BaseModel):
    uuid: str = Field(..., description="UUID юридического лица.")
    country: str = Field(..., description="Страна юридического лица.")
    registration_identifier_type: Optional[str] = Field(None, description="Тип регистрационного идентификатора.")
    registration_identifier_value: str = Field(..., description="Значение регистрационного идентификатора.")
    tax_identifier: str = Field(..., description="Налоговый идентификатор.")
    user_id: int = Field(..., description="ID связанного пользователя.")
    user_uuid: str = Field(..., description="UUID связанного пользователя.")
    directory_id: int = Field(..., description="ID директории.")
    directory_uuid: str = Field(..., description="UUID директории.")
    data_id: Optional[int] = Field(None, description="ID подробных данных о ЮЛ.")
    can_be_updated_by_user: bool = Field(..., description="Может ли запись редактироваться Пользователем? (true - да/false - нет)")
    mt: bool = Field(..., description="Может ли Пользователь по данному ЮЛ выполнять Заявки по переводу денежных средств? (true - да/false - нет)")
    application_access_list: int = Field(..., description="ID перечня доступных услуг для данного ЮЛ.")
    is_active: bool = Field(..., description="Активно ли юридическое лицо.")
    updated_at: Optional[str] = Field(None, description="Дата-время последнего обновления основной информации о ЮЛ (Формат: 'dd.mm.YYYY HH:MM:SS UTC').")
    created_at: Optional[str] = Field(None, description="Дата-время создания записи (Формат: 'dd.mm.YYYY HH:MM:SS UTC').")

class ExtendedLegalEntity(BaseLegalEntity):
    name_latin: Optional[str] = Field(None, description="Название на латинице.")
    name_national: Optional[str] = Field(None, description="Название на национальном языке.")
    organizational_and_legal_form_latin: Optional[str] = Field(None, description="Организационно-правовая форма на латинице.")
    organizational_and_legal_form_national: Optional[str] = Field(None, description="Организационно-правовая форма на национальном языке.")
    data_updated_at: Optional[str] = Field(None, description="Дата-время последнего обновления данных ЮЛ (Формат: 'dd.mm.YYYY HH:MM:SS UTC').")

class ResponseGetLegalEntities(BaseModel):
    data: List[Optional[Union[BaseLegalEntity, ExtendedLegalEntity]]] = Field([], description="Массив ЮЛ.")
    count: int = Field(0, description="Количество записей по текущей фильтрации (с учетом пагинации).")
    total_records: Optional[int] = Field(None, description="Всего записей (нужно для реализации пагинации в таблице).")
    total_pages: Optional[int] = Field(None, description="Всего страниц, с текущим размером страницы(page_size).")

# person
class PersonData(BaseModel):
    id: int = Field(..., description="ID физического лица.")
    surname: Optional[str] = Field(None, description="Фамилия.")
    name: Optional[str] = Field(None, description="Имя.")
    patronymic: Optional[str] = Field(None, description="Отчество.")
    gender: Optional[str] = Field(None, description="Пол.")
    job_title: Optional[str] = Field(None, description="Должность.")
    basic_action_signatory: Optional[str] = Field(None, description="Основание по которому ФЛ выступает подписантом ('Устав'/'Доверенность').")
    power_of_attorney_number: Optional[str] = Field(None, description="Номер доверенности.")
    power_of_attorney_date: Optional[str] = Field(None, description="Дата доверенности (Формат: 'dd.mm.YYYY').")
    email: Optional[str] = Field(None, description="Email.")
    phone: Optional[str] = Field(None, description="Телефон.")
    contact: Optional[str] = Field(None, description="Контактная информация.")
    legal_entity_uuid: str = Field(..., description="UUID связанного юридического лица.")
    updated_at: Optional[str] = Field(None, description="Дата последнего обновления (Формат: 'dd.mm.YYYY HH:MM:SS UTC').")
    created_at: Optional[str] = Field(None, description="Дата создания записи (Формат: 'dd.mm.YYYY HH:MM:SS UTC').")

class ResponseGetPersons(BaseModel):
    data: List[Optional[PersonData]] = Field([], description="Список физических лиц.")
    count: int = Field(0, description="Количество записей по текущей фильтрации (с учетом пагинации).")
    total_records: Optional[int] = Field(None, description="Всего записей (нужно для реализации пагинации в таблице).")
    total_pages: Optional[int] = Field(None, description="Всего страниц, с текущим размером страницы(page_size).")
