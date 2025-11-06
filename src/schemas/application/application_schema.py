from typing import List, Literal, Optional
from pydantic import BaseModel, Field


# FILTERS
class FilterApplications(BaseModel):
    field: Literal[
        "id", "uuid", "name", "user_id", "user_uuid", "legal_entity_id", "legal_entity_uuid", "directory_id", "directory_uuid", "type", "status", "data_id", "created_at",
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

class FiltersApplications(BaseModel):
    filters: List[FilterApplications] = Field(..., description="Массив фильтров-объектов.")

class OrderApplications(BaseModel):
    field: Literal[
        "id", "uuid", "name", "user_id", "user_uuid", "legal_entity_id", "legal_entity_uuid", "directory_id", "directory_uuid", "type", "status", "data_id", "created_at",
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

class OrdersApplications(BaseModel):
    orders: List[OrderApplications] = Field(..., description="Массив объектов, описывающих сотировку.")

# RESPONSES
class BaseApplication(BaseModel):
    uuid: str = Field(..., description="UUID заявки.")
    name: str = Field(..., description="Человекочитаемое уникальное название заявки.")
    user_id: int = Field(..., description="ID пользователя.")
    user_uuid: str = Field(..., description="UUID пользователя.")
    legal_entity_id: int = Field(..., description="ID юридического лица.")
    legal_entity_uuid: str = Field(..., description="UUID юридического лица.")
    directory_id: int = Field(..., description="ID директории.")
    directory_uuid: str = Field(..., description="UUID директории.")
    type: Optional[int] = Field(..., description="Тип заявки (вид услуги).")
    status: Optional[str] = Field(None, description="Статус Заявки.")  # см. APPLICATION_STATUS_MAPPING
    data_id: Optional[int] = Field(None, description="ID подробных данных о Заявке.")
    can_be_updated_by_user: bool = Field(..., description="Может ли запись редактироваться Пользователем (true - да/false - нет).")
    updated_at: Optional[str] = Field(None, description="Дата-время последнего обновления основной информации о Заявке (Формат: 'dd.mm.YYYY HH:MM:SS TZ').")
    created_at: str = Field(..., description="Дата-время создания Заявки (Формат: 'dd.mm.YYYY HH:MM:SS TZ').")
