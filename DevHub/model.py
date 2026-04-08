import sqlite3
import hashlib
import uuid
import json
import random    
import string       
from datetime import datetime, timedelta

class BaseModel:
    """Базовий клас для роботи з базою даних SQLite"""
    def __init__(self, db_path="devhub.db"):
        self.db_path = db_path
        self._init_db()

    def _get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def _init_db(self):
        queries = [
            """CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                login TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL
            )""",
            """CREATE TABLE IF NOT EXISTS projects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                project_name TEXT NOT NULL,
                json_data TEXT, 
                last_opened DATETIME,
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
            )""",
            """CREATE TABLE IF NOT EXISTS canvas_elements (
                uuid TEXT PRIMARY KEY,
                name TEXT,
                x REAL,
                y REAL
            )""",
            """CREATE TABLE IF NOT EXISTS table_columns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                table_uuid TEXT,
                column_name TEXT,
                column_type TEXT,
                description TEXT,
                FOREIGN KEY(table_uuid) REFERENCES canvas_elements(uuid) ON DELETE CASCADE
            )""",
            """CREATE TABLE IF NOT EXISTS table_relations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                from_uuid TEXT,
                from_col TEXT,
                to_uuid TEXT,
                to_col TEXT,
                FOREIGN KEY(from_uuid) REFERENCES canvas_elements(uuid) ON DELETE CASCADE,
                FOREIGN KEY(to_uuid) REFERENCES canvas_elements(uuid) ON DELETE CASCADE
            )""",
            """CREATE TABLE IF NOT EXISTS api_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                url TEXT,
                status INTEGER,
                timestamp DATETIME
            )"""
        ]
        
        with self._get_connection() as conn:
            for q in queries:
                conn.execute(q)
            
            # Дефолтний адмін (з email)
            check_user = conn.execute("SELECT * FROM users WHERE login='admin'").fetchone()
            if not check_user:
                pwd_hash = hashlib.sha256("admin123".encode()).hexdigest()
                conn.execute("INSERT INTO users (login, email, password_hash) VALUES (?, ?, ?)", 
                             ("admin", "admin@devhub.com", pwd_hash))
            conn.commit()

    def _sanitize_name(self, name):
        """Очищує назви для SQL"""
        return ''.join(c if c.isalnum() or c == '_' else '_' for c in name)

    def _validate_type(self, col_type):
        """Перевіряє типи даних SQL"""
        allowed_types = ["TEXT", "INTEGER", "REAL", "BLOB", "DATETIME"]
        base_type = col_type.split()[0].upper()
        return col_type if base_type in allowed_types else "TEXT"


class AuthService(BaseModel):
    """Сервіс для автентифікації та реєстрації"""
    def authenticate(self, login_or_email, password):
        """Вхід по логіну АБО пошті"""
        pwd_hash = hashlib.sha256(password.encode()).hexdigest()
        query = "SELECT id FROM users WHERE (login = ? OR email = ?) AND password_hash = ?"
        with self._get_connection() as conn:
            res = conn.execute(query, (login_or_email, login_or_email, pwd_hash)).fetchone()
            return res[0] if res else None

    def register(self, login, email, password):
        """Реєстрація нового користувача (додано email)"""
        pwd_hash = hashlib.sha256(password.encode()).hexdigest()
        try:
            with self._get_connection() as conn:
                conn.execute("INSERT INTO users (login, email, password_hash) VALUES (?, ?, ?)", 
                             (login, email, pwd_hash))
                conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False # Логін або пошта вже зайняті


class ProjectService(BaseModel):
    """Сервіс для керування хмарними проектами"""
    def get_user_projects(self, user_id, search_term=""):
        """Повертає відсортований за алфавітом список проектів (Пункт 13)"""
        query = """SELECT id, project_name, last_opened FROM projects 
                   WHERE user_id = ? AND project_name LIKE ? 
                   ORDER BY project_name ASC"""
        with self._get_connection() as conn:
            return conn.execute(query, (user_id, f"%{search_term}%")).fetchall()

    def delete_project(self, project_id):
        with self._get_connection() as conn:
            conn.execute("DELETE FROM projects WHERE id = ?", (project_id,))
            conn.commit()

    def save_project_to_db(self, user_id, project_name, canvas_data, project_id=None):
        json_str = json.dumps(canvas_data)
        now = datetime.now()
        
        with self._get_connection() as conn:
            if project_id:
                query = "UPDATE projects SET json_data = ?, last_opened = ? WHERE id = ?"
                conn.execute(query, (json_str, now, project_id))
                res_id = project_id
            else:
                query = "INSERT INTO projects (user_id, project_name, json_data, last_opened) VALUES (?, ?, ?, ?)"
                cursor = conn.execute(query, (user_id, project_name, json_str, now))
                res_id = cursor.lastrowid
            conn.commit()
            return res_id

    def load_project_from_db(self, project_id):
        query = "SELECT json_data FROM projects WHERE id = ?"
        with self._get_connection() as conn:
            res = conn.execute(query, (project_id,)).fetchone()
            return json.loads(res[0]) if res else None


