import os
import json
import requests
import tkinter as tk
import re
import pandas as pd
import smtplib
import random
from dotenv import load_dotenv
from google import genai
from email.mime.text import MIMEText
from tkinter import ttk, filedialog, simpledialog
from view import (
    LoginFrame, DashboardFrame, ColumnDialog, AISmartFillDialog, 
    MessageDialog, ProgressDialog, VerificationDialog, TableManagerDialog
)
from validators import (
    validate_sql_name, 
    confirm_save_action, 
    validate_foreign_key_match, 
    check_unsaved_changes
)

load_dotenv()

class ApiManager:
    """Менеджер для роботи з вкладкою API Client (відправка HTTP запитів)."""
    def __init__(self, model, view):
        self.model = model
        self.view = view

    def handle_request(self):
        """Відправляє GET запит за вказаним URL, обробляє відповідь та виводить результат або помилку."""
        dash_fr = self.view.frames[DashboardFrame]
        url = dash_fr.url_entry.get().strip()
        if not url.startswith(("http://", "https://")):
            MessageDialog(self.view, "Помилка URL", "Введіть валідний URL (http/https)", "error")
            return
        
        output_widget = getattr(dash_fr, 'result_text', None)
        if hasattr(dash_fr, 'api_progress'):
            dash_fr.api_progress.pack(fill="x", padx=10, before=dash_fr.result_text)
            dash_fr.api_progress.start(10)
            dash_fr.update()

        try:
            if output_widget:
                output_widget.delete("1.0", "end")
                output_widget.insert("end", "Завантаження...\n")
                dash_fr.update()
            response = requests.get(url, timeout=10)
            self.model.log_api_call(url, response.status_code)
            try:
                data = response.json()
                formatted = json.dumps(data, indent=4, ensure_ascii=False)
            except:
                formatted = response.text
            if output_widget:
                output_widget.delete("1.0", "end")
                output_widget.insert("end", f"Status: {response.status_code}\n\n{formatted}")
        except Exception as e:
            if output_widget: output_widget.insert("end", f"\nПомилка: {str(e)}")
            else: MessageDialog(self.view, "Помилка API", str(e), "error")
        finally:
            if hasattr(dash_fr, 'api_progress'):
                dash_fr.api_progress.stop()
                dash_fr.api_progress.pack_forget()


