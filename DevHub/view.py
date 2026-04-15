import tkinter as tk
from tkinter import ttk

class MainView(tk.Tk):
    """Головне вікно програми. Ініціалізує базові налаштування екрану та контейнери для фреймів."""
    def __init__(self):
        super().__init__()
        self.title("DevHub Architect & API")
        self.geometry("1200x800")
        self.configure(bg="#0d1117")

        self.container = tk.Frame(self)
        self.container.pack(fill="both", expand=True)

        self.frames = {}
        for F in (LoginFrame, DashboardFrame):
            frame = F(parent=self.container, controller=self)
            self.frames[F] = frame
            frame.grid(row=0, column=0, sticky="nsew")

        self.container.grid_rowconfigure(0, weight=1)
        self.container.grid_columnconfigure(0, weight=1)
        self.show_frame(LoginFrame)

    def show_frame(self, frame_class):
        """Перемикає видимість фреймів (наприклад, з екрану логіну на дашборд)."""
        frame = self.frames[frame_class]
        frame.tkraise()

    def start(self):
        """Запускає головний цикл подій Tkinter."""
        self.mainloop()

# --- БАЗОВІ КАСТОМНІ ВІКНА ---

class CustomDialog(tk.Toplevel):
    """Базовий клас для стильних діалогових вікон. Автоматично центрується на екрані та блокує головне вікно."""
    def __init__(self, parent, title="DevHub", width=350, height=200):
        super().__init__(parent)
        self.title(title)
        self.geometry(f"{width}x{height}")
        self.configure(bg="#161b22")
        self.resizable(False, False)
        self.transient(parent) 
        self.grab_set()        
        
        self.update_idletasks()
        x = (self.winfo_screenwidth() // 2) - (width // 2)
        y = (self.winfo_screenheight() // 2) - (height // 2)
        self.geometry(f"+{x}+{y}")

class ProgressDialog(CustomDialog):
    """Вікно завантаження з анімацією. Використовується під час тривалих процесів (наприклад, звернення до ШІ)."""
    def __init__(self, parent, message="Обробка даних..."):
        super().__init__(parent, title="Processing", width=400, height=150)
        
        container = tk.Frame(self, bg="#161b22", padx=20, pady=20)
        container.pack(fill="both", expand=True)

        tk.Label(container, text="✨", font=("Arial", 24), bg="#161b22", fg="#4ade80").pack()
        tk.Label(container, text=message, font=("Segoe UI", 11), bg="#161b22", fg="white").pack(pady=10)
        
        self.progress = ttk.Progressbar(container, orient="horizontal", length=300, mode="indeterminate")
        self.progress.pack(pady=5)
        self.progress.start(10)

    def close(self):
        """Зупиняє анімацію і закриває вікно завантаження."""
        self.progress.stop()
        self.destroy()

class VerificationDialog(CustomDialog):
    """Вікно для введення 6-значного коду верифікації, що надсилається на email."""
    def __init__(self, parent, email):
        super().__init__(parent, title="Підтвердження Email", width=350, height=230)
        self.result = None
        
        container = tk.Frame(self, bg="#161b22", padx=25, pady=20)
        container.pack(fill="both", expand=True)

        tk.Label(container, text="📧 Код відправлено!", font=("Segoe UI", 12, "bold"), bg="#161b22", fg="#4ade80").pack()
        tk.Label(container, text=f"Введіть 6-значний код з пошти\n{email}", font=("Segoe UI", 9), bg="#161b22", fg="#8b949e").pack(pady=5)

        self.code_entry = tk.Entry(container, bg="#0d1117", fg="white", font=("Arial", 16, "bold"), 
                                  insertbackground="white", justify="center", bd=1, relief="solid")
        self.code_entry.pack(fill="x", pady=15, ipady=5)
        self.code_entry.focus()

        btn = tk.Button(container, text="ПЕРЕВІРИТИ", bg="#238636", fg="white", font=("Segoe UI", 10, "bold"),
                        bd=0, pady=8, cursor="hand2", command=self.confirm)
        btn.pack(fill="x")

    def confirm(self):
        """Зберігає введений код і закриває вікно."""
        self.result = self.code_entry.get().strip()
        self.destroy()

class MessageDialog(CustomDialog):
    """Кастомна заміна стандартним сірим вікнам (messagebox). Має різні кольори для помилок, інфо та успіху."""
    def __init__(self, parent, title, message, m_type="info"):
        super().__init__(parent, title=title, width=380, height=180)
        
        container = tk.Frame(self, bg="#161b22", padx=20, pady=20)
        container.pack(fill="both", expand=True)
        
        colors = {"info": "#58a6ff", "error": "#f85149", "success": "#4ade80"}
        icons = {"info": "ℹ️", "error": "❌", "success": "✅"}
        
        top_frame = tk.Frame(container, bg="#161b22")
        top_frame.pack(fill="x")
        
        tk.Label(top_frame, text=icons.get(m_type, "ℹ️"), font=("Arial", 20), bg="#161b22", fg=colors.get(m_type, "white")).pack(side="left", padx=(0, 10))
        tk.Label(top_frame, text=title, font=("Segoe UI", 12, "bold"), bg="#161b22", fg=colors.get(m_type, "white")).pack(side="left")
        
        tk.Label(container, text=message, font=("Segoe UI", 10), bg="#161b22", fg="#c9d1d9", wraplength=320, justify="left").pack(anchor="w", pady=15)
        
        btn = tk.Button(container, text="ОК", bg="#21262d", fg="white", font=("Segoe UI", 10), bd=0, padx=20, pady=5, cursor="hand2", command=self.destroy)
        btn.pack(side="right")

# --- РОБОЧІ ВІКНА ПРОГРАМИ ---

class AISmartFillDialog(tk.Toplevel):
    """Вікно налаштувань для генерації даних за допомогою ШІ."""
    def __init__(self, parent, lang="UA", default_dialect="PostgreSQL"):
        super().__init__(parent)
        self.result = None
        self.grab_set()
        
        self.title("AI Smart Data Generator ✨")
        self.geometry("400x570") 
        self.resizable(False, False)
        self.configure(bg="#161b22")

        container = tk.Frame(self, bg="#161b22", padx=20, pady=20)
        container.pack(fill="both", expand=True)

        tk.Label(container, text="Smart Data Export", font=("Segoe UI", 14, "bold"), bg="#161b22", fg="#4ade80").pack(pady=(0, 20))

        tk.Label(container, text="База даних (Діалект) / SQL Dialect:", bg="#161b22", fg="white").pack(anchor="w")
        self.dialect_var = tk.StringVar(value=default_dialect)
        self.combo_dialect = ttk.Combobox(container, textvariable=self.dialect_var, values=["PostgreSQL", "MySQL", "SQLite", "Oracle"], state="readonly")
        self.combo_dialect.pack(fill="x", pady=(5, 15))

        tk.Label(container, text="Мова даних / Data Language:", bg="#161b22", fg="white").pack(anchor="w")
        self.lang_var = tk.StringVar(value="Українська")
        self.combo_lang = ttk.Combobox(container, textvariable=self.lang_var, values=["Українська", "English", "Deutsch"], state="readonly")
        self.combo_lang.pack(fill="x", pady=(5, 15))

        tk.Label(container, text="Кількість рядків (на таблицю):", bg="#161b22", fg="white").pack(anchor="w")
        self.count_var = tk.IntVar(value=5)
        self.slider = tk.Scale(container, from_=1, to=50, orient="horizontal", variable=self.count_var, 
                               bg="#161b22", fg="white", highlightthickness=0, troughcolor="#30363d", activebackground="#4ade80")
        self.slider.pack(fill="x", pady=(5, 15))

        tk.Label(container, text="Додаткові побажання (фільтри/тема):", bg="#161b22", fg="white").pack(anchor="w")
        self.context_text = tk.Text(container, height=4, bg="#0d1117", fg="white", insertbackground="white", bd=1, relief="solid")
        self.context_text.insert("1.0", "Реальні імена, ціни в гривнях, без нецензурної лексики")
        self.context_text.pack(fill="both", expand=True, pady=(5, 20))

        btn_fr = tk.Frame(container, bg="#161b22")
        btn_fr.pack(fill="x")
        
        self.btn_run = tk.Button(btn_fr, text="Запустити ШІ ✨", bg="#238636", fg="white", font=("Segoe UI", 10, "bold"),
                                 bd=0, padx=20, pady=10, cursor="hand2", command=self.confirm)
        self.btn_run.pack(side="right")
        
        self.btn_skip = tk.Button(btn_fr, text="Лише структура", bg="#30363d", fg="white", font=("Segoe UI", 10),
                                  bd=0, padx=20, pady=10, cursor="hand2", command=self.destroy)
        self.btn_skip.pack(side="left")

    def confirm(self):
        """Збирає всі налаштування генерації у словник та передає контролеру."""
        self.result = {
            "lang": self.lang_var.get(),
            "count": self.count_var.get(),
            "context": self.context_text.get("1.0", "end-1c"),
            "dialect": self.dialect_var.get()
        }
        self.destroy()

class TableManagerDialog(CustomDialog):
    """Повноцінний редактор таблиці. Показує список колонок і дозволяє їх додавати, змінювати або видаляти."""
    def __init__(self, parent, table_name, columns):
        super().__init__(parent, title=f"Налаштування: {table_name}", width=450, height=350)
        self.action = None
        self.data = None
        
        container = tk.Frame(self, bg="#161b22", padx=20, pady=20)
        container.pack(fill="both", expand=True)
        
        tk.Label(container, text="Поля таблиці:", font=("Segoe UI", 12, "bold"), bg="#161b22", fg="white").pack(anchor="w", pady=(0, 10))
        
        self.lb = tk.Listbox(container, bg="#0d1117", fg="#c9d1d9", font=("Segoe UI", 10), 
                             bd=1, relief="solid", selectbackground="#1f6feb", selectforeground="white")
        self.lb.pack(fill="both", expand=True, pady=5)
        
        for c in columns:
            prefix = "🔑 " if "PRIMARY KEY" in c[1].upper() else "• "
            self.lb.insert("end", f"{prefix}{c[0]}  |  {c[1]}")
            
        btn_fr = tk.Frame(container, bg="#161b22")
        btn_fr.pack(fill="x", pady=10)
        
        tk.Button(btn_fr, text="➕ Додати", bg="#238636", fg="white", bd=0, padx=15, pady=5, cursor="hand2", command=self.add_f).pack(side="left")
        tk.Button(btn_fr, text="✏️ Редагувати", bg="#1f6feb", fg="white", bd=0, padx=15, pady=5, cursor="hand2", command=self.edit_f).pack(side="left", padx=10)
        tk.Button(btn_fr, text="❌ Видалити", bg="#f85149", fg="white", bd=0, padx=15, pady=5, cursor="hand2", command=self.del_f).pack(side="right")

    def add_f(self):
        """Встановлює дію 'add' і закриває вікно, щоб контролер викликав ColumnDialog."""
        self.action = "add"
        self.destroy()

    def edit_f(self):
        """Витягує назву обраної колонки для подальшого редагування."""
        sel = self.lb.curselection()
        if sel:
            raw_text = self.lb.get(sel[0])
            self.data = raw_text.replace("🔑 ", "").replace("• ", "").split("  |  ")[0]
            self.action = "edit"
            self.destroy()

    def del_f(self):
        """Витягує назву обраної колонки для подальшого видалення."""
        sel = self.lb.curselection()
        if sel:
            raw_text = self.lb.get(sel[0])
            self.data = raw_text.replace("🔑 ", "").replace("• ", "").split("  |  ")[0]
            self.action = "delete"
            self.destroy()


class ColumnDialog(CustomDialog):
    """Вікно для створення нового поля або редагування існуючого (назва, тип, розмір, опис)."""
    def __init__(self, parent, lang="UA", edit_data=None):
        title = "Редагувати поле" if edit_data else "Нове поле"
        super().__init__(parent, title=title, width=380, height=300) 
        self.result = None
        
        container = tk.Frame(self, bg="#161b22", padx=20, pady=20)
        container.pack(fill="both", expand=True)

        tk.Label(container, text="Назва поля:", font=("Arial", 10), bg="#161b22", fg="white").pack(anchor="w")
        self.entry_name = ttk.Entry(container, width=40)
        self.entry_name.pack(pady=(5, 10))
        self.entry_name.focus()

        type_frame = tk.Frame(container, bg="#161b22")
        type_frame.pack(fill="x", pady=5)
        tk.Label(type_frame, text="Тип:", font=("Arial", 10), bg="#161b22", fg="white").pack(side="left")
        tk.Label(type_frame, text="Розмір (напр. 64):", font=("Arial", 10), bg="#161b22", fg="#8b949e").pack(side="right", padx=(0, 20))
        
        inputs_frame = tk.Frame(container, bg="#161b22")
        inputs_frame.pack(fill="x")
        self.type_combo = ttk.Combobox(inputs_frame, values=["INTEGER", "VARCHAR", "TEXT", "REAL", "DATETIME", "BOOLEAN"], width=20, state="readonly")
        self.type_combo.set("VARCHAR")
        self.type_combo.pack(side="left")
        
        self.entry_size = ttk.Entry(inputs_frame, width=10)
        self.entry_size.pack(side="right", padx=(0, 20))

        tk.Label(container, text="Опис (для ШІ):", font=("Arial", 10), bg="#161b22", fg="white").pack(anchor="w", pady=(15, 0))
        self.entry_desc = ttk.Entry(container, width=40)
        self.entry_desc.pack(pady=5)

        btn_frame = tk.Frame(container, bg="#161b22")
        btn_frame.pack(pady=15)
        self.btn_ok = tk.Button(btn_frame, text="Зберегти", bg="#238636", fg="white", bd=0, padx=20, pady=5, cursor="hand2", command=self.on_ok)
        self.btn_ok.pack(side="left", padx=10)
        self.btn_cancel = tk.Button(btn_frame, text="Скасувати", bg="#30363d", fg="white", bd=0, padx=20, pady=5, cursor="hand2", command=self.destroy)
        self.btn_cancel.pack(side="left", padx=10)

        # Якщо ми редагуємо поле — підтягуємо старі дані у віджети
        if edit_data:
            self.entry_name.insert(0, edit_data[0])
            full_type = edit_data[1]
            if "(" in full_type:
                self.type_combo.set(full_type.split("(")[0])
                self.entry_size.insert(0, full_type.split("(")[1].replace(")", ""))
            else:
                self.type_combo.set(full_type.split()[0])
            if edit_data[2]:
                self.entry_desc.insert(0, edit_data[2])

    def on_ok(self):
        """Збирає введені дані, валідує їх на наявність розміру і повертає як кортеж."""
        name = self.entry_name.get().strip()
        desc = self.entry_desc.get().strip()
        tp = self.type_combo.get()
        sz = self.entry_size.get().strip()
        
        # Об'єднуємо тип і розмір, якщо це необхідно
        if tp == "VARCHAR" and sz.isdigit():
            tp = f"VARCHAR({sz})"
            
        if name:
            self.result = (name, tp, desc)
            self.destroy()

class LoginFrame(tk.Frame):
    """Фрейм сторінки авторизації та реєстрації."""
    def __init__(self, parent, controller):
        super().__init__(parent, bg="#0d1117")
        self.controller = controller

        self.canvas = tk.Canvas(self, highlightthickness=0, bg="#0d1117")
        self.canvas.pack(fill="both", expand=True)

        try:
            self.bg_image = tk.PhotoImage(file="img/Main_bg.png")
            self.canvas.create_image(600, 400, image=self.bg_image, anchor="center")
        except:
            self.canvas.create_oval(100, 100, 300, 300, outline="#1a1f2e", width=2)
            self.canvas.create_oval(800, 500, 1100, 800, outline="#1a1f2e", width=2)

        self._draw_rounded_rect(410, 140, 790, 660, 30, fill="#161b22", outline="#4ade80", width=1)

        self.form_container = tk.Frame(self.canvas, bg="#161b22", padx=30)
        self.canvas.create_window(600, 415, window=self.form_container, width=320, height=480)

        self.show_login_form()

    def show_login_form(self):
        """Очищає форму та будує інтерфейс для входу (логіну)."""
        for widget in self.form_container.winfo_children():
            widget.destroy()

        tk.Label(self.form_container, text="🌿", font=("Arial", 45), bg="#161b22", fg="#4ade80").pack(pady=(10, 0))
        tk.Label(self.form_container, text="DevHub Architect & API", font=("Segoe UI", 16, "bold"), bg="#161b22", fg="white").pack(pady=(5, 2))
        tk.Label(self.form_container, text="Login / Register", font=("Segoe UI", 10), bg="#161b22", fg="#8b949e").pack(pady=(0, 20))

        self.tabs_fr = tk.Frame(self.form_container, bg="#161b22")
        self.tabs_fr.pack(fill="x", pady=10)
        
        self.btn_l = tk.Label(self.tabs_fr, text="Login", font=("Segoe UI", 10, "bold"), bg="#161b22", fg="#4ade80", cursor="hand2")
        self.btn_l.pack(side="left", expand=True)
        self.btn_r = tk.Label(self.tabs_fr, text="Register", font=("Segoe UI", 10), bg="#161b22", fg="#8b949e", cursor="hand2")
        self.btn_r.pack(side="left", expand=True)
        self.btn_r.bind("<Button-1>", lambda e: self.show_register_form())

        self.login_entry = self._create_input("👤 Username or Email", False)
        self.pass_entry = self._create_input("🔒 Password", True)

        self.btn_login = tk.Button(self.form_container, text="Login", font=("Segoe UI", 12, "bold"),
                                   bg="#1ba976", fg="white", activebackground="#14835b", 
                                   activeforeground="white", bd=0, cursor="hand2", pady=10)
        self.btn_login.pack(fill="x", pady=(20, 10))
        self.btn_login.config(command=lambda: self.controller.app_logic.handle_login())

        # ОНОВЛЕНО: Прив'язка функції відновлення пароля
        self.lbl_forgot = tk.Label(self.form_container, text="Forgot Password?", font=("Segoe UI", 9), 
                                   bg="#161b22", fg="#8b949e", cursor="hand2")
        self.lbl_forgot.pack()
        self.lbl_forgot.bind("<Button-1>", lambda e: self.controller.app_logic.handle_forgot_password())

    def show_register_form(self):
        """Очищає форму та будує інтерфейс для реєстрації."""
        for widget in self.form_container.winfo_children():
            widget.destroy()
            
        tk.Label(self.form_container, text="📝", font=("Arial", 40), bg="#161b22", fg="#58a6ff").pack()
        tk.Label(self.form_container, text="Create Account", font=("Segoe UI", 18, "bold"), bg="#161b22", fg="white").pack(pady=10)

        self.reg_login_entry = self._create_input("👤 Username", False)
        self.reg_email_entry = self._create_input("📧 Email", False)
        self.reg_pass_entry = self._create_input("🔒 Password", True)

        self.btn_reg = tk.Button(self.form_container, text="Register", font=("Segoe UI", 12, "bold"),
                                 bg="#454173", fg="white", bd=0, cursor="hand2", pady=10)
        self.btn_reg.pack(fill="x", pady=20)
        self.btn_reg.config(command=lambda: self.controller.app_logic.handle_register())
        
        btn_back = tk.Label(self.form_container, text="← Back to Login", bg="#161b22", fg="#8b949e", cursor="hand2")
        btn_back.pack()
        btn_back.bind("<Button-1>", lambda e: self.show_login_form())

    def _draw_rounded_rect(self, x1, y1, x2, y2, r, **kwargs):
        points = [x1+r, y1, x1+r, y1, x2-r, y1, x2-r, y1, x2, y1, x2, y1+r, x2, y1+r, x2, y2-r, x2, y2-r, x2, y2, x2-r, y2, x2-r, y2, x1+r, y2, x1+r, y2, x1, y2, x1, y2-r, x1, y2-r, x1, y1+r, x1, y1+r, x1, y1]
        return self.canvas.create_polygon(points, **kwargs, smooth=True)

    def _create_input(self, placeholder, is_pass):
        """Створює стилізоване поле введення з підтримкою placeholder-у."""
        container = tk.Frame(self.form_container, bg="#1f2430", highlightthickness=1, 
                             highlightbackground="#30363d", padx=10, pady=7)
        container.pack(fill="x", pady=5)
        ent = tk.Entry(container, bg="#1f2430", fg="white", insertbackground="#4ade80", font=("Segoe UI", 11), bd=0)
        if is_pass: ent.config(show="*")
        ent.insert(0, placeholder)
        
        def on_focus(e):
            container.config(highlightbackground="#4ade80")
            if ent.get() == placeholder:
                ent.delete(0, "end")
                if is_pass: ent.config(show="*")
        def on_focus_out(e):
            container.config(highlightbackground="#30363d")
            if not ent.get():
                if is_pass: ent.config(show="")
                ent.insert(0, placeholder)
                
        if is_pass: ent.config(show="")
        ent.bind("<FocusIn>", on_focus)
        ent.bind("<FocusOut>", on_focus_out)
        ent.pack(fill="x")
        return ent

class DashboardFrame(tk.Frame):
    """Головний фрейм програми, що містить робочий простір (Architect) та бічну панель з проєктами."""
    def __init__(self, parent, controller):
        super().__init__(parent, bg="#0d1117")
        self.controller = controller
        
        self.toolbar = tk.Frame(self, bg="#161b22", height=50, bd=1, relief="flat")
        self.toolbar.pack(side="top", fill="x")

        btn_style = {"bg": "#21262d", "fg": "#c9d1d9", "bd": 0, "padx": 10, "pady": 5, "activebackground": "#30363d", "activeforeground": "white", "cursor": "hand2"}

        self.btn_toggle_sidebar = tk.Button(self.toolbar, text="☰", command=self.toggle_sidebar, **btn_style)
        self.btn_toggle_sidebar.pack(side="left", padx=5, pady=8)

        self.btn_new = tk.Button(self.toolbar, text="📄 Новий", **btn_style)
        self.btn_new.pack(side="left", padx=2, pady=8)
        self.btn_open = tk.Button(self.toolbar, text="📂 Відкрити", **btn_style)
        self.btn_open.pack(side="left", padx=2, pady=8)
        self.btn_save = tk.Button(self.toolbar, text="💾 Зберегти (JSON)", **btn_style)
        self.btn_save.pack(side="left", padx=2, pady=8)
        self.btn_db_save = tk.Button(self.toolbar, text="☁️ В хмару", **btn_style)
        self.btn_db_save.pack(side="left", padx=2, pady=8)

        tk.Frame(self.toolbar, width=1, bg="#30363d").pack(side="left", fill="y", padx=10, pady=10)

        self.btn_add_table = tk.Button(self.toolbar, text="＋ Таблиця", **btn_style)
        self.btn_add_table.pack(side="left", padx=2, pady=8)
        
        self.btn_fk = tk.Button(self.toolbar, text="🔗 Foreign Key", **btn_style)
        self.btn_fk.pack(side="left", padx=2, pady=8)

        export_style = btn_style.copy()
        export_style.update({"bg": "#238636", "fg": "white"}) 
        self.btn_export_sql = tk.Button(self.toolbar, text="⚡ Експорт SQL", **export_style)
        self.btn_export_sql.pack(side="right", padx=10, pady=8)

        excel_style = btn_style.copy()
        excel_style.update({"bg": "#1f6feb", "fg": "white"}) 
        self.btn_export_excel = tk.Button(self.toolbar, text="📊 Структура (Excel)", **excel_style)
        self.btn_export_excel.pack(side="right", padx=(10, 0), pady=8)

        self.main_content = tk.Frame(self, bg="#0d1117")
        self.main_content.pack(fill="both", expand=True)

        self.sidebar = tk.Frame(self.main_content, width=220, bg="#0d1117", bd=0)
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)

        self.lbl_search_title = tk.Label(self.sidebar, text="ПОШУК ПРОЕКТІВ", font=("Segoe UI", 8, "bold"), bg="#0d1117", fg="#8b949e")
        self.lbl_search_title.pack(pady=(15, 2))
        
        self.search_ent = tk.Entry(self.sidebar, bg="#161b22", fg="white", bd=1, insertbackground="white", relief="solid")
        self.search_ent.pack(fill="x", padx=10, pady=5, ipady=3)

        self.lbl_my_projects = tk.Label(self.sidebar, text="МОЇ ПРОЕКТИ", font=("Segoe UI", 9, "bold"), bg="#0d1117", fg="#8b949e")
        self.lbl_my_projects.pack(pady=(15, 5))
        
        self.list_container = tk.Frame(self.sidebar, bg="#0d1117")
        self.list_container.pack(fill="both", expand=True, padx=10, pady=10)

        self.project_listbox = tk.Listbox(self.list_container, bg="#161b22", fg="#c9d1d9", bd=1, relief="solid", font=("Segoe UI", 10), 
                                         highlightthickness=0, selectbackground="#1f6feb", selectforeground="white")
        self.project_listbox.pack(side="left", fill="both", expand=True)

        self.project_scroll = ttk.Scrollbar(self.list_container, orient="vertical", command=self.project_listbox.yview)
        self.project_scroll.pack(side="right", fill="y")
        self.project_listbox.config(yscrollcommand=self.project_scroll.set)
        
        self.p_menu = tk.Menu(self, tearoff=0, bg="#161b22", fg="white")
        self.p_menu.add_command(label="Видалити проект")

        self.notebook = ttk.Notebook(self.main_content)
        self.notebook.pack(side="left", fill="both", expand=True)

        self.canvas_frame = tk.Frame(self.notebook, bg="#0d1117")
        self.canvas = tk.Canvas(self.canvas_frame, bg="#0d1117", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)

        self.api_frame = tk.Frame(self.notebook, bg="#0d1117")
        self._setup_api_ui()

        self.notebook.add(self.canvas_frame, text="📐 Database Architect")
        self.notebook.add(self.api_frame, text="🌐 API Client")
        
        self.sidebar_visible = True
        self._draw_grid()

    def update_language_ui(self, lang):
        """Оновлює текстові лейбли на обрану мову."""
        t = {
            "UA": {"new": "📄 Новий", "open": "📂 Відкрити", "save": "💾 Зберегти (JSON)", "cloud": "☁️ В хмару", "tab": "＋ Таблиця", "fk": "🔗 Foreign Key", "export": "⚡ Експорт SQL", "export_ex": "📊 Структура (Excel)", "search": "ПОШУК ПРОЕКТІВ", "my_projs": "МОЇ ПРОЕКТИ", "arch_tab": "📐 Database Architect", "api_tab": "🌐 API Client", "del_proj": "Видалити проект", "url": "URL:", "send": "Send Request"},
            "EN": {"new": "📄 New", "open": "📂 Open", "save": "💾 Save (JSON)", "cloud": "☁️ Cloud Save", "tab": "＋ Table", "fk": "🔗 Relation", "export": "⚡ Export SQL", "export_ex": "📊 Structure (Excel)", "search": "SEARCH PROJECTS", "my_projs": "MY PROJECTS", "arch_tab": "📐 Architect", "api_tab": "🌐 API Client", "del_proj": "Delete Project", "url": "URL:", "send": "Send Request"}
        }.get(lang, "UA")
        
        self.btn_new.config(text=t["new"]); self.btn_open.config(text=t["open"]); self.btn_save.config(text=t["save"])
        self.btn_db_save.config(text=t["cloud"]); self.btn_add_table.config(text=t["tab"]); self.btn_fk.config(text=t["fk"])
        self.btn_export_sql.config(text=t["export"]); self.lbl_search_title.config(text=t["search"])
        self.btn_export_excel.config(text=t["export_ex"])
        self.lbl_my_projects.config(text=t["my_projs"]); self.notebook.tab(0, text=t["arch_tab"])
        self.notebook.tab(1, text=t["api_tab"]); self.p_menu.entryconfigure(0, label=t["del_proj"])
        self.lbl_url.config(text=t["url"]); self.btn_send.config(text=t["send"])

    def set_fk_button_state(self, active=False):
        """Підсвічує кнопку FK синім кольором під час створення зв'язку."""
        if active:
            self.btn_fk.configure(bg="#1f6feb", fg="white") 
        else:
            self.btn_fk.configure(bg="#21262d", fg="#c9d1d9")

    def _draw_grid(self):
        """Малює фонову розмітку (сітку) на канвасі."""
        self.canvas.delete("grid")
        for i in range(0, 2000, 25):
            self.canvas.create_line(i, 0, i, 2000, fill="#161b22", tags="grid") 
            self.canvas.create_line(0, i, 2000, i, fill="#161b22", tags="grid")
        self.canvas.tag_lower("grid")

    def toggle_sidebar(self):
        """Ховає або показує бічну панель зі списком проєктів."""
        if self.sidebar_visible: self.sidebar.pack_forget()
        else: self.sidebar.pack(side="left", fill="y", before=self.notebook)
        self.sidebar_visible = not self.sidebar_visible

    def _setup_api_ui(self):
        """Ініціалізує інтерфейс для вкладки API Client."""
        top_bar = tk.Frame(self.api_frame, pady=10, bg="#161b22")
        top_bar.pack(fill="x")
        self.lbl_url = tk.Label(top_bar, text="URL:", bg="#161b22", fg="white")
        self.lbl_url.pack(side="left", padx=10)
        self.url_entry = ttk.Entry(top_bar, width=80)
        self.url_entry.pack(side="left", padx=5, fill="x", expand=True)
        self.btn_send = tk.Button(top_bar, text="Send Request", bg="#238636", fg="white", bd=0, padx=15, pady=5, cursor="hand2")
        self.btn_send.pack(side="left", padx=10)
        self.api_progress = ttk.Progressbar(self.api_frame, orient="horizontal", mode="indeterminate")
        self.result_text = tk.Text(self.api_frame, bg="#0d1117", fg="#4ade80", font=("Consolas", 11), insertbackground="white", bd=0)
        self.result_text.pack(fill="both", expand=True, padx=10, pady=10)

    def draw_table(self, table_id, name, x, y, columns=None):
        """Малює візуальне представлення таблиці та її полів на канвасі."""
        self.canvas.delete(table_id)

        width, header_h, row_h = 160, 30, 25
        total_h = header_h + (len(columns) if columns else 1) * row_h + 5
        
        self.canvas.create_rectangle(x+2, y+2, x+width+2, y+total_h+2, fill="#000000", outline="", tags=(table_id, "table"))
        self.canvas.create_rectangle(x, y, x+width, y+total_h, fill="#161b22", outline="#30363d", tags=(table_id, "table"))
        self.canvas.create_rectangle(x, y, x+width, y+header_h, fill="#21262d", outline="#30363d", tags=(table_id, "table"))
        self.canvas.create_text(x+width/2, y+header_h/2, text=name.upper(), fill="#58a6ff", font=("Segoe UI", 9, "bold"), tags=(table_id, "table"))
        
        if columns:
             for i, (col_name, col_type, desc) in enumerate(columns):
                 prefix = "🔑 " if "PRIMARY KEY" in col_type.upper() else "• "
                 self.canvas.create_text(x+10, y+header_h+12+(i*row_h), text=f"{prefix}{col_name}: {col_type}", fill="#c9d1d9", anchor="w", font=("Segoe UI", 9), tags=(table_id, "table"))

    def draw_connection(self, from_id, from_col, cols_f, to_id, to_col, cols_t):
        """Малює пунктирну лінію зв'язку між двома таблицями."""
        items_f = self.canvas.find_withtag(from_id); items_t = self.canvas.find_withtag(to_id)
        if items_f and items_t:
            c1 = self.canvas.coords(items_f[1]); c2 = self.canvas.coords(items_t[1])
            idx_f = next((i for i, col in enumerate(cols_f) if col[0] == from_col), 0)
            idx_t = next((i for i, col in enumerate(cols_t) if col[0] == to_col), 0)
            y1 = c1[1] + 30 + (idx_f * 25) + 12; y2 = c2[1] + 30 + (idx_t * 25) + 12
            x1 = c1[2] if c1[0] < c2[0] else c1[0]; x2 = c2[0] if c1[0] < c2[0] else c2[2]
            
            line = self.canvas.create_line(x1, y1, x2, y2, fill="#58a6ff", width=1.5, arrow=tk.LAST, dash=(4, 2), tags=("connection"))
            self.canvas.tag_lower(line)