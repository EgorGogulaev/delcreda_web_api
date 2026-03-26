from typing import Dict


PRIVILEGE_MAPPING: Dict[str, int] = {
    "Admin": 1,
    "Сounterparty": 2,
    "Client": 3,
}

SERVICE_NOTE_SUBJECT_MAPPING: Dict[str, int] = {
    "Заявка": 1,
    "Контрагент": 2,
    "Документ": 3,
    "Пользователь": 4,
    "Заявка на КП": 5,
}

USER_GROUP_MAPPING: Dict[str, int] = {
    "SuperUser": 1,
}

INFORMATION_TYPE_MAPPING: Dict[str, int] = {
    "Counterparty":1,
    "Application": 2,
    "BankDetails": 3,
    "Directory": 4,
    "Chat": 5,
}