class ArchitectManager:
    """Менеджер для роботи з візуальним редактором таблиць (Канвас)."""
    def __init__(self, model, view, parent_controller):
        self.model = model
        self.view = view
        self.parent = parent_controller 

    def handle_add_table(self):
        """Відкриває міні-діалог для введення назви і створює нову таблицю з автоматичним полем 'id'."""
        table_name = simpledialog.askstring("Нова таблиця", "Введіть назву таблиці:", parent=self.view)
        if not table_name: return
        
        is_valid, error_msg = validate_sql_name(table_name)
        if not is_valid:
            MessageDialog(self.view, "Помилка валідації", error_msg, "error")
            return
            
        table_id = self.model.add_new_element(table_name)
        # Автоматично створюємо Primary Key
        self.model.add_column(table_id, "id", "INTEGER PRIMARY KEY", "Auto-generated ID")
        
        self.parent.is_dirty = True
        self.parent.refresh_canvas()

    def handle_fk_setup(self):
        """Вмикає або вимикає режим створення зовнішнього ключа (Foreign Key)."""
        dash = self.view.frames[DashboardFrame]
        if self.parent.fk_step is not None:
            self.cancel_fk_mode()
            return
        self.parent.fk_step = 1 
        self.parent.fk_data = {}
        if hasattr(dash, 'set_fk_button_state'): dash.set_fk_button_state(True)
        self.view.bind("<Escape>", lambda e: self.cancel_fk_mode())
        msg = "Режим FK: УВІМКНЕНО. Оберіть таблицю-джерело\n(Натисніть ESC для скасування)"
        MessageDialog(self.view, "FK Mode", msg, "info")

    def cancel_fk_mode(self, show_msg=True):
        """Скасовує процес створення FK і знімає підсвітку кнопок."""
        self.parent.fk_step = None
        self.parent.fk_data = {}
        dash = self.view.frames[DashboardFrame]
        if hasattr(dash, 'set_fk_button_state'): dash.set_fk_button_state(False)
        self.view.unbind("<Escape>") 
        if show_msg:
            MessageDialog(self.view, "FK Mode", "Режим скасовано", "info")

    def _select_column_for_fk(self, table_id, table_name, step):
        """Відкриває вікно вибору колонки для створення зв'язку (Крок 1 і Крок 2)."""
        columns = self.model.get_columns_for_table(table_id)
        if not columns:
            MessageDialog(self.view, "Увага", "У цій таблиці немає колонок!", "error")
            self.cancel_fk_mode()
            return
            
        top = tk.Toplevel(self.view)
        top.title(f"Step {step}")
        top.geometry("300x350")
        top.grab_set() 
        
        tk.Label(top, text=f"Table: {table_name}", font=("Arial", 10, "bold")).pack(pady=10)
        
        lb = tk.Listbox(top, font=("Arial", 10), selectbackground="#1f6feb", selectforeground="white")
        for col_name, col_type, desc in columns:
            lb.insert("end", f"{col_name} ({col_type})")
            
        lb.pack(fill="both", expand=True, padx=20, pady=5)

        def confirm():
            selection = lb.curselection()
            if selection:
                full_str = lb.get(selection[0])
                selected_col = full_str.split(" (")[0]
                selected_col_type = next(c[1] for c in columns if c[0] == selected_col)
                
                if step == 1: # Вибрали таблицю-джерело
                    self.parent.fk_data.update({"from_id": table_id, "from_col": selected_col, "from_type": selected_col_type})
                    self.parent.fk_step = 2
                    top.destroy()
                    MessageDialog(self.view, "FK Mode", "Крок 2: Оберіть цільову таблицю", "info")
                else:         # Вибрали цільову таблицю
                    is_valid, err = validate_foreign_key_match(self.parent.fk_data["from_type"], selected_col_type)
                    if not is_valid:
                        MessageDialog(self.view, "Помилка типу", err, "error")
                        self.cancel_fk_mode()
                        top.destroy()
                        return
                    self.model.add_relation(self.parent.fk_data["from_id"], self.parent.fk_data["from_col"], table_id, selected_col)
                    self.parent.is_dirty = True
                    self.parent.refresh_canvas()
                    self.cancel_fk_mode(show_msg=False) 
                    top.destroy()
                    MessageDialog(self.view, "Успіх", "Зв'язок створено!", "success")
                    
        ttk.Button(top, text="Підтвердити", command=confirm).pack(pady=15)


