import datetime
from typing import Optional

import pytz


TIMEZONES = {
    None: 'UTC',
    
    # СНГ
    'Moscow': 'Europe/Moscow',
    'Yekaterinburg': 'Asia/Yekaterinburg',
    'Novosibirsk': 'Asia/Novosibirsk',
    'Vladivostok': 'Asia/Vladivostok',
    'Kaliningrad': 'Europe/Kaliningrad',
    'Almaty': 'Asia/Almaty',
    'Ulaanbaatar': 'Asia/Ulaanbaatar',
    'Tashkent': 'Asia/Tashkent',
    
    # Китай
    'Shanghai': 'Asia/Shanghai',
    'Hong_Kong': 'Asia/Hong_Kong',
    
    # Европа
    'Berlin': 'Europe/Berlin',
    'Paris': 'Europe/Paris',
    'London': 'Europe/London',
}

TIMEZONES_RU_ALIAS = {
    'UTC': None,
    
    # СНГ
    'Москва': 'Moscow',
    'Екатеринбург': 'Yekaterinburg',
    'Новосибирск': 'Novosibirsk',
    'Владивосток': 'Vladivostok',
    'Калининград': 'Kaliningrad',
    'Алматы': 'Almaty', 'Казахстан': 'Almaty',
    'Улан-Батор': 'Ulaanbaatar', 'Монголия': 'Ulaanbaatar',
    'Ташкент': 'Tashkent', 'Узбекистан': 'Tashkent',
    
    # Китай
    'Шанхай': 'Shanghai',
    'Гонконг': 'Hong_Kong',
    
    # Европа
    'Берлин': 'Berlin',
    'Париж': 'Paris',
    'Лондон': 'London',
}

def __get_timezone(key: Optional[str]) -> str:
    if key in TIMEZONES:
        return TIMEZONES[key]
    
    if key in TIMEZONES_RU_ALIAS:
        en_key = TIMEZONES_RU_ALIAS[key]
        return TIMEZONES[en_key]
    
    return TIMEZONES[None]

def convert_tz(
    utc_time_str: str,
    tz_city: Optional[str] = None,
) -> str:
    tz: str = __get_timezone(tz_city)
    if tz_city is None:
        return utc_time_str
    try:
        dt_utc = datetime.datetime.strptime(utc_time_str, "%d.%m.%Y %H:%M:%S UTC")
        utc_timezone = pytz.timezone('UTC')
        dt_utc = utc_timezone.localize(dt_utc)
        
        target_tz = pytz.timezone(tz)
        dt_target = dt_utc.astimezone(target_tz)
        
        return dt_target.strftime("%d.%m.%Y %H:%M:%S %Z")
    except Exception as e:
        return f"Ошибка: {e}"
