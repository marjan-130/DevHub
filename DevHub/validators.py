import re
from tkinter import messagebox

def validate_sql_name(name):
    """Перевірка безпеки назв таблиць та колонок"""
    if not name or name.strip() == "":
        return False, "Назва не може бути порожньою!"
    
    # Регулярний вираз: латиниця, цифри, підкреслення
    if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', name):
        return False, "Назва має починатися з літери та не містити спецсимволів."
    
    if len(name) > 30:
        return False, "Назва занадто довга (макс. 30 символів)."
    
    reserved = ["SELECT", "TABLE", "CREATE", "DROP", "ALTER", "INSERT", "USER", "UPDATE", "DELETE"]
    if name.upper() in reserved:
        return False, f"'{name}' — зарезервоване слово SQL."
    return True, ""

def confirm_save_action(action_name):
    """Універсальне вікно для підтвердження дій"""
    return messagebox.askyesno(
        "Підтвердження дії", 
        f"Ви впевнені, що хочете {action_name}?\nЦю дію буде зафіксовано в системі."
    )

def can_add_primary_key(existing_columns):
    """Перевірка, чи вже є PK в таблиці"""
    for _, col_type in existing_columns:
        if "PRIMARY KEY" in col_type.upper():
            return False, "У таблиці вже є Primary Key. Він може бути тільки один!"
    return True, ""

def validate_foreign_key_match(from_col_type, to_col_type):
    """Перевірка відповідності типів для зв'язку"""
    # Беремо тільки перше слово (напр. з 'INTEGER PRIMARY KEY' беремо 'INTEGER')
    type1 = from_col_type.split()[0].upper()
    type2 = to_col_type.split()[0].upper()
    
    if type1 != type2:
        return False, f"Типи не збігаються: {type1} та {type2}."
    return True, ""

def check_unsaved_changes(is_dirty):
    """Попередження про незбережені зміни"""
    if is_dirty:
        return messagebox.askyesno(
            "Незбережені зміни", 
            "У вас є незбережені зміни. Ви впевнені, що хочете продовжити без збереження?"
        )
    return True