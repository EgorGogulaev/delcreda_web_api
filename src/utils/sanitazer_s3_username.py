import re
import unicodedata

def sanitize_s3_username(name: str) -> str:
    """
    Подготавливает имя для создания одноуровневой 'папки' в S3.
    Удаляет все слэши из исходного имени, заменяет небезопасные символы,
    нормализует Unicode и возвращает строку вида 'safe-name/'.
    """
    if not name or not name.strip():
        raise ValueError("Имя папки не может быть пустым или состоять только из пробелов")
    
    # 1. Удаляем все слэши — вложенность запрещена
    name = name.replace("/", "").replace("\\", "")
    
    # 2. Нормализуем Unicode (удаляем диакритику)
    name = unicodedata.normalize('NFD', name)
    name = ''.join(c for c in name if unicodedata.category(c) != 'Mn')
    
    # 3. Заменяем пробелы и табуляции на дефис
    name = re.sub(r'\s+', '-', name)
    
    # 4. Оставляем только безопасные символы (без слэшей!)
    name = re.sub(r"[^a-zA-Z0-9\-_.!()'*)]", "_", name)
    
    # 5. Убираем повторяющиеся подчёркивания/дефисы
    name = re.sub(r"_+", "_", name)
    name = re.sub(r"-+", "-", name)
    
    # 6. Убираем подчёркивания/дефисы в начале и конце
    name = name.strip("_.-")
    
    if not name:
        raise ValueError("Имя папки после очистки стало пустым")
    
    # 7. Добавляем завершающий слэш — обозначаем как 'папку'
    return name
