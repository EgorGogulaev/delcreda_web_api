from typing import List, Literal, Optional
from pydantic import BaseModel, Field



class CreateNotificationDataSchema(BaseModel):
    data: str = Field(..., max_length=512)


# FILTERS
class FilterNotifications(BaseModel):
    field: Literal[
        "id", "uuid", "for_admin", "subject_id", "subject_uuid", "initiator_user_id", "initiator_user_uuid", "recipient_user_id", "recipient_user_uuid", "data", "is_read", "read_at", "is_important", "time_importance_change", "created_at",
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

class FiltersNotifications(BaseModel):
    filters: List[FilterNotifications] = Field(..., description="Массив фильтров-объектов.")

class OrderNotifications(BaseModel):
    field: Literal[
        "id", "uuid", "for_admin", "subject_id", "subject_uuid", "initiator_user_id", "initiator_user_uuid", "recipient_user_id", "recipient_user_uuid", "data", "is_read", "read_at", "is_important", "time_importance_change", "created_at",
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

class OrdersNotifications(BaseModel):
    orders: List[OrderNotifications] = Field(..., description="Массив объектов, описывающих сотировку.")

# RESPONSES
class NotificationData(BaseModel):
    uuid: str = Field(..., description="UUID уведомления.")
    for_admin: bool = Field(..., description="Является ли уведомление для администратора.")
    subject: Optional[str] = Field(None, description="Тип субъекта уведомления (Заявка/ЮЛ).")
    subject_uuid: Optional[str] = Field(None, description="UUID субъекта уведомления.")
    initiator_user_id: int = Field(..., description="ID инициатора уведомления.")
    initiator_user_uuid: str = Field(..., description="UUID инициатора уведомления.")
    recipient_user_id: Optional[int] = Field(None, description="ID получателя уведомления.")
    recipient_user_uuid: Optional[str] = Field(None, description="UUID получателя уведомления.")
    data: str = Field(..., description="Контент уведомления.")
    is_read: bool = Field(..., description="Прочитано ли уведомление.")
    read_at: Optional[str] = Field(None, description="Дата-время прочтения уведомления (Формат: 'dd.mm.YYYY HH:MM:SS UTC').")
    is_important: bool = Field(..., description="Уведомление важное? (true - да/false - нет).")
    time_importance_change: Optional[str] = Field(None, description="Дата-время переключения статуса важности уведомления на противоположный (Формат: 'dd.mm.YYYY HH:MM:SS UTC').")
    created_at: Optional[str] = Field(None, description="Дата-время создания уведомления (Формат: 'dd.mm.YYYY HH:MM:SS UTC').")

class ResponseGetNotifications(BaseModel):
    data: List[NotificationData] = Field([], description="Список уведомлений.")
    count: int = Field(0, description="Количество записей по текущей фильтрации (с учетом пагинации).")
    total_records: Optional[int] = Field(None, description="Всего записей (нужно для реализации пагинации в таблице).")
    total_pages: Optional[int] = Field(None, description="Всего страниц, с текущим размером страницы(page_size).")
