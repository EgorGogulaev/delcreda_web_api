from typing import List, Literal, Optional
from pydantic import BaseModel, Field

class FilterCommercialProposals(BaseModel):
    field: Literal[
        "id", "uuid", "appliaction_name", "commercial_proposal_name", "type", "user_id", "user_uuid", "counterparty_id", "counterparty_uuid", "application_id", "application_uuid", "directory_id", "directory_uuid", "document_uuid", "status", "can_be_updated_by_user", "updated_at", "created_at",
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


class FiltersCommercialProposals(BaseModel):
    filters: List[FilterCommercialProposals] = Field(..., description="Массив фильтров-объектов.")

class OrderCommercialProposals(BaseModel):
    field: Literal[
        "id", "uuid", "appliaction_name", "commercial_proposal_name", "type", "user_id", "user_uuid", "counterparty_id", "counterparty_uuid", "application_id", "application_uuid", "directory_id", "directory_uuid", "document_uuid", "status", "can_be_updated_by_user", "updated_at", "created_at",
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

class OrdersCommercialProposals(BaseModel):
    orders: List[OrderCommercialProposals] = Field(..., description="Массив объектов, описывающих сотировку.")

class CommercialProposal(BaseModel):
    uuid: str = Field(..., description="UUID заявки на КП.")
    appliaction_name: str = Field(..., description="Название зявки на КП в БД web-приложения.")
    commercial_proposal_name: Optional[str] = Field(None, description="Наименование документа КП(из ERP).")
    type: int = Field(..., description="Тип заявки на КП.")
    user_id: int = Field(..., description="ID целевого Пользователя.")
    user_uuid: str = Field(..., description="UUID целевого Пользователя.")
    counterparty_id: int = Field(..., description="ID карточки Контрагента к которому будет прикреплена заявка на КП.")
    counterparty_uuid: str = Field(..., description="UUID карточки Контрагента к которому будет прикреплена заявка на КП.")
    application_id: Optional[int] = Field(None, description="ID Заявки на ПР (если заявка на КП будет прекреплена к Заявке на ПР).")
    application_uuid: Optional[str] = Field(None, description="UUID Заявки на ПР (если заявка на КП будет прекреплена к Заявке на ПР).")
    directory_id: int = Field(..., description="ID Директории для Документов по данной заявке на КП.")
    directory_uuid: str = Field(..., description="UUID Директории для Документов по данной заявке на КП.")
    document_uuid: Optional[str] = Field(None, description="UUID Документа КП.")
    status: int = Field(..., description="ID статуса КП")
    can_be_updated_by_user: bool = Field(..., description="Может ли запись редактироваться Пользователем? (true - да/false - нет)")
    updated_at: Optional[str] = Field(None, description="Дата-время последнего обновления заявки по КП (Формат: 'dd.mm.YYYY HH:MM:SS UTC').")
    created_at: Optional[str] = Field(None, description="Дата-время создания записи (Формат: 'dd.mm.YYYY HH:MM:SS UTC').")

class ResponseGetCommercialProposals(BaseModel):
    data: List[Optional[CommercialProposal]] = Field([], description="Массив заявок на КП.")
    count: int = Field(0, description="Количество записей по текущей фильтрации (с учетом пагинации).")
    total_records: Optional[int] = Field(None, description="Всего записей (нужно для реализации пагинации в таблице).")
    total_pages: Optional[int] = Field(None, description="Всего страниц, с текущим размером страницы(page_size).")
