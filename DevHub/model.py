import psycopg2
from psycopg2 import sql
import hashlib
import uuid
import json
import random    
import string       
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Завантажуємо змінні з .env для хмарного підключення до Neon
load_dotenv()

class BaseModel:
    """Базовий клас для налаштування підключення до PostgreSQL (Local Docker або Neon Cloud) та створення таблиць."""
    def __init__(self):
        """Ініціалізує параметри підключення та запускає перевірку/створення бази даних. DATABASE_URL має пріоритет."""
        self.db_url = os.getenv("DATABASE_URL")
        
        # Фолбек на локальні налаштування Docker, якщо хмарний URL відсутній
        if not self.db_url:
            self.db_url = "dbname=devhub user=admin password=mysecretpassword host=localhost port=5432"
            
        self._init_db()

    def _get_connection(self):
        """Повертає активне з'єднання з базою даних."""
        return psycopg2.connect(self.db_url)

    def _init_db(self):
        """Створює всі необхідні таблиці (користувачі, проєкти, канвас тощо), якщо їх ще немає. Також створює адміна за замовчуванням."""
        queries = [
            """CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                login VARCHAR(100) UNIQUE NOT NULL,
                email VARCHAR(100) UNIQUE NOT NULL,
                password_hash VARCHAR(255) NOT NULL
            )""",
            """CREATE TABLE IF NOT EXISTS projects (
                id SERIAL PRIMARY KEY,
                user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
                project_name VARCHAR(255) NOT NULL,
                json_data TEXT, 
                last_opened TIMESTAMP
            )""",
            """CREATE TABLE IF NOT EXISTS canvas_elements (
                uuid VARCHAR(50) PRIMARY KEY,
                name VARCHAR(100),
                x REAL,
                y REAL
            )""",
            """CREATE TABLE IF NOT EXISTS table_columns (
                id SERIAL PRIMARY KEY,
                table_uuid VARCHAR(50) REFERENCES canvas_elements(uuid) ON DELETE CASCADE,
                column_name VARCHAR(100),
                column_type VARCHAR(50),
                description TEXT
            )""",
            """CREATE TABLE IF NOT EXISTS table_relations (
                id SERIAL PRIMARY KEY,
                from_uuid VARCHAR(50) REFERENCES canvas_elements(uuid) ON DELETE CASCADE,
                from_col VARCHAR(100),
                to_uuid VARCHAR(50) REFERENCES canvas_elements(uuid) ON DELETE CASCADE,
                to_col VARCHAR(100)
            )""",
            """CREATE TABLE IF NOT EXISTS api_logs (
                id SERIAL PRIMARY KEY,
                url TEXT,
                status INTEGER,
                timestamp TIMESTAMP
            )"""
        ]
        
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                for q in queries:
                    cur.execute(q)
                
                # Створення базового адміністратора
                cur.execute("SELECT id FROM users WHERE login=%s", ("admin",))
                if not cur.fetchone():
                    pwd_hash = hashlib.sha256("admin123".encode()).hexdigest()
                    cur.execute("INSERT INTO users (login, email, password_hash) VALUES (%s, %s, %s)", 
                                 ("admin", "admin@devhub.com", pwd_hash))
            conn.commit()

    def _sanitize_name(self, name):
        """Очищає назви (таблиць, полів) від спецсимволів, залишаючи лише букви, цифри та підкреслення."""
        return ''.join(c if c.isalnum() or c == '_' else '_' for c in name)

    def _validate_type(self, col_type):
        """Перевіряє, чи підтримується вказаний SQL тип даних. Також пропускає типи з розміром, як VARCHAR(64)."""
        allowed_types = ["TEXT", "INTEGER", "REAL", "VARCHAR", "DATETIME", "TIMESTAMP", "BOOLEAN"]
        base_type = col_type.upper().split('(')[0].split()[0]
        if base_type in allowed_types:
            return col_type
        return "TEXT"


