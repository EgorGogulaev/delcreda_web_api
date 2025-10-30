from typing import List, Optional
from pydantic import BaseModel, Field


class MessageData(BaseModel):
    user_id: int = Field(..., description="ID Пользователя, отправившего сообщение.")
    user_uuid: str = Field(..., description="UUID Пользователя, отправившего сообщение.")
    user_privilege: str = Field(..., description="Привелегии Пользователя.")
    chat_id: int = Field(..., description="ID чата")
    data: str = Field(..., description="Контент сообщения.")
    created_at: Optional[str] = Field(None, description="Дата-время создания сообщения (Формат: 'dd.mm.YYYY HH:MM:SS UTC').")

class ResponseGetMessages(BaseModel):
    data: List[Optional[MessageData]] = Field([], description="Массив сообщений.")
    count: int = Field(0, description="Количество записей по текущей фильтрации (с учетом пагинации).")
    total_records: Optional[int] = Field(None, description="Всего записей (нужно для реализации пагинации в таблице).")
    total_pages: Optional[int] = Field(None, description="Всего страниц, с текущим размером страницы(page_size).")
