from typing import List, Literal, Optional
from pydantic import BaseModel, Field


class FilterContracts(BaseModel):
    field: Literal[
        "id", "uuid", "name", "type", "user_id", "user_uuid", "counterparty_id", "counterparty_uuid", "application_id", "application_uuid", "file_uuid", "start_date" "expiration_date" "updated_at", "created_at",
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


class FiltersContracts(BaseModel):
    filters: List[FilterContracts] = Field(..., description="Массив фильтров-объектов.")

class OrderContracts(BaseModel):
    field: Literal[
        "id", "uuid", "name", "type", "user_id", "user_uuid", "counterparty_id", "counterparty_uuid", "application_id", "application_uuid", "file_uuid", "start_date" "expiration_date" "updated_at", "created_at",
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

class OrdersContracts(BaseModel):
    orders: List[OrderContracts] = Field(..., description="Массив объектов, описывающих сотировку.")

class Contract(BaseModel):
    uuid: str = Field(..., description="UUID карточки Договора.")
    name: str = Field(..., description="Название Договора.")
    type: int = Field(..., description="Тип Договора.")
    user_id: int = Field(..., description="ID целевого Пользователя.")
    user_uuid: str = Field(..., description="UUID целевого Пользователя.")
    counterparty_id: int = Field(..., description="ID карточки Контрагента к которому будет прикреплен Договор (если не указана Заявка на ПР).")
    counterparty_uuid: str = Field(..., description="UUID карточки Контрагента к которому будет прикреплен Договор (если не указана Заявка на ПР).")
    application_id: Optional[int] = Field(None, description="ID Заявки на ПР (если Договор будет прекреплен к Заявке на ПР).")
    application_uuid: Optional[str] = Field(None, description="UUID Заявки на ПР (если Договор будет прекреплен к Заявке на ПР).")
    file_uuid: Optional[str] = Field(None, description="UUID Документа - для карточки Договора.")
    start_date: Optional[str] = Field(None, description="Дата начала действия Договора. (Формат: 'dd.mm.YYYY')")
    expiration_date: Optional[str] = Field(None, description="Дата окончания действия Договора. (Формат: 'dd.mm.YYYY')")
    updated_at: Optional[str] = Field(None, description="Дата-время последнего обновления карточки Договора (Формат: 'dd.mm.YYYY HH:MM:SS UTC').")
    created_at: Optional[str] = Field(None, description="Дата-время создания записи (Формат: 'dd.mm.YYYY HH:MM:SS UTC').")

class ResponseGetContracts(BaseModel):
    data: List[Optional[Contract]] = Field([], description="Массив заявок на КП.")
    count: int = Field(0, description="Количество записей по текущей фильтрации (с учетом пагинации).")
    total_records: Optional[int] = Field(None, description="Всего записей (нужно для реализации пагинации в таблице).")
    total_pages: Optional[int] = Field(None, description="Всего страниц, с текущим размером страницы(page_size).")
