from typing import Dict, List, Literal, Optional
from pydantic import BaseModel, Field


class UserSchema(BaseModel):
    user_id: Optional[int] = Field(None, description="ID пользователя.")
    user_uuid: Optional[str] = Field(None, description="UUID пользователя.")
    user_dir_uuid: Optional[str] = Field(None, description="UUID Директории пользователя.")
    privilege_id: Optional[int] = Field(None, description="ID Прав пользователя.")

class AuthData(BaseModel):
    login: str = Field(..., description="Логин пользователя.", min_length=4, max_length=255)
    password: str = Field(..., description="Пароль пользователя.", min_length=8, max_length=255)


# FILTERS
class FilterUsersInfo(BaseModel):
    field: Literal[
        "id", "uuid", "login", "password", "privilege", "is_active", "last_auth", "created_at",
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

class FiltersUsersInfo(BaseModel):
    filters: List[FilterUsersInfo] = Field(..., description="Массив фильтров-объектов.")

class OrderUsersInfo(BaseModel):
    field: Literal[
        "id", "uuid", "token", "login", "password", "privilege", "is_active", "last_auth", "created_at",
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

class OrdersUsersInfo(BaseModel):
    orders: List[OrderUsersInfo] = Field(..., description="Массив объектов, описывающих сотировку.")

# RESPONSES
# auth
class ResponseAuth(BaseModel):
    token: str = Field(..., description="Идентифицирующий токен.")
    user_id: int = Field(..., description="ID пользователя в системе.")
    user_uuid: str = Field(..., description="UUID пользователя в системе.")
    user_dir_uuid: str = Field(..., description="UUID Директории пользователя.")
    privilege: str = Field(..., description="Права пользователя.")

# user info
class UserInfo(BaseModel):
    uuid: str = Field(..., description="UUID-пользователя.")
    token: str = Field(..., description="ТОКЕН пользователя.")
    login: str = Field(..., description="ЛОГИН пользователя")
    password: str = Field(..., description="ПАРОЛЬ пользователя.")
    privilege: str = Field(..., description="ПРАВА пользователя.")
    is_active: bool = Field(..., description="СТАТУС АКТИВНОСТИ(возможности использовать сервис) пользователя.")
    contact_id: int = Field(..., description="Идентификатор в БД контактной информации(техническое поле, не для вывода).")
    s3_login: str = Field(..., description="ЛОГИН пользователя в S3.")
    s3_password: str = Field(..., description="ПАРОЛЬ пользователя в S3.")
    email: Optional[str] = Field(None, description="Email-адрес пользователя.")
    email_notification: bool = Field(..., description="Email используется для получения пользователем уведомлений? (True-да/False-нет)")
    telegram: Optional[str] = Field(..., description="Имя пользователя в telegram.")
    telegram_notification: bool = Field(None, description="Telegram используется для получения пользователем уведомлений? (True-да/False-нет)")
    last_auth: Optional[str] = Field(None, description="Дата-время последней авторизации пользователя (Формат: 'dd.mm.YYYY HH:MM:SS UTC').")
    created_at: Optional[str] = Field(None, description="Дата-время создания пользователя (Формат: 'dd.mm.YYYY HH:MM:SS UTC').")


class ResponseGetUsersInfo(BaseModel):
    data: List[Optional[UserInfo]] = Field([], description="Массив данных Пользователей.")
    count: int = Field(0, description="Количество записей по текущей фильтрации (с учетом пагинации).")
    total_records: Optional[int] = Field(None, description="Всего записей (нужно для реализации пагинации в таблице).")
    total_pages: Optional[int] = Field(None, description="Всего страниц, с текущим размером страницы(page_size).")

class ClientState(BaseModel):
    data: Dict = Field({}, description="Данные состояния.")
    ttl: Optional[int] = Field(None, description="Время жизни (В ответе: |TTL| -1 => нет TTL; -2 => ключ не существует).")

class UpdateUserContactData(BaseModel):
    new_email: Optional[str] = Field("~", description="Новый email-адрес.")
    email_notification: str|bool = Field("~", description="Пользователь хочет получать уведомления на email-адрес? (True-да/False-нет)")
    
    new_telegram: Optional[str] = Field("~", description="Новое имя пользователя telegram (@durov).")
    telegram_notification: str|bool = Field("~", description="Пользователь хочет получать уведомления в telegram(требуется подписка на бота - @delcreda_notifications_bot)? (True-да/False-нет)")

class ConfirmationV2Data(BaseModel):
    new_password: Optional[str] = Field(None, description="Новый пароль")
