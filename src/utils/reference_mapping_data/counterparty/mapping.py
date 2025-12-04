from typing import Dict, Literal


PersonGender: type = Literal["m", "w"]

COUNTERPARTY_TYPE_MAPPING: Dict[str, int] = {
    "ЮЛ": 1,
    "ФЛ": 2,
}

# ______________________________________________________________________
# BANK_PAYMENT_DETAILS_TYPE_MAPPING: Dict[str, int] = {
#     "Получатель": 1,
#     "Отправитель": 2,
# }

# BANK_PAYMENT_DETAILS_TYPE_FOR_KEYS: List[int] = list(range(1, 3))
# ______________________________________________________________________

# ______________________________________________________________________
# BANK_CODE_TYPE_MAPPING: Dict[str, int] = {
#     "SWIFT": 1,
#     "BIC": 2,
#     "CIPS": 3,
# }

# BANK_CODE_TYPE_FOR_KEYS: List[int] = list(range(1, 4))
# ______________________________________________________________________

# ______________________________________________________________________
# COUNTERPARTY_PERSON_ROLE_MAPPING: Dict[str, int] = {
#     "Подписант": 1,
#     "Администратор контракта": 2,
#     "Финансовый специалист": 3,
# }

# COUNTERPARTY_PERSON_ROLE_FOR_KEYS: List[int] = list(range(1, 4))
# ______________________________________________________________________

# ______________________________________________________________________
# BASIC_ACTION_SIGNATORY_MAPPING: Dict[str, int] = {
#     "Устав": 1,
#     "Доверенность": 2,
# }

# BASIC_ACTION_SIGNATORY_FOR_KEYS: List[int] = list(range(1, 3))
# ______________________________________________________________________
