import datetime
from typing import List, Tuple

from config import ADMIN_LOGIN, ADMIN_PASSWORD, ADMIN_TOKEN as token, ADMIN_UUID


PRIVILEGE: List[Tuple] = [
    (1, "Admin", "Администратор web-приложения.", ),
    (2, "Сounterparty", "Контрагент (с кем есть договор)", ),
    (3, "Client", "Клиент (с кем еще нет договора, статус при регистрации)", ),
]

ADMIN: List[Tuple] = [
    (1, ADMIN_UUID, 1, ADMIN_LOGIN, ADMIN_PASSWORD, 1, True, None, "-", "-", None, datetime.datetime.now(tz=datetime.timezone.utc),),
]

ADMIN_DIRECTORY: List[Tuple] = [
    (
        1, ADMIN_UUID, None, "-", 1, 1, ADMIN_UUID, 1, ADMIN_UUID, True, None, None, None, False, None, None, None, datetime.datetime.now(tz=datetime.timezone.utc),
    )
]

ADMIN_TOKEN: List[Tuple] = [
    (1, token, True, datetime.datetime.now(tz=datetime.timezone.utc),),
]

SERVICE_NOTE_SUBJECT: List[Tuple] = [
    (1, "Заявка", "Служебная заметка связанная с Заявкой"),
    (2, "Контрагент", "Служебная заметка связанная с Контрагентом"),
    (3, "Документ", "Служебная заметка связанная с Документом"),
    (4, "Пользователь", "Служебная заметка связанная с Пользователем"),
    (5, "Заявка на КП", "Служебная заметка связанная с заявкой на КП"),
]
