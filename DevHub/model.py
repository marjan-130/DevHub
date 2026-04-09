import psycopg2
from psycopg2 import sql
import hashlib
import uuid
import json
import random    
import string       
from datetime import datetime, timedelta

class BaseModel:
    """Базовий клас для роботи з PostgreSQL у Docker"""
    def __init__(self):
        self.conn_params = {
            "dbname": "devhub",
            "user": "admin",
            "password": "mysecretpassword",
            "host": "localhost",
            "port": "5432"
        }
        self._init_db()

    def _get_connection(self):
        return psycopg2.connect(**self.conn_params)

    def _init_db(self):
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
                
                cur.execute("SELECT id FROM users WHERE login=%s", ("admin",))
                if not cur.fetchone():
                    pwd_hash = hashlib.sha256("admin123".encode()).hexdigest()
                    cur.execute("INSERT INTO users (login, email, password_hash) VALUES (%s, %s, %s)", 
                                 ("admin", "admin@devhub.com", pwd_hash))
            conn.commit()

    def _sanitize_name(self, name):
        return ''.join(c if c.isalnum() or c == '_' else '_' for c in name)

    def _validate_type(self, col_type):
        allowed_types = ["TEXT", "INTEGER", "REAL", "VARCHAR", "DATETIME", "TIMESTAMP", "BOOLEAN"]
        base_type = col_type.split()[0].upper()
        return col_type if base_type in allowed_types else "TEXT"


class AuthService(BaseModel):
    def authenticate(self, login_or_email, password):
        pwd_hash = hashlib.sha256(password.encode()).hexdigest()
        query = "SELECT id FROM users WHERE (login = %s OR email = %s) AND password_hash = %s"
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, (login_or_email, login_or_email, pwd_hash))
                res = cur.fetchone()
                return res[0] if res else None

    def register(self, login, email, password):
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


class ProjectService(BaseModel):
    def get_user_projects(self, user_id, search_term=""):
        query = """SELECT id, project_name, last_opened FROM projects 
                   WHERE user_id = %s AND project_name ILIKE %s 
                   ORDER BY project_name ASC"""
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, (user_id, f"%{search_term}%"))
                return cur.fetchall()

    def delete_project(self, project_id):
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM projects WHERE id = %s", (project_id,))
            conn.commit()

    def save_project_to_db(self, user_id, project_name, canvas_data, project_id=None):
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
                return res[0] if res else None

    def load_project_from_db(self, project_id):
        query = "SELECT json_data FROM projects WHERE id = %s"
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, (project_id,))
                res = cur.fetchone()
                return json.loads(res[0]) if res else None


