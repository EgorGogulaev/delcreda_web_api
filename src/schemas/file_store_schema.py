from typing import List, Literal, Optional
from pydantic import BaseModel, Field



# FILTERS
class FilterUserFilesInfo(BaseModel):
    field: Literal[
        "id", "uuid", "name", "extansion", "size", "type", "directory_id", "directory_uuid", "path", "owner_user_id", "owner_user_uuid", "uploader_user_id", "uploader_user_uuid", "visible", "visibility_off_time", "visibility_off_user_id", "visibility_off_user_uuid", "is_deleted", "deleted_at", "deleters_user_id", "deleters_user_uuid", "created_at",
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

class FiltersUserFilesInfo(BaseModel):
    filters: List[FilterUserFilesInfo] = Field(..., description="Массив фильтров-объектов.")

class OrderUserFilesInfo(BaseModel):
    field: Literal[
        "id", "uuid", "name", "extansion", "size", "type", "directory_id", "directory_uuid", "path", "owner_user_id", "owner_user_uuid", "uploader_user_id", "uploader_user_uuid", "visible", "visibility_off_time", "visibility_off_user_id", "visibility_off_user_uuid", "is_deleted", "deleted_at", "deleters_user_id", "deleters_user_uuid", "created_at",
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

class OrdersUserFilesInfo(BaseModel):
    orders: List[OrderUserFilesInfo] = Field(..., description="Массив объектов, описывающих сотировку.")

class FilterUserDirsInfo(BaseModel):
    field: Literal[
        "id", "uuid", "parent", "path", "type", "owner_user_id", "owner_user_uuid", "uploader_user_id", "uploader_user_uuid", "visible", "visibility_off_time", "visibility_off_user_id", "visibility_off_user_uuid", "is_deleted", "deleted_at", "deleters_user_id", "deleters_user_uuid", "created_at",
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

class FiltersUserDirsInfo(BaseModel):
    filters: List[FilterUserDirsInfo] = Field(..., description="Массив фильтров-объектов.")

class OrderUserDirsInfo(BaseModel):
    field: Literal[
        "id", "uuid", "parent", "path", "type", "owner_user_id", "owner_user_uuid", "uploader_user_id", "uploader_user_uuid", "visible", "visibility_off_time", "visibility_off_user_id", "visibility_off_user_uuid", "is_deleted", "deleted_at", "deleters_user_id", "deleters_user_uuid", "created_at",
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

class OrdersUserDirsInfo(BaseModel):
    orders: List[OrderUserDirsInfo] = Field(..., description="Массив объектов, описывающих сотировку.")


# RESPONSES
# docs:
class FileInfoFromFS(BaseModel):
    path: Optional[str] = Field(None, description="Путь к файлу.")
    size: Optional[int] = Field(None, description="Размер файла в байтах.")
    last_modified: Optional[str] = Field(None, description="Время последней модификации файла (ISO-формат).")
    etag: Optional[str] = Field(None, description="Уникальный идентификатор в S3.")
    content_type: Optional[str] = Field(None, description="Тип файла.")
    msg: Optional[str] = Field(None, description="Поле появляется при отсутствии файла.")

class BaseFileInfo(BaseModel):
    uuid: str = Field(..., description="UUID файла.")
    name: str = Field(..., description="Имя файла.")
    extansion: Optional[str] = Field(None, description="Расширение файла.")
    type: Optional[int] = Field(None, description="Тип файла.")  # TODO тут должна быть строка
    directory_id: int = Field(..., description="ID директории.")
    directory_uuid: str = Field(..., description="UUID директории.")
    path: str = Field(..., description="Путь к файлу.")
    owner_user_id: Optional[int] = Field(None, description="ID владельца файла.")
    owner_user_uuid: Optional[str] = Field(None, description="UUID владельца файла.")
    uploader_user_id: int = Field(..., description="ID пользователя, загрузившего файл.")
    uploader_user_uuid: str = Field(..., description="UUID пользователя, загрузившего файл.")
    visible: bool = Field(..., description="Видимость файла.")
    is_deleted: bool = Field(..., description="Удален ли файл.")
    deleted_at: Optional[str] = Field(None, description="Дата-время удаления файла (Формат: 'dd.mm.YYYY HH:MM:SS UTC').")
    created_at: Optional[str] = Field(None, description="Дата-время создания записи о файле (Формат: 'dd.mm.YYYY HH:MM:SS UTC').")

class AdminFileInfo(BaseFileInfo):
    visibility_off_time: Optional[str] = Field(None, description="Дата-время выключения видимости.")
    visibility_off_user_id: Optional[int] = Field(None, description="ID пользователя, выключившего видимость.")
    visibility_off_user_uuid: Optional[str] = Field(None, description="UUID пользователя, выключившего видимость.")
    deleters_user_id: Optional[int] = Field(None, description="ID пользователя, удалившего файл.")
    deleters_user_uuid: Optional[str] = Field(None, description="UUID пользователя, удалившего файл.")

class ResponseGetUserFilesInfo(BaseModel):
    data_from_db: List[Optional[BaseFileInfo | AdminFileInfo]] = Field([], description="Информация о файлах из базы данных.")
    data_from_fs: List[Optional[FileInfoFromFS]] = Field([], description="Информация о файлах из файловой системы (только для админов).")
    count: int = Field(0, description="Количество записей по текущей фильтрации (с учетом пагинации)..")
    total_records: Optional[int] = Field(None, description="Общее количество записей.")
    total_pages: Optional[int] = Field(None, description="Общее количество страниц.")

# dirs:
class DirInfoFromFS(BaseModel):
    path: Optional[str] = Field(None, description="Путь к директории(префиксу).")
    files: Optional[List[Optional[str]]] = Field([], description="Массив названий файлов, находящихся по данному пути.")
    directories: Optional[List[Optional[str]]] = Field([], description="Массив директорий(префиксов), находящихся по данному пути.")
    msg: Optional[str] = Field(None, description="Поле появляется при отсутствии директории(префикса).")

class BaseDirInfo(BaseModel):
    uuid: str = Field(..., description="UUID директории.")
    parent: Optional[int] = Field(None, description="Родительская директория.")
    owner_user_id: Optional[int] = Field(None, description="ID владельца директории.")
    owner_user_uuid: Optional[str] = Field(None, description="UUID владельца директории.")
    uploader_user_id: int = Field(..., description="ID пользователя, создавшего директорию.")
    uploader_user_uuid: str = Field(..., description="UUID пользователя, создавшего директорию.")
    path: str = Field(..., description="Путь к директории.")
    type: Optional[int] = Field(None, description="Тип директории.")  # TODO тут должна быть строка
    visible: bool = Field(..., description="Видимость директории.")
    is_deleted: bool = Field(..., description="Удалена ли директория.")
    deleted_at: Optional[str] = Field(None, description="Дата удаления директории (Формат: 'dd.mm.YYYY HH:MM:SS UTC').")
    created_at: Optional[str] = Field(None, description="Дата-время создания записи о директории (Формат: 'dd.mm.YYYY HH:MM:SS UTC').")

class AdminDirInfo(BaseDirInfo):
    visibility_off_time: Optional[str] = Field(None, description="Время выключения видимости.")
    visibility_off_user_id: Optional[int] = Field(None, description="ID пользователя, выключившего видимость.")
    visibility_off_user_uuid: Optional[str] = Field(None, description="UUID пользователя, выключившего видимость.")
    deleters_user_id: Optional[int] = Field(None, description="ID пользователя, удалившего директорию.")
    deleters_user_uuid: Optional[str] = Field(None, description="UUID пользователя, удалившего директорию.")

class ResponseGetUserDirsInfo(BaseModel):
    data_from_db: List[Optional[BaseDirInfo | AdminDirInfo]] = Field([], description="Информация о директориях из базы данных.")
    data_from_fs: List[Optional[DirInfoFromFS]] = Field([], description="Информация о директориях из файловой системы (только для админов).")
    count: int = Field(0, description="Количество записей по текущей фильтрации (с учетом пагинации).")
    total_records: Optional[int] = Field(None, description="Общее количество записей.")
    total_pages: Optional[int] = Field(None, description="Общее количество страниц.")
