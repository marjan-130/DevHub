import json
import requests
import tkinter as tk
import re
import smtplib
import random
from google import genai
from email.mime.text import MIMEText
from tkinter import ttk, messagebox, filedialog, simpledialog
from view import LoginFrame, DashboardFrame, ColumnDialog, AISmartFillDialog
from validators import (
    validate_sql_name, 
    confirm_save_action, 
    can_add_primary_key, 
    validate_foreign_key_match, 
    check_unsaved_changes
)

class ApiManager:
    """Клас для керування мережевими запитами (API Client)"""
    def __init__(self, model, view):
        self.model = model
        self.view = view

    def handle_request(self):
        dash_fr = self.view.frames[DashboardFrame]
        url = dash_fr.url_entry.get().strip()
        if not url.startswith(("http://", "https://")):
            messagebox.showwarning("URL Error", "Введіть валідний URL (http/https)")
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
            else: messagebox.showerror("Помилка", str(e))
        finally:
            if hasattr(dash_fr, 'api_progress'):
                dash_fr.api_progress.stop()
                dash_fr.api_progress.pack_forget()

class ArchitectManager:
    """Клас для керування графічним редактором"""
    def __init__(self, model, view, parent_controller):
        self.model = model
        self.view = view
        self.parent = parent_controller 

    def handle_add_table(self):
        dialog = ColumnDialog(self.view, lang=self.parent.lang)
        self.view.wait_window(dialog)
        if dialog.result:
            table_name, initial_type, is_primary, description = dialog.result
            is_valid, error_msg = validate_sql_name(table_name)
            if not is_valid:
                messagebox.showerror("Error", error_msg)
                return
            if confirm_save_action(f"створити таблицю '{table_name}'"):
                table_id = self.model.add_new_element(table_name)
                col_type = initial_type
                if is_primary: col_type += " PRIMARY KEY"
                self.model.add_column(table_id, "id", col_type)
                self.parent.is_dirty = True
                self.parent.refresh_canvas()
                self.model.add_column(table_id, "id", col_type, description)

    def handle_fk_setup(self):
        dash = self.view.frames[DashboardFrame]
        if self.parent.fk_step is not None:
            self.cancel_fk_mode()
            return
        self.parent.fk_step = 1 
        self.parent.fk_data = {}
        if hasattr(dash, 'set_fk_button_state'): dash.set_fk_button_state(True)
        self.view.bind("<Escape>", lambda e: self.cancel_fk_mode())
        msg = "FK Mode: ON. Select source table\n(Press ESC to cancel)" if self.parent.lang == "EN" else "Режим FK: УВІМКНЕНО. Оберіть таблицю-джерело\n(Натисніть ESC для скасування)"
        messagebox.showinfo("FK Mode", msg)

    def cancel_fk_mode(self, show_msg=True):
        self.parent.fk_step = None
        self.parent.fk_data = {}
        dash = self.view.frames[DashboardFrame]
        if hasattr(dash, 'set_fk_button_state'): dash.set_fk_button_state(False)
        self.view.unbind("<Escape>") 
        if show_msg:
            msg = "Mode disabled" if self.parent.lang == "EN" else "Режим скасовано"
            messagebox.showinfo("FK Mode", msg)

    def _select_column_for_fk(self, table_id, table_name, step):
        columns = self.model.get_columns_for_table(table_id)
        if not columns:
            messagebox.showwarning("Warning", "No columns in this table!")
            self.cancel_fk_mode()
            return
        top = tk.Toplevel(self.view)
        top.title(f"Step {step}" if self.parent.lang == "EN" else f"Крок {step}")
        top.geometry("300x350")
        top.grab_set() 
        tk.Label(top, text=f"Table: {table_name}", font=("Arial", 10, "bold")).pack(pady=10)
        lb = tk.Listbox(top, font=("Arial", 10))
        for col_name, col_type, desc in columns:
            lb.insert("end", f"{col_name} ({col_type})")

        def confirm():
            selection = lb.curselection()
            if selection:
                full_str = lb.get(selection[0])
                selected_col = full_str.split(" (")[0]
                selected_col_type = next(c[1] for c in columns if c[0] == selected_col)
                if step == 1:
                    self.parent.fk_data.update({"from_id": table_id, "from_col": selected_col, "from_type": selected_col_type})
                    self.parent.fk_step = 2
                    top.destroy()
                    msg = "Step 2: Select target table" if self.parent.lang == "EN" else "Крок 2: Оберіть цільову таблицю"
                    messagebox.showinfo("FK Mode", msg)
                else:
                    is_valid, err = validate_foreign_key_match(self.parent.fk_data["from_type"], selected_col_type)
                    if not is_valid:
                        messagebox.showerror("Error", err)
                        self.cancel_fk_mode()
                        top.destroy()
                        return
                    self.model.add_relation(self.parent.fk_data["from_id"], self.parent.fk_data["from_col"], table_id, selected_col)
                    self.parent.is_dirty = True
                    self.parent.refresh_canvas()
                    self.cancel_fk_mode(show_msg=False) 
                    top.destroy()
                    messagebox.showinfo("Success", "Relation created!" if self.parent.lang == "EN" else "Зв'язок створено!")
        btn_text = "Confirm" if self.parent.lang == "EN" else "Підтвердити"
        ttk.Button(top, text=btn_text, command=confirm).pack(pady=15)