class ArchitectService(BaseModel):
    def add_new_element(self, name, x=50, y=50):
        unique_id = str(uuid.uuid4())
        name = self._sanitize_name(name)
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("INSERT INTO canvas_elements (uuid, name, x, y) VALUES (%s, %s, %s, %s)", (unique_id, name, x, y))
            conn.commit()
        return unique_id

    def update_element_pos(self, uuid, x, y):
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("UPDATE canvas_elements SET x = %s, y = %s WHERE uuid = %s", (x, y, uuid))
            conn.commit()

    def get_all_elements(self):
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT uuid, name, x, y FROM canvas_elements")
                return cur.fetchall()

    def add_column(self, table_uuid, col_name, col_type="TEXT", description=""):
        col_name = self._sanitize_name(col_name)
        col_type = self._validate_type(col_type)
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("INSERT INTO table_columns (table_uuid, column_name, column_type, description) VALUES (%s, %s, %s, %s)", 
                            (table_uuid, col_name, col_type, description))
            conn.commit()

    def get_columns_for_table(self, table_uuid):
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT column_name, column_type, description FROM table_columns WHERE table_uuid = %s", (table_uuid,))
                return cur.fetchall()

    def add_relation(self, from_id, from_col, to_id, to_col):
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("INSERT INTO table_relations (from_uuid, from_col, to_uuid, to_col) VALUES (%s, %s, %s, %s)", 
                            (from_id, from_col, to_id, to_col))
            conn.commit()

    def get_relations(self):
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT from_uuid, from_col, to_uuid, to_col FROM table_relations")
                return cur.fetchall()

    # --- ОНОВЛЕНИЙ МЕТОД РОЗУМНОГО ЕКСПОРТУ ---
    def generate_sql_script(self, dialect="PostgreSQL"):
        tables = self.get_all_elements()
        sql_output = f"-- DevHub Architect Export ({dialect})\n"
        sql_output += f"-- Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n"
        
        table_names = {t[0]: t[1] for t in tables}
        
        for t_uuid, t_name, _, _ in tables:
            columns = self.get_columns_for_table(t_uuid)
            
            # Налаштування Primary Key під конкретну БД
            pk_type = "SERIAL PRIMARY KEY"
            if dialect == "SQLite": pk_type = "INTEGER PRIMARY KEY AUTOINCREMENT"
            elif dialect == "MySQL": pk_type = "INT AUTO_INCREMENT PRIMARY KEY"
            elif dialect == "Oracle": pk_type = "NUMBER GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY"

            sql_output += f"CREATE TABLE {t_name} (\n"
            col_lines = []
            
            for c_name, c_type, c_desc in columns:
                current_type = c_type
                
                # Підміна типів даних
                if "PRIMARY KEY" in current_type.upper():
                    current_type = pk_type
                else:
                    if dialect == "Oracle" and "VARCHAR" in current_type:
                        current_type = current_type.replace("VARCHAR", "VARCHAR2")
                    elif dialect == "PostgreSQL" and "DATETIME" in current_type:
                        current_type = current_type.replace("DATETIME", "TIMESTAMP")
                
                line = f"    {c_name} {current_type}"
                col_lines.append(line)
            
            for f_uuid, f_col, t_uuid_target, t_col in self.get_relations():
                if f_uuid == t_uuid:
                    target_name = table_names.get(t_uuid_target, "unknown")
                    col_lines.append(f"    FOREIGN KEY ({f_col}) REFERENCES {target_name}({t_col})")
            
            sql_output += ",\n".join(col_lines) + "\n);\n\n"
            
            # Експорт коментарів (у SQLite немає COMMENT ON COLUMN)
            for c_name, _, c_desc in columns:
                if c_desc:
                    if dialect in ["PostgreSQL", "Oracle"]:
                        sql_output += f"COMMENT ON COLUMN {t_name}.{c_name} IS '{c_desc}';\n"
                    elif dialect == "MySQL":
                        sql_output += f"-- Column {t_name}.{c_name} description: {c_desc}\n"
            if any(c[2] for c in columns): sql_output += "\n"
            
        return sql_output


class DataModel(AuthService, ProjectService, ArchitectService):
    def log_api_call(self, url, status):
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("INSERT INTO api_logs (url, status, timestamp) VALUES (%s, %s, %s)", 
                            (url, status, datetime.now()))
            conn.commit()

    def get_current_canvas_data(self):
        els = self.get_all_elements()
        return {
            "elements": els,
            "columns": [{"table_uuid": e[0], "items": self.get_columns_for_table(e[0])} for e in els],
            "relations": self.get_relations()
        }

    def apply_canvas_data(self, data):
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
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(self.get_current_canvas_data(), f, indent=4)

    def import_from_json(self, path):
        with open(path, 'r', encoding='utf-8') as f:
            self.apply_canvas_data(json.load(f))

    def clear_all_data(self):
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM table_relations")
                cur.execute("DELETE FROM table_columns")
                cur.execute("DELETE FROM canvas_elements")
            conn.commit()

    def generate_mock_values(self, table_uuid, count=10, year_filter=True):
        columns = self.get_columns_for_table(table_uuid)
        all_rows = []
        for _ in range(count):
            row = []
            for name, col_type, desc in columns:
                col_type = col_type.upper()
                if "PRIMARY KEY" in col_type or "SERIAL" in col_type:
                    row.append("NULL") 
                elif "INTEGER" in col_type:
                    row.append(random.randint(1, 1000))
                elif "REAL" in col_type:
                    row.append(round(random.uniform(1.0, 1000.0), 2))
                elif "DATETIME" in col_type or "TIMESTAMP" in col_type:
                    days_back = 365 if year_filter else 3650
                    date = datetime.now() - timedelta(days=random.randint(0, days_back))
                    row.append(date.strftime('%Y-%m-%d %H:%M:%S'))
                else:
                    row.append(f"Test_{''.join(random.choices(string.ascii_lowercase, k=4))}")
            all_rows.append(row)
        return all_rows