class AuthService(BaseModel):
    """Сервіс для автентифікації та реєстрації користувачів."""
    def authenticate(self, login_or_email, password):
        """Перевіряє логін/email та пароль. Повертає ID користувача у разі успіху, або None."""
        pwd_hash = hashlib.sha256(password.encode()).hexdigest()
        query = "SELECT id FROM users WHERE (login = %s OR email = %s) AND password_hash = %s"
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, (login_or_email, login_or_email, pwd_hash))
                res = cur.fetchone()
                return res[0] if res else None

    def register(self, login, email, password):
        """Створює нового користувача. Повертає True, якщо успішно, і False, якщо користувач вже існує."""
        pwd_hash = hashlib.sha256(password.encode()).hexdigest()
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("INSERT INTO users (login, email, password_hash) VALUES (%s, %s, %s)", 
                                 (login, email, pwd_hash))
                conn.commit()
            return True
        except Exception:
            return False 

    def check_email_exists(self, email):
        """Перевіряє, чи є такий email в базі даних"""
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT id FROM users WHERE email = %s", (email,))
                return cur.fetchone() is not None

    def update_password(self, email, new_password):
        """Хешує та оновлює пароль для користувача"""
        pwd_hash = hashlib.sha256(new_password.encode()).hexdigest()
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("UPDATE users SET password_hash = %s WHERE email = %s", (pwd_hash, email))
            conn.commit()


class ProjectService(BaseModel):
    """Сервіс для керування проєктами (збереження, завантаження, видалення, перейменування)."""
    def get_user_projects(self, user_id, search_term=""):
        """Повертає список проєктів конкретного користувача, фільтруючи за назвою (пошук)."""
        query = """SELECT id, project_name, last_opened FROM projects 
                   WHERE user_id = %s AND project_name ILIKE %s 
                   ORDER BY project_name ASC"""
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, (user_id, f"%{search_term}%"))
                return cur.fetchall()

    def delete_project(self, project_id):
        """Видаляє проєкт користувача з бази даних за його ID."""
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM projects WHERE id = %s", (project_id,))
            conn.commit()

    def rename_project(self, project_id, new_name):
        """Перейменовує існуючий проєкт у базі даних."""
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("UPDATE projects SET project_name = %s WHERE id = %s", (new_name, project_id))
            conn.commit()

    def save_project_to_db(self, user_id, project_name, canvas_data, project_id=None):
        """Зберігає стан канвасу у форматі JSON. Якщо project_id передано - оновлює існуючий, інакше - створює новий."""
        json_str = json.dumps(canvas_data)
        now = datetime.now()
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                if project_id:
                    cur.execute("UPDATE projects SET json_data = %s, last_opened = %s WHERE id = %s RETURNING id", 
                                 (json_str, now, project_id))
                else:
                    cur.execute("INSERT INTO projects (user_id, project_name, json_data, last_opened) VALUES (%s, %s, %s, %s) RETURNING id", 
                                 (user_id, project_name, json_str, now))
                res = cur.fetchone()
                conn.commit()
                return res[0] if res else project_id

    def load_project_from_db(self, project_id):
        """Завантажує збережений JSON-стан проєкту з бази."""
        query = "SELECT json_data FROM projects WHERE id = %s"
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, (project_id,))
                res = cur.fetchone()
                return json.loads(res[0]) if res else None


