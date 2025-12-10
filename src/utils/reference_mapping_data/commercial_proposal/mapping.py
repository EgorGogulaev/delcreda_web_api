from typing import Dict


COMMERCIAL_PROPOSAL_TYPE_MAPPING: Dict[str, int] = {
    "MT": 1,
    # TODO
}
# (, Согласовано, Отклонено, Закрыто администратором(не дает Пользователю делать update)) - Админ
COMMERCIAL_PROPOSAL_STATUS_MAPPING: Dict[str, int] = {
    "На рассмотрении сторон": 1,
    "Согласовано": 2,
    "Отклонено": 3,
    "Закрыто администратором": 4,
}
