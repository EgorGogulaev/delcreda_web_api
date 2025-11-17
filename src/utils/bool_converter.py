from typing import Optional


def bool_converter(v: Optional[bool|str]) -> Optional[bool|str]:
    if isinstance(v, bool) or v is None or v == "~":
        return v
    elif isinstance(v, str):
        if v in ("true", "True", "Да", "да", "Yes", "yes"):
            return True
        elif v in ("false", "False", "Нет", "нет", "No", "no"):
            return False
    
    raise ValueError(f"Не валидное значение для конвертации в bool - {v}")