class ArchitectService(BaseModel):
    """Сервіс для керування архітектурою бази даних (таблицями, колонками, зв'язками)."""
    def add_new_element(self, name, x=50, y=50):
        """Створює нову таблицю на канвасі та генерує для неї унікальний UUID."""
        unique_id = str(uuid.uuid4())
        name = self._sanitize_name(name)
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("INSERT INTO canvas_elements (uuid, name, x, y) VALUES (%s, %s, %s, %s)", (unique_id, name, x, y))
            conn.commit()
        return unique_id

    def update_element_pos(self, uuid, x, y):
        """Оновлює координати таблиці на канвасі після її перетягування."""
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("UPDATE canvas_elements SET x = %s, y = %s WHERE uuid = %s", (x, y, uuid))
            conn.commit()

    def delete_element(self, table_uuid):
        """Видаляє таблицю та всі її колонки з бази даних."""
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM table_columns WHERE table_uuid = %s", (table_uuid,))
                cur.execute("DELETE FROM canvas_elements WHERE uuid = %s", (table_uuid,))
            conn.commit()

    def get_all_elements(self):
        """Отримує всі таблиці (їх UUID, назви та координати) для поточного проєкту."""
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT uuid, name, x, y FROM canvas_elements")
                return cur.fetchall()

    def add_column(self, table_uuid, col_name, col_type="TEXT", description=""):
        """Додає нове поле до вказаної таблиці."""
        col_name = self._sanitize_name(col_name)
        col_type = self._validate_type(col_type)
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("INSERT INTO table_columns (table_uuid, column_name, column_type, description) VALUES (%s, %s, %s, %s)", 
                            (table_uuid, col_name, col_type, description))
            conn.commit()

    def update_column(self, table_uuid, old_col_name, new_col_name, new_col_type, new_desc):
        """Оновлює назву, тип та опис існуючої колонки."""
        new_col_name = self._sanitize_name(new_col_name)
        new_col_type = self._validate_type(new_col_type)
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    UPDATE table_columns 
                    SET column_name = %s, column_type = %s, description = %s
                    WHERE table_uuid = %s AND column_name = %s
                """, (new_col_name, new_col_type, new_desc, table_uuid, old_col_name))
            conn.commit()

    def delete_column(self, table_uuid, col_name):
        """Видаляє колонку з таблиці та автоматично підчищає всі зв'язки (FK), де ця колонка брала участь."""
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM table_columns WHERE table_uuid = %s AND column_name = %s", (table_uuid, col_name))
                cur.execute("DELETE FROM table_relations WHERE (from_uuid = %s AND from_col = %s) OR (to_uuid = %s AND to_col = %s)", 
                            (table_uuid, col_name, table_uuid, col_name))
            conn.commit()

    def get_columns_for_table(self, table_uuid):
        """Повертає список всіх полів для конкретної таблиці."""
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT column_name, column_type, description FROM table_columns WHERE table_uuid = %s", (table_uuid,))
                return cur.fetchall()

    def add_relation(self, from_id, from_col, to_id, to_col):
        """Створює зв'язок (Foreign Key) між двома колонками з різних таблиць."""
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("INSERT INTO table_relations (from_uuid, from_col, to_uuid, to_col) VALUES (%s, %s, %s, %s)", 
                            (from_id, from_col, to_id, to_col))
            conn.commit()

    def get_relations(self):
        """Повертає всі наявні зв'язки (FK) для малювання ліній на канвасі."""
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT from_uuid, from_col, to_uuid, to_col FROM table_relations")
                return cur.fetchall()

    def generate_sql_script(self, dialect="PostgreSQL"):
        """Генерує готовий SQL код для створення БД, адаптуючи типи даних під обраний діалект (PostgreSQL, MySQL, Oracle, SQLite)."""
        tables = self.get_all_elements()
        sql_output = f"-- DevHub Architect Export ({dialect})\n"
        sql_output += f"-- Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n"
        table_names = {t[0]: t[1] for t in tables}
        
        for t_uuid, t_name, _, _ in tables:
            columns = self.get_columns_for_table(t_uuid)
            pk_type = "SERIAL PRIMARY KEY"
            if dialect == "SQLite": pk_type = "INTEGER PRIMARY KEY AUTOINCREMENT"
            elif dialect == "MySQL": pk_type = "INT AUTO_INCREMENT PRIMARY KEY"
            elif dialect == "Oracle": pk_type = "NUMBER GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY"

            sql_output += f"CREATE TABLE {t_name} (\n"
            col_lines = []
            for c_name, c_type, c_desc in columns:
                curr_type = c_type
                if "PRIMARY KEY" in curr_type.upper():
                    curr_type = pk_type
                else:
                    if dialect == "Oracle" and "VARCHAR" in curr_type:
                        curr_type = curr_type.replace("VARCHAR", "VARCHAR2")
                    elif dialect == "PostgreSQL" and "DATETIME" in curr_type:
                        curr_type = curr_type.replace("DATETIME", "TIMESTAMP")
                col_lines.append(f"    {c_name} {curr_type}")
            
            for f_uuid, f_col, t_uuid_target, t_col in self.get_relations():
                if f_uuid == t_uuid:
                    target_name = table_names.get(t_uuid_target, "unknown")
                    col_lines.append(f"    FOREIGN KEY ({f_col}) REFERENCES {target_name}({t_col})")
            
            sql_output += ",\n".join(col_lines) + "\n);\n\n"
            
            # Експорт коментарів
            for c_name, _, c_desc in columns:
                if c_desc:
                    if dialect in ["PostgreSQL", "Oracle"]:
                        sql_output += f"COMMENT ON COLUMN {t_name}.{c_name} IS '{c_desc}';\n"
                    elif dialect == "MySQL":
                        sql_output += f"-- Column {t_name}.{c_name} description: {c_desc}\n"
            if any(c[2] for c in columns): sql_output += "\n"
            
        return sql_output