class AppController:
    """Головний контролер системи"""
    def __init__(self, model, view):
        self.model = model
        self.view = view
        self.api_mgr = ApiManager(model, view)
        self.arch_mgr = ArchitectManager(model, view, self)

        self.lang = "UA"
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
        self.view.config(menu=menubar)

    def switch_language(self, lang):
        self.lang = lang
        dash = self.view.frames[DashboardFrame]
        if hasattr(dash, 'update_language_ui'): dash.update_language_ui(lang)
        self.view.title(f"DevHub Architect & API [{lang}]")

    def handle_register(self):
        login_fr = self.view.frames[LoginFrame]
        user = login_fr.reg_login_entry.get().strip()
        email_widget = getattr(login_fr, 'reg_email_entry', None)
        email = email_widget.get().strip() if email_widget else ""
        pwd = login_fr.reg_pass_entry.get().strip()
        
        if not user or not email or not pwd:
            messagebox.showwarning("Помилка", "Заповніть усі поля!")
            return
        if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
            messagebox.showerror("Помилка", "Некоректний формат Email!")
            return

        verification_code = str(random.randint(100000, 999999))
        messagebox.showinfo("Відправка", f"Відправляємо код підтвердження на {email}...\nБудь ласка, зачекайте.")
        self.view.update() 
        
        if self.send_verification_email(email, verification_code):
            user_code = simpledialog.askstring("Підтвердження", f"Код відправлено на {email}.\nВведіть 6-значний код:", parent=self.view)
            if user_code == verification_code:
                if self.model.register(user, email, pwd):
                    messagebox.showinfo("Успіх", "Акаунт успішно створено!")
                    login_fr.show_login_form()
                else: messagebox.showerror("Помилка", "Користувач вже існує.")
            elif user_code is not None:
                messagebox.showerror("Помилка", "Невірний код! Реєстрацію скасовано.")
        else: messagebox.showerror("Помилка SMTP", "Не вдалося відправити лист. Перевірте SMTP.")

    def send_verification_email(self, receiver_email, code):
        sender_email = "devhubapi@gmail.com" 
        sender_password = "unet lckv jkkk bhmd" 

        msg = MIMEText(f"Вітаємо у DevHub Architect!\n\nВаш код підтвердження: {code}")
        msg['Subject'] = 'Код підтвердження DevHub'
        msg['From'] = f"DevHub Admin <{sender_email}>"
        msg['To'] = receiver_email
        try:
            server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
            server.login(sender_email, sender_password)
            server.sendmail(sender_email, receiver_email, msg.as_string())
            server.quit()
            return True
        except Exception as e:
            print(f"SMTP Error: {e}")
            return False

    # --- ЕКСПОРТ З ШІ GEMINI ---
    def handle_export_sql(self):
        dialog = AISmartFillDialog(self.view, lang=self.lang)
        self.view.wait_window(dialog)
        
        ai_insert_script = ""
        if dialog.result:
            # 1. СТВОРЮЄМО КЛІЄНТА 
            client = genai.Client(api_key="AIzaSyDe8PZHFbCbzqiOJAXevzHEMBVMhvLrqOU")
            
            params = dialog.result
            tables = self.model.get_all_elements()
            
            messagebox.showinfo("AI Wizard", f"ШІ генерує дані. Будь ласка, зачекайте...")
            
            for t_id, t_name, _, _ in tables:
                cols = self.model.get_columns_for_table(t_id)
                cols_str = ", ".join([f"{c[0]} ({c[1]}{f', Опис: {c[2]}' if c[2] else ''})" for c in cols])
                
                prompt = f"""
                Ти — SQL розробник. Згенеруй ТОЧНО {params['count']} SQL INSERT запитів для таблиці '{t_name}'.
                Колонки: {cols_str}.
                Мова даних: {params['lang']}.
                Контекст/Тема: {params['context']}.
                Вимоги: 
                - Тільки чистий SQL код.
                - Дата у форматі 'YYYY-MM-DD HH:MM:SS'.
                - Реалістичні дані.
                - Без ```sql блоків.
                """
                try:
                    # 2. ВИКЛИК ГЕНЕРАЦІЇ
                    response = client.models.generate_content(
                        model='gemini-2.5-flash',
                        contents=prompt
                    )
                    ai_insert_script += f"\n-- AI Data for {t_name}\n{response.text.strip()}\n"
                except Exception as e:
                    ai_insert_script += f"\n-- AI Error for {t_name}: {str(e)}\n"

        # Формуємо фінальний файл
        sql_structure = self.model.generate_sql_script()
        final_code = sql_structure + "\n\n-- START AI GENERATED DATA --\n" + ai_insert_script
        
        path = filedialog.asksaveasfilename(defaultextension=".sql", initialfile="project_dump.sql")
        if path:
            with open(path, 'w', encoding='utf-8') as f:
                f.write(final_code)
            messagebox.showinfo("SQL", "Експорт структури та ШІ-даних завершено!")

    def handle_login(self):
        login_fr = self.view.frames[LoginFrame]
        uid = self.model.authenticate(login_fr.login_entry.get().strip(), login_fr.pass_entry.get().strip())
        if uid:
            self.current_user_id = uid
            self.view.show_frame(DashboardFrame)
            dash = self.view.frames[DashboardFrame]
            dash.project_listbox.bind("<<ListboxSelect>>", self.handle_load_project)
            dash.search_ent.bind("<KeyRelease>", lambda e: self.refresh_project_list())
            if hasattr(dash, 'p_menu'): dash.p_menu.entryconfigure(0, command=self.handle_delete_project)
            self.refresh_project_list()
            self.refresh_canvas()
        else: messagebox.showerror("Error", "Invalid credentials")

    def _show_context_menu(self, event):
        dash = self.view.frames[DashboardFrame]
        dash.project_listbox.selection_clear(0, tk.END)
        nearest = dash.project_listbox.nearest(event.y)
        if nearest >= 0:
            dash.project_listbox.selection_set(nearest)
            dash.p_menu.post(event.x_root, event.y_root)

    def handle_delete_project(self):
        dash = self.view.frames[DashboardFrame]
        selection = dash.project_listbox.curselection()
        if selection:
            text = dash.project_listbox.get(selection[0])
            p_id = int(text.split("ID:")[1].replace(")", ""))
            if messagebox.askyesno("Delete", "Delete project forever?"):
                self.model.delete_project(p_id)
                if self.current_project_id == p_id: self.current_project_id = None
                self.refresh_project_list()

    def handle_db_save(self):
        if not self.current_user_id: return
        name = simpledialog.askstring("Save", "Project Name:", initialvalue="My Project") if not self.current_project_id else "Updated"
        if not name and not self.current_project_id: return
        self.current_project_id = self.model.save_project_to_db(self.current_user_id, name, self.model.get_current_canvas_data(), self.current_project_id)
        self.is_dirty = False
        self.refresh_project_list()
        messagebox.showinfo("OK", "Saved to cloud")

    def refresh_project_list(self):
        dash = self.view.frames[DashboardFrame]
        dash.project_listbox.delete(0, tk.END)
        for p_id, p_name, p_date in self.model.get_user_projects(self.current_user_id, dash.search_ent.get()):
            dash.project_listbox.insert(tk.END, f"{p_name} (ID:{p_id})")

    def handle_load_project(self, event):
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
        path = filedialog.asksaveasfilename(defaultextension=".json")
        if path: self.model.export_to_json(path); self.is_dirty = False

    def handle_open_file(self):
        if not check_unsaved_changes(self.is_dirty): return
        path = filedialog.askopenfilename()
        if path:
            self.model.import_from_json(path)
            self.current_project_id = None; self.is_dirty = False; self.refresh_canvas()

    def handle_new_project(self):
        if not check_unsaved_changes(self.is_dirty): return
        if messagebox.askyesno("New", "Clear workspace?"):
            self.current_project_id = None; self.model.clear_all_data(); self.is_dirty = False; self.refresh_canvas()

    def refresh_canvas(self):
        dash_fr = self.view.frames[DashboardFrame]
        dash_fr.canvas.delete("all")
        if hasattr(dash_fr, '_draw_grid'): dash_fr._draw_grid()
        for t_id, name, x, y in self.model.get_all_elements():
            dash_fr.draw_table(t_id, name, x, y, columns=self.model.get_columns_for_table(t_id))
        self.refresh_lines()

    def refresh_lines(self):
        dash_fr = self.view.frames[DashboardFrame]
        dash_fr.canvas.delete("connection")
        for f_id, f_col, t_id, t_col in self.model.get_relations():
            dash_fr.draw_connection(f_id, f_col, self.model.get_columns_for_table(f_id), t_id, t_col, self.model.get_columns_for_table(t_id))

    def _setup_canvas_bindings(self):
        dash_fr = self.view.frames[DashboardFrame]
        dash_fr.canvas.bind("<Button-1>", self.on_canvas_click)
        dash_fr.canvas.bind("<B1-Motion>", self.on_drag_motion)
        dash_fr.canvas.bind("<ButtonRelease-1>", self.on_drag_stop)
        dash_fr.canvas.bind("<Double-Button-1>", self.on_table_double_click)
        dash_fr.canvas.bind("<Button-3>", self.show_table_context_menu)

    def show_table_context_menu(self, event):
        canvas = event.widget
        item = canvas.find_closest(event.x, event.y)
        tags = canvas.gettags(item)
        if "table" in tags:
            table_id = tags[0]
            menu = tk.Menu(self.view, tearoff=0)
            txt = {"edit": "📝 Редагувати" if self.lang == "UA" else "📝 Edit", "del": "❌ Видалити" if self.lang == "UA" else "❌ Delete"}
            menu.add_command(label=txt["edit"], command=lambda: self.on_table_double_click(event))
            menu.add_command(label=txt["del"], command=lambda: self.delete_table_action(table_id))
            menu.post(event.x_root, event.y_root)

    def delete_table_action(self, table_uuid):
        if messagebox.askyesno("Confirm", "Видалити таблицю?"):
            with self.model._get_connection() as conn:
                conn.execute("DELETE FROM canvas_elements WHERE uuid = ?", (table_uuid,))
                conn.commit()
            self.refresh_canvas()

    def on_canvas_click(self, event):
        item = event.widget.find_closest(event.x, event.y)
        tags = event.widget.gettags(item)
        if "table" in tags:
            table_id = tags[0]
            if self.fk_step in [1, 2]:
                all_t = self.model.get_all_elements()
                t_name = next((t[1] for t in all_t if t[0] == table_id), "Table")
                self.arch_mgr._select_column_for_fk(table_id, t_name, self.fk_step)
                return
            self.drag_data = {"item": table_id, "x": event.x, "y": event.y}
    
    def on_drag_motion(self, event):
        if self.drag_data:
            event.widget.move(self.drag_data["item"], event.x - self.drag_data["x"], event.y - self.drag_data["y"])
            self.refresh_lines(); self.drag_data.update({"x": event.x, "y": event.y}); self.is_dirty = True 

    def on_drag_stop(self, event):
        if self.drag_data:
            items = event.widget.find_withtag(self.drag_data["item"])
            if items:
                coords = event.widget.coords(items[0])
                self.model.update_element_pos(self.drag_data["item"], coords[0], coords[1])
            self.drag_data = None

    def on_table_double_click(self, event):
        item = event.widget.find_closest(event.x, event.y)
        tags = event.widget.gettags(item)
        if "table" in tags:
            t_uuid = tags[0]
            top = tk.Toplevel(self.view)
            top.title("Add Field"); top.geometry("300x250"); top.grab_set()
            tk.Label(top, text="Field Name:").pack()
            name_ent = ttk.Entry(top); name_ent.pack()
            tk.Label(top, text="Type:").pack()
            type_cb = ttk.Combobox(top, values=["INTEGER", "TEXT", "REAL", "DATETIME"], state="readonly")
            type_cb.set("TEXT"); type_cb.pack()
            is_pk = tk.BooleanVar()
            tk.Checkbutton(top, text="PK?", variable=is_pk).pack()
            tk.Label(top, text="Description (for AI):").pack(pady=5)
            desc_ent = ttk.Entry(top, width=25)
            desc_ent.pack()

            def save():
                name = name_ent.get().strip()
                desc = desc_ent.get().strip()
                if not name: return
                is_valid, err = validate_sql_name(name)
                if not is_valid: return messagebox.showerror("Error", err)
                tp = type_cb.get()
                if is_pk.get():
                    can, err_pk = can_add_primary_key(self.model.get_columns_for_table(t_uuid))
                    if not can: return messagebox.showerror("Error", err_pk)
                    tp += " PRIMARY KEY"
                self.model.add_column(t_uuid, name, tp, description=desc)
                self.is_dirty = True; self.refresh_canvas(); top.destroy()
            ttk.Button(top, text="Save", command=save).pack()

    def _setup_bindings(self):
        dash_fr = self.view.frames[DashboardFrame]
        dash_fr.btn_send.config(command=self.api_mgr.handle_request)
        dash_fr.btn_add_table.config(command=self.arch_mgr.handle_add_table)
        dash_fr.btn_fk.config(command=self.arch_mgr.handle_fk_setup)
        dash_fr.btn_save.config(command=self.handle_save_file)
        dash_fr.btn_open.config(command=self.handle_open_file)
        dash_fr.btn_new.config(command=self.handle_new_project)
        dash_fr.btn_export_sql.config(command=self.handle_export_sql)
        dash_fr.btn_db_save.config(command=self.handle_db_save)