class AppController:
    """Головний контролер системи, що зв'язує Модель і Вигляд."""
    def __init__(self, model, view):
        self.model = model
        self.view = view
        self.api_mgr = ApiManager(model, view)
        self.arch_mgr = ArchitectManager(model, view, self)

        # Безпечне завантаження ключів з .env
        self.gemini_key = os.getenv("GEMINI_API_KEY")
        self.smtp_email = os.getenv("SMTP_EMAIL")
        self.smtp_password = os.getenv("SMTP_PASSWORD")

        self.lang = "UA"
        self.default_dialect = "PostgreSQL"
        self.current_user_id = None
        self.current_project_id = None
        self.is_dirty = False
        self.fk_step = None
        self.fk_data = {}
        self.drag_data = None
        
        self.view.app_logic = self 
        self._setup_bindings()
        self._setup_main_menu()
        self.view.show_frame(LoginFrame)
        self._setup_canvas_bindings()

    def _setup_main_menu(self):
        """Ініціалізує верхнє меню вікна (Файл, Мова, Діалект)."""
        menubar = tk.Menu(self.view)
        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="Новий / New", command=self.handle_new_project)
        file_menu.add_separator()
        file_menu.add_command(label="Вихід / Exit", command=self.view.quit)
        menubar.add_cascade(label="Файл / File", menu=file_menu)
        
        lang_menu = tk.Menu(menubar, tearoff=0)
        lang_menu.add_command(label="Українська", command=lambda: self.switch_language("UA"))
        lang_menu.add_command(label="English", command=lambda: self.switch_language("EN"))
        menubar.add_cascade(label="Мова / Language", menu=lang_menu)
        
        dialect_menu = tk.Menu(menubar, tearoff=0)
        for d in ["PostgreSQL", "MySQL", "SQLite", "Oracle"]:
            dialect_menu.add_command(label=d, command=lambda db=d: self.switch_dialect(db))
        menubar.add_cascade(label="Діалект SQL", menu=dialect_menu)
        self.view.config(menu=menubar)

    def switch_dialect(self, dialect):
        """Змінює SQL діалект за замовчуванням для поточного сеансу."""
        self.default_dialect = dialect
        MessageDialog(self.view, "Налаштування", f"Діалект за замовчуванням змінено на: {dialect}", "info")

    def switch_language(self, lang):
        """Змінює мову інтерфейсу."""
        self.lang = lang
        dash = self.view.frames[DashboardFrame]
        if hasattr(dash, 'update_language_ui'): dash.update_language_ui(lang)
        self.view.title(f"DevHub Architect & API [{lang}]")

    def handle_register(self):
        """Обробляє реєстрацію: валідація, відправка коду, створення користувача."""
        login_fr = self.view.frames[LoginFrame]
        user = login_fr.reg_login_entry.get().strip()
        email_widget = getattr(login_fr, 'reg_email_entry', None)
        email = email_widget.get().strip() if email_widget else ""
        pwd = login_fr.reg_pass_entry.get().strip()
        
        if not user or not email or not pwd:
            MessageDialog(self.view, "Помилка", "Заповніть усі поля!", "error")
            return
        if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
            MessageDialog(self.view, "Помилка", "Некоректний формат Email!", "error")
            return

        verification_code = str(random.randint(100000, 999999))
        
        loader = ProgressDialog(self.view, f"Відправляємо код на {email}...")
        self.view.update() 
        
        success = self.send_verification_email(email, verification_code)
        loader.close()

        if success:
            dialog = VerificationDialog(self.view, email)
            self.view.wait_window(dialog)
            
            if dialog.result == verification_code:
                if self.model.register(user, email, pwd):
                    MessageDialog(self.view, "Успіх", "Акаунт успішно створено!", "success")
                    login_fr.show_login_form()
                else: 
                    MessageDialog(self.view, "Помилка", "Користувач вже існує.", "error")
            elif dialog.result is not None:
                MessageDialog(self.view, "Помилка", "Невірний код! Реєстрацію скасовано.", "error")
        else: 
            MessageDialog(self.view, "Помилка SMTP", "Не вдалося відправити лист. Перевірте .env.", "error")

    def send_verification_email(self, receiver_email, code):
        """Надсилає email з 6-значним кодом через SMTP сервер Google."""
        if not self.smtp_email or not self.smtp_password:
            return False
        msg = MIMEText(f"Вітаємо у DevHub Architect!\n\nВаш код підтвердження: {code}")
        msg['Subject'] = 'Код підтвердження DevHub'
        msg['From'] = f"DevHub Admin <{self.smtp_email}>"
        msg['To'] = receiver_email
        try:
            server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
            server.login(self.smtp_email, self.smtp_password)
            server.sendmail(self.smtp_email, receiver_email, msg.as_string())
            server.quit()
            return True
        except Exception:
            return False

    def handle_export_sql(self):
        """Запускає діалог ШІ-генерації, викликає Gemini API та зберігає готовий .sql скрипт."""
        dialog = AISmartFillDialog(self.view, lang=self.lang, default_dialect=self.default_dialect)
        self.view.wait_window(dialog)
        
        ai_insert_script = ""
        if dialog.result:
            if not self.gemini_key:
                MessageDialog(self.view, "Помилка", "API ключ не знайдено! Перевірте файл .env", "error")
                return

            client = genai.Client(api_key=self.gemini_key)
            params = dialog.result
            selected_dialect = params.get('dialect', 'PostgreSQL')
            tables = self.model.get_all_elements()
            
            loader = ProgressDialog(self.view, f"ШІ генерує дані для {len(tables)} таблиць...")
            self.view.update()
            
            for t_id, t_name, _, _ in tables:
                cols = self.model.get_columns_for_table(t_id)
                cols_str = ", ".join([f"{c[0]} ({c[1]}{f', Опис: {c[2]}' if c[2] else ''})" for c in cols])
                
                prompt = f"""
                Ти — SQL розробник. Згенеруй ТОЧНО {params['count']} SQL INSERT запитів для таблиці '{t_name}'.
                База даних (діалект): {selected_dialect}.
                Колонки: {cols_str}.
                Мова даних: {params['lang']}.
                Контекст/Тема: {params['context']}.
                Вимоги: 
                - Тільки чистий SQL код для вставки даних (INSERT INTO).
                - Реалістичні дані.
                - Без ```sql блоків.
                """
                try:
                    response = client.models.generate_content(model='gemini-2.5-flash', contents=prompt)
                    ai_insert_script += f"\n-- AI Data for {t_name}\n{response.text.strip()}\n"
                except Exception as e:
                    ai_insert_script += f"\n-- AI Error for {t_name}: {str(e)}\n"

            loader.close()

            sql_structure = self.model.generate_sql_script(dialect=selected_dialect)
            final_code = sql_structure + "\n\n-- START AI GENERATED DATA --\n" + ai_insert_script
            
            path = filedialog.asksaveasfilename(defaultextension=".sql", initialfile=f"project_dump_{selected_dialect.lower()}.sql")
            if path:
                with open(path, 'w', encoding='utf-8') as f:
                    f.write(final_code)
                MessageDialog(self.view, "Експорт завершено", f"Дані ({selected_dialect}) збережено!", "success")

    def handle_export_excel(self):
        """Генерує Data Dictionary (звіт про структуру БД) і зберігає у форматі Excel."""
        tables = self.model.get_all_elements()
        if not tables:
            MessageDialog(self.view, "Інфо", "Немає таблиць для експорту.", "info")
            return

        path = filedialog.asksaveasfilename(defaultextension=".xlsx", initialfile="database_structure.xlsx", filetypes=[("Excel files", "*.xlsx")])
        if not path:
            return

        data = []
        relations = self.model.get_relations()
        table_names = {t[0]: t[1] for t in tables} 

        for t_uuid, t_name, _, _ in tables:
            columns = self.model.get_columns_for_table(t_uuid)
            for c_name, c_type, c_desc in columns:
                fk_info = ""
                for f_id, f_col, to_id, to_col in relations:
                    if f_id == t_uuid and f_col == c_name:
                        target_name = table_names.get(to_id, "Unknown")
                        fk_info = f"➡ {target_name} ({to_col})"

                data.append({
                    "Таблиця": t_name,
                    "Поле": c_name,
                    "Тип даних": c_type,
                    "Опис": c_desc if c_desc else "",
                    "Зв'язок (FK)": fk_info
                })

        try:
            df = pd.DataFrame(data)
            df.to_excel(path, index=False)
            MessageDialog(self.view, "Excel", "Словник бази даних успішно збережено!", "success")
        except Exception as e:
            MessageDialog(self.view, "Помилка експорту", str(e), "error")

    def handle_login(self):
        """Обробляє логін. При успішному вході примусово зачищає старі дані канвасу."""
        login_fr = self.view.frames[LoginFrame]
        uid = self.model.authenticate(login_fr.login_entry.get().strip(), login_fr.pass_entry.get().strip())
        if uid:
            self.current_user_id = uid
            
            # --- ЗАЧИСТКА ДАНИХ ДЛЯ НОВОЇ СЕСІЇ ---
            self.current_project_id = None 
            self.is_dirty = False
            self.model.clear_all_data() 
            
            self.view.show_frame(DashboardFrame)
            dash = self.view.frames[DashboardFrame]
            
            dash.project_listbox.bind("<<ListboxSelect>>", self.handle_load_project)
            dash.search_ent.bind("<KeyRelease>", lambda e: self.refresh_project_list())
            dash.project_listbox.bind("<Button-3>", self._show_context_menu) # Права кнопка миші
            
            if hasattr(dash, 'p_menu'): 
                dash.p_menu.delete(0, "end")
                dash.p_menu.add_command(label="✏️ Перейменувати", command=self.handle_rename_project)
                dash.p_menu.add_command(label="❌ Видалити", command=self.handle_delete_project)
                
            self.refresh_project_list()
            self.refresh_canvas()
        else: 
            MessageDialog(self.view, "Помилка", "Невірний логін або пароль", "error")

    def _show_context_menu(self, event):
        """Відображає контекстне меню (перейменувати/видалити) при кліку правою кнопкою по проєкту."""
        dash = self.view.frames[DashboardFrame]
        dash.project_listbox.selection_clear(0, tk.END)
        nearest = dash.project_listbox.nearest(event.y)
        if nearest >= 0:
            dash.project_listbox.selection_set(nearest)
            dash.p_menu.post(event.x_root, event.y_root)

    def handle_delete_project(self):
        """Видаляє проєкт з бази даних."""
        dash = self.view.frames[DashboardFrame]
        selection = dash.project_listbox.curselection()
        if selection:
            text = dash.project_listbox.get(selection[0])
            p_id = int(text.split("ID:")[1].replace(")", ""))
            if tk.messagebox.askyesno("Delete", "Delete project forever?"):
                self.model.delete_project(p_id)
                if self.current_project_id == p_id: self.current_project_id = None
                self.refresh_project_list()

    def handle_rename_project(self):
        """Запитує нову назву та перейменовує проєкт."""
        dash = self.view.frames[DashboardFrame]
        selection = dash.project_listbox.curselection()
        if selection:
            text = dash.project_listbox.get(selection[0])
            p_id = int(text.split("ID:")[1].replace(")", ""))
            old_name = text.split(" (ID:")[0]
            
            new_name = simpledialog.askstring("Перейменувати", "Нова назва проєкту:", initialvalue=old_name, parent=self.view)
            
            if new_name and new_name.strip() and new_name.strip() != old_name:
                self.model.rename_project(p_id, new_name.strip())
                self.refresh_project_list()
                MessageDialog(self.view, "Успіх", "Проєкт успішно перейменовано", "success")

    def handle_db_save(self):
        """Зберігає поточний стан (JSON) у базу даних."""
        if not self.current_user_id: return
        name = simpledialog.askstring("Save", "Project Name:", initialvalue="My Project") if not self.current_project_id else "Updated"
        if not name and not self.current_project_id: return
        self.current_project_id = self.model.save_project_to_db(self.current_user_id, name, self.model.get_current_canvas_data(), self.current_project_id)
        self.is_dirty = False
        self.refresh_project_list()
        MessageDialog(self.view, "Збережено", "Проєкт збережено в базу даних", "success")

    def refresh_project_list(self):
        """Оновлює список проєктів на бічній панелі."""
        dash = self.view.frames[DashboardFrame]
        dash.project_listbox.delete(0, tk.END)
        for p_id, p_name, p_date in self.model.get_user_projects(self.current_user_id, dash.search_ent.get()):
            dash.project_listbox.insert(tk.END, f"{p_name} (ID:{p_id})")

    def handle_load_project(self, event):
        """Завантажує обраний проєкт з бази даних на канвас."""
        if not check_unsaved_changes(self.is_dirty): return
        dash = self.view.frames[DashboardFrame]
        selection = dash.project_listbox.curselection()
        if selection:
            p_id = int(dash.project_listbox.get(selection[0]).split("ID:")[1].replace(")", ""))
            data = self.model.load_project_from_db(p_id)
            if data:
                self.current_project_id = p_id
                self.model.apply_canvas_data(data)
                self.is_dirty = False
                self.refresh_canvas()

    def handle_save_file(self):
        """Зберігає проєкт локально у JSON."""
        path = filedialog.asksaveasfilename(defaultextension=".json")
        if path: self.model.export_to_json(path); self.is_dirty = False

    def handle_open_file(self):
        """Завантажує проєкт з локального JSON-файлу."""
        if not check_unsaved_changes(self.is_dirty): return
        path = filedialog.askopenfilename()
        if path:
            self.model.import_from_json(path)
            self.current_project_id = None; self.is_dirty = False; self.refresh_canvas()

    def handle_new_project(self):
        """Очищає робочий простір для нового проєкту."""
        if not check_unsaved_changes(self.is_dirty): return
        if tk.messagebox.askyesno("New", "Clear workspace?"):
            self.current_project_id = None; self.model.clear_all_data(); self.is_dirty = False; self.refresh_canvas()

    def refresh_canvas(self):
        """Перемальовує всі таблиці та зв'язки на канвасі."""
        dash_fr = self.view.frames[DashboardFrame]
        dash_fr.canvas.delete("all")
        if hasattr(dash_fr, '_draw_grid'): dash_fr._draw_grid()
        for t_id, name, x, y in self.model.get_all_elements():
            dash_fr.draw_table(t_id, name, x, y, columns=self.model.get_columns_for_table(t_id))
        self.refresh_lines()

    def refresh_lines(self):
        """Перемальовує лише лінії зв'язків."""
        dash_fr = self.view.frames[DashboardFrame]
        dash_fr.canvas.delete("connection")
        for f_id, f_col, t_id, t_col in self.model.get_relations():
            dash_fr.draw_connection(f_id, f_col, self.model.get_columns_for_table(f_id), t_id, t_col, self.model.get_columns_for_table(t_id))

    def _setup_canvas_bindings(self):
        """Налаштовує відстеження кліків миші по канвасу."""
        dash_fr = self.view.frames[DashboardFrame]
        dash_fr.canvas.bind("<Button-1>", self.on_canvas_click)
        dash_fr.canvas.bind("<B1-Motion>", self.on_drag_motion)
        dash_fr.canvas.bind("<ButtonRelease-1>", self.on_drag_stop)
        dash_fr.canvas.bind("<Double-Button-1>", self.on_table_double_click)
        dash_fr.canvas.bind("<Button-3>", self.show_table_context_menu)

    def show_table_context_menu(self, event):
        """Відображає контекстне меню (редагувати/видалити) при кліку правою кнопкою по таблиці."""
        canvas = event.widget
        item = canvas.find_closest(event.x, event.y)
        tags = canvas.gettags(item)
        if "table" in tags:
            table_id = tags[0]
            menu = tk.Menu(self.view, tearoff=0)
            menu.add_command(label="📝 Редагувати", command=lambda: self.on_table_double_click(event))
            menu.add_command(label="❌ Видалити", command=lambda: self.delete_table_action(table_id))
            menu.post(event.x_root, event.y_root)

    def delete_table_action(self, table_uuid):
        """Видаляє обрану таблицю з БД та оновлює канвас."""
        if tk.messagebox.askyesno("Confirm", "Видалити таблицю?"):
            with self.model._get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("DELETE FROM canvas_elements WHERE uuid = %s", (table_uuid,))
                conn.commit()
            self.refresh_canvas()

    def on_canvas_click(self, event):
        """Обробляє натискання лівої кнопки миші (початок перетягування або вибір для FK)."""
        item = event.widget.find_closest(event.x, event.y)
        tags = event.widget.gettags(item)
        if "table" in tags:
            table_id = tags[0]
            if self.fk_step in [1, 2]:
                all_t = self.model.get_all_elements()
                t_name = next((t[1] for t in all_t if t[0] == table_id), "Table")
                self.arch_mgr._select_column_for_fk(table_id, t_name, self.fk_step)
                return
            
            # Піднімаємо таблицю "вище" і фіксуємо координати
            event.widget.tag_raise(table_id)
            self.drag_data = {"item": table_id, "x": event.x, "y": event.y}
    
    def on_drag_motion(self, event):
        """Обробляє перетягування таблиці (плавний рух)."""
        if self.drag_data:
            dx = event.x - self.drag_data["x"]
            dy = event.y - self.drag_data["y"]
            event.widget.move(self.drag_data["item"], dx, dy)
            
            self.drag_data["x"] = event.x
            self.drag_data["y"] = event.y
            
            self.refresh_lines()
            self.is_dirty = True 

    def on_drag_stop(self, event):
        """Обробляє відпускання лівої кнопки миші (зберігає нові координати таблиці)."""
        if self.drag_data:
            items = event.widget.find_withtag(self.drag_data["item"])
            if items:
                coords = event.widget.coords(items[0])
                self.model.update_element_pos(self.drag_data["item"], coords[0], coords[1])
            self.drag_data = None

    def on_table_double_click(self, event):
        """Відкриває повноцінний редактор таблиці (TableManagerDialog)."""
        item = event.widget.find_closest(event.x, event.y)
        tags = event.widget.gettags(item)
        if "table" in tags:
            t_uuid = tags[0]
            all_t = self.model.get_all_elements()
            t_name = next((t[1] for t in all_t if t[0] == t_uuid), "Table")
            columns = self.model.get_columns_for_table(t_uuid)
            
            manager = TableManagerDialog(self.view, t_name, columns)
            self.view.wait_window(manager)
            
            if manager.action == "add":
                dialog = ColumnDialog(self.view, lang=self.lang)
                self.view.wait_window(dialog)
                if dialog.result:
                    name, tp, desc = dialog.result
                    is_valid, err = validate_sql_name(name)
                    if not is_valid: 
                        MessageDialog(self.view, "Помилка", err, "error")
                        return
                    self.model.add_column(t_uuid, name, tp, description=desc)
                    self.is_dirty = True
                    self.refresh_canvas()
                    
            elif manager.action == "edit":
                old_col_name = manager.data
                if old_col_name == "id":
                    MessageDialog(self.view, "Помилка", "Primary Key не можна редагувати!", "error")
                    return
                    
                old_col_data = next((c for c in columns if c[0] == old_col_name), None)
                if old_col_data:
                    dialog = ColumnDialog(self.view, lang=self.lang, edit_data=old_col_data)
                    self.view.wait_window(dialog)
                    if dialog.result:
                        new_name, new_tp, new_desc = dialog.result
                        self.model.update_column(t_uuid, old_col_name, new_name, new_tp, new_desc)
                        self.is_dirty = True
                        self.refresh_canvas()
                        
            elif manager.action == "delete":
                col_name = manager.data
                if col_name == "id":
                    MessageDialog(self.view, "Помилка", "Primary Key не можна видалити!", "error")
                elif tk.messagebox.askyesno("Видалення", f"Видалити поле {col_name}?"):
                    self.model.delete_column(t_uuid, col_name)
                    self.is_dirty = True
                    self.refresh_canvas()

    def handle_forgot_password(self):
        """Процес відновлення пароля через підтвердження пошти"""
        from tkinter import simpledialog
        import random
        
        # 1. Питаємо email
        email = simpledialog.askstring("Відновлення", "Введіть ваш Email:", parent=self.view)
        if not email: return
        
        # 2. Перевіряємо, чи є він у базі
        if not self.model.check_email_exists(email):
            from view import MessageDialog
            MessageDialog(self.view, "Помилка", "Користувача з таким Email не знайдено", "error")
            return

        # 3. Генеруємо код і відправляємо (як при реєстрації)
        verification_code = str(random.randint(100000, 999999))
        if self.send_verification_email(email, verification_code):
            from view import VerificationDialog, MessageDialog
            dialog = VerificationDialog(self.view, email)
            self.view.wait_window(dialog)
            
            # 4. Якщо код введено правильно
            if dialog.result == verification_code:
                new_pwd = simpledialog.askstring("Новий пароль", "Введіть новий пароль:", parent=self.view, show="*")
                if new_pwd:
                    self.model.update_password(email, new_pwd)
                    MessageDialog(self.view, "Успіх", "Пароль змінено! Тепер можете увійти", "success")
            elif dialog.result is not None:
                MessageDialog(self.view, "Помилка", "Невірний код підтвердження", "error")
   
    def _setup_bindings(self):
        """Налаштовує кнопки верхньої панелі (Toolbar)."""
        dash_fr = self.view.frames[DashboardFrame]
        dash_fr.btn_send.config(command=self.api_mgr.handle_request)
        dash_fr.btn_add_table.config(command=self.arch_mgr.handle_add_table)
        dash_fr.btn_fk.config(command=self.arch_mgr.handle_fk_setup)
        dash_fr.btn_save.config(command=self.handle_save_file)
        dash_fr.btn_open.config(command=self.handle_open_file)
        dash_fr.btn_new.config(command=self.handle_new_project)
        dash_fr.btn_export_sql.config(command=self.handle_export_sql)
        dash_fr.btn_export_excel.config(command=self.handle_export_excel)
        dash_fr.btn_db_save.config(command=self.handle_db_save)