class DataModel(AuthService, ProjectService, ArchitectService):
    """Головний клас моделі даних, який об'єднує всі сервіси та додаткові функції."""
    def log_api_call(self, url, status):
        """Логує кожен виклик API у базі даних (для історії)."""
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("INSERT INTO api_logs (url, status, timestamp) VALUES (%s, %s, %s)", 
                            (url, status, datetime.now()))
            conn.commit()

    def get_current_canvas_data(self):
        """Збирає всі елементи канвасу (таблиці, поля, зв'язки) у єдиний словник для експорту або збереження."""
        els = self.get_all_elements()
        return {
            "elements": els,
            "columns": [{"table_uuid": e[0], "items": self.get_columns_for_table(e[0])} for e in els],
            "relations": self.get_relations()
        }

    def apply_canvas_data(self, data):
        """Очищає поточний канвас і завантажує нові дані з переданого словника (наприклад, при відкритті проєкту)."""
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM table_relations")
                cur.execute("DELETE FROM table_columns")
                cur.execute("DELETE FROM canvas_elements")
                for el in data["elements"]:
                    cur.execute("INSERT INTO canvas_elements VALUES (%s, %s, %s, %s)", el)
                for group in data["columns"]:
                    for cn, ct, desc in group["items"]:
                        cur.execute("INSERT INTO table_columns (table_uuid, column_name, column_type, description) VALUES (%s, %s, %s, %s)", 
                                     (group["table_uuid"], cn, ct, desc))
                for rel in data["relations"]:
                    cur.execute("INSERT INTO table_relations (from_uuid, from_col, to_uuid, to_col) VALUES (%s, %s, %s, %s)", rel)
            conn.commit()

    def export_to_json(self, path):
        """Експортує поточний стан канвасу у локальний .json файл."""
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(self.get_current_canvas_data(), f, indent=4)

    def import_from_json(self, path):
        """Імпортує стан канвасу з локального .json файлу."""
        with open(path, 'r', encoding='utf-8') as f:
            self.apply_canvas_data(json.load(f))

    def clear_all_data(self):
        """Повністю очищає канвас (використовується при створенні нового проєкту або зміні користувача)."""
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM table_relations")
                cur.execute("DELETE FROM table_columns")
                cur.execute("DELETE FROM canvas_elements")
            conn.commit()

    def generate_mock_values(self, table_uuid, count=10, year_filter=True):
        """Службовий метод для генерації випадкових даних (Mock data) без використання ШІ."""
        columns = self.get_columns_for_table(table_uuid)
        all_rows = []
        for _ in range(count):
            row = []
            for name, col_type, desc in columns:
                ct = col_type.upper()
                if "PRIMARY" in ct or "SERIAL" in ct: row.append("NULL")
                elif "INTEGER" in ct: row.append(random.randint(1, 1000))
                elif "REAL" in ct: row.append(round(random.uniform(1.0, 1000.0), 2))
                elif "DATE" in ct or "TIME" in ct or "TIMESTAMP" in ct:
                    days = 365 if year_filter else 3650
                    d = datetime.now() - timedelta(days=random.randint(0, days))
                    row.append(d.strftime('%Y-%m-%d %H:%M:%S'))
                else: row.append(f"Mock_{''.join(random.choices(string.ascii_lowercase, k=4))}")
            all_rows.append(row)
        return all_rows