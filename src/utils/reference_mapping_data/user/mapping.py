from typing import Dict


PRIVILEGE_MAPPING: Dict[str, int] = {
    "Admin": 1,
    "User": 2,
    "Intermediary": 3,
}

SERVICE_NOTE_SUBJECT_MAPPING: Dict[str, int] = {
    "Поручение": 1,
    "ЮЛ": 2,
    "Документ": 3,
    "Пользователь": 4,
}
