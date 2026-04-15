import re
from tkinter import messagebox

def validate_sql_name(name):
    """
    Перевіряє безпеку назв таблиць та колонок для уникнення SQL-ін'єкцій
    та синтаксичних помилок. Відкидає спецсимволи та зарезервовані слова.
    """
    if not name or name.strip() == "":
        return False, "Назва не може бути порожньою!"
    
    # Дозволяємо лише латиницю, цифри та підкреслення
    if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', name):
        return False, "Назва має починатися з літери та не містити спецсимволів."
    
    if len(name) > 30:
        return False, "Назва занадто довга (макс. 30 символів)."
    
    # Перевірка на зарезервовані слова SQL
    reserved = ["SELECT", "TABLE", "CREATE", "DROP", "ALTER", "INSERT", "USER", "UPDATE", "DELETE", "FROM", "WHERE"]
    if name.upper() in reserved:
        return False, f"'{name}' — зарезервоване слово SQL."
        
    return True, ""

def validate_foreign_key_match(from_col_type, to_col_type):
    """
    Перевіряє відповідність типів даних при створенні зовнішнього ключа (Foreign Key).
    Інтелектуально відсікає розміри та атрибути, наприклад:
    'VARCHAR(64) PRIMARY KEY' порівнюватиметься з 'VARCHAR(128)' просто як 'VARCHAR'.
    """
    # Відкидаємо дужки і беремо перше слово
    type1 = from_col_type.split('(')[0].split()[0].upper()
    type2 = to_col_type.split('(')[0].split()[0].upper()
    
    if type1 != type2:
        return False, f"Типи не збігаються: {type1} та {type2}."
    return True, ""

def validate_email_format(email):
    """
    Базова перевірка формату електронної пошти для реєстрації (наявність @ та крапки).
    """
    if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
        return False
    return True

def validate_url_format(url):
    """
    Перевірка валідності посилання для роботи API-клієнта.
    """
    if not url.startswith(("http://", "https://")):
        return False
    return True

def confirm_save_action(action_name):
    """
    Універсальне системне вікно для підтвердження критичних дій (створення/видалення).
    """
    return messagebox.askyesno(
        "Підтвердження дії", 
        f"Ви впевнені, що хочете {action_name}?\nЦю дію буде зафіксовано в системі."
    )

def check_unsaved_changes(is_dirty):
    """
    Попередження про наявність незбережених змін перед виходом або відкриттям нового проєкту.
    """
    if is_dirty:
        return messagebox.askyesno(
            "Незбережені зміни", 
            "У вас є незбережені зміни. Ви впевнені, що хочете продовжити без збереження?"
        )
    return True

def can_add_primary_key(existing_columns):
    """
    Перевірка, чи вже є Primary Key в таблиці.
    (Залишено для зворотної сумісності, оскільки тепер PK генерується автоматично).
    """
    # Очікуємо 3 параметри: ім'я, тип, опис
    for _, col_type, _ in existing_columns:
        if "PRIMARY KEY" in col_type.upper():
            return False, "У таблиці вже є Primary Key. Він може бути тільки один!"
    return True, ""