class ArchitectService(BaseModel):
    """Сервіс для зберігання структури БД у локальній пам'яті (SQLite)"""
    def add_new_element(self, name, x=50, y=50):
        unique_id = str(uuid.uuid4())
        name = self._sanitize_name(name)
        with self._get_connection() as conn:
            conn.execute("INSERT INTO canvas_elements (uuid, name, x, y) VALUES (?, ?, ?, ?)", (unique_id, name, x, y))
            conn.commit()
        return unique_id

    def update_element_pos(self, uuid, x, y):
        with self._get_connection() as conn:
            conn.execute("UPDATE canvas_elements SET x = ?, y = ? WHERE uuid = ?", (x, y, uuid))
            conn.commit()

    def get_all_elements(self):
        with self._get_connection() as conn:
            return conn.execute("SELECT uuid, name, x, y FROM canvas_elements").fetchall()

    def add_column(self, table_uuid, col_name, col_type="TEXT", description=""):
        col_name = self._sanitize_name(col_name)
        col_type = self._validate_type(col_type)
        with self._get_connection() as conn:
            conn.execute("INSERT INTO table_columns (table_uuid, column_name, column_type, description) VALUES (?, ?, ?, ?)", 
                         (table_uuid, col_name, col_type, description))
            conn.commit()

    def get_columns_for_table(self, table_uuid):
        with self._get_connection() as conn:
            return conn.execute("SELECT column_name, column_type, description FROM table_columns WHERE table_uuid = ?", (table_uuid,)).fetchall()

    def add_relation(self, from_id, from_col, to_id, to_col):
        with self._get_connection() as conn:
            conn.execute("INSERT INTO table_relations (from_uuid, from_col, to_uuid, to_col) VALUES (?, ?, ?, ?)", (from_id, from_col, to_id, to_col))
            conn.commit()

    def get_relations(self):
        with self._get_connection() as conn:
            return conn.execute("SELECT from_uuid, from_col, to_uuid, to_col FROM table_relations").fetchall()

    def generate_sql_script(self):
        """Генерація SQL-коду на основі поточних таблиць"""
        tables = self.get_all_elements()
        sql_output = "-- DevHub Architect Export\n\n"
        table_names = {t[0]: t[1] for t in tables}
        
        for t_uuid, t_name, _, _ in tables:
            columns = self.get_columns_for_table(t_uuid)
            sql_output += f"CREATE TABLE {t_name} (\n"
            col_lines = [f"    {c[0]} {c[1]}" for c in columns]
            
            for f_uuid, f_col, t_uuid_target, t_col in self.get_relations():
                if f_uuid == t_uuid:
                    target_name = table_names.get(t_uuid_target, "unknown")
                    col_lines.append(f"    FOREIGN KEY ({f_col}) REFERENCES {target_name}({t_col})")
            
            sql_output += ",\n".join(col_lines) + "\n);\n\n"
        return sql_output


class DataModel(AuthService, ProjectService, ArchitectService):
    """Фінальний клас-фасад, який об'єднує всі сервіси"""
    def __init__(self, db_path="devhub.db"):
        super().__init__(db_path)

    def log_api_call(self, url, status):
        with self._get_connection() as conn:
            conn.execute("INSERT INTO api_logs (url, status, timestamp) VALUES (?, ?, ?)", (url, status, datetime.now()))
            conn.commit()

    def get_current_canvas_data(self):
        """Збирає всі поточні елементи в один словник для збереження"""
        els = self.get_all_elements()
        return {
            "elements": els,
            "columns": [{"table_uuid": e[0], "items": self.get_columns_for_table(e[0])} for e in els],
            "relations": self.get_relations()
        }

    def apply_canvas_data(self, data):
        """Очищує поточний канвас і завантажує дані з JSON"""
        with self._get_connection() as conn:
            conn.execute("DELETE FROM table_relations")
            conn.execute("DELETE FROM table_columns")
            conn.execute("DELETE FROM canvas_elements")
            
            for el in data["elements"]:
                conn.execute("INSERT INTO canvas_elements VALUES (?, ?, ?, ?)", el)
            for group in data["columns"]:
                for cn, ct in group["items"]:
                    conn.execute("INSERT INTO table_columns (table_uuid, column_name, column_type) VALUES (?, ?, ?)", (group["table_uuid"], cn, ct))
            for rel in data["relations"]:
                conn.execute("INSERT INTO table_relations (from_uuid, from_col, to_uuid, to_col) VALUES (?, ?, ?, ?)", rel)
            conn.commit()

    def export_to_json(self, path):
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(self.get_current_canvas_data(), f, indent=4)

    def import_from_json(self, path):
        with open(path, 'r', encoding='utf-8') as f:
            self.apply_canvas_data(json.load(f))

    def clear_all_data(self):
        """Очищення робочої області"""
        with self._get_connection() as conn:
            conn.execute("DELETE FROM table_relations")
            conn.execute("DELETE FROM table_columns")
            conn.execute("DELETE FROM canvas_elements")
            conn.commit()

    def generate_mock_values(self, table_uuid, count=10, year_filter=True):
        """Генерує випадкові дані для вказаної таблиці"""
        columns = self.get_columns_for_table(table_uuid)
        all_rows = []
        for _ in range(count):
            row = []
            for name, col_type, desc in columns:
                col_type = col_type.upper()
                if "PRIMARY KEY" in col_type:
                    row.append("NULL") 
                elif "INTEGER" in col_type:
                    row.append(random.randint(1, 1000))
                elif "REAL" in col_type:
                    row.append(round(random.uniform(1.0, 1000.0), 2))
                elif "DATETIME" in col_type:
                    days_back = 365 if year_filter else 3650
                    date = datetime.now() - timedelta(days=random.randint(0, days_back))
                    row.append(date.strftime('%Y-%m-%d %H:%M:%S'))
                else:
                    # Для TEXT та інших генеруємо випадкове слово
                    row.append(f"Test_{''.join(random.choices(string.ascii_lowercase, k=4))}")
            all_rows.append(row)
        return all_rows