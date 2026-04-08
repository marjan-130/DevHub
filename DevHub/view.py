import tkinter as tk
from tkinter import ttk, messagebox

class MainView(tk.Tk):
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
        frame = self.frames[frame_class]
        frame.tkraise()

    def start(self):
        self.mainloop()

# --- ВІКНО НАЛАШТУВАНЬ AI ГЕНЕРАЦІЇ ---
class AISmartFillDialog(tk.Toplevel):
    def __init__(self, parent, lang="UA"):
        super().__init__(parent)
        self.result = None
        self.grab_set()
        
        self.title("AI Smart Data Generator ✨")
        self.geometry("400x500")
        self.resizable(False, False)
        self.configure(bg="#161b22")

        container = tk.Frame(self, bg="#161b22", padx=20, pady=20)
        container.pack(fill="both", expand=True)

        tk.Label(container, text="Smart Data Export", font=("Segoe UI", 14, "bold"), bg="#161b22", fg="#4ade80").pack(pady=(0, 20))

        tk.Label(container, text="Мова даних / Data Language:", bg="#161b22", fg="white").pack(anchor="w")
        self.lang_var = tk.StringVar(value="Українська")
        self.combo_lang = ttk.Combobox(container, textvariable=self.lang_var, values=["Українська", "English", "Deutsch"])
        self.combo_lang.pack(fill="x", pady=(5, 15))

        tk.Label(container, text="Кількість рядків (на таблицю):", bg="#161b22", fg="white").pack(anchor="w")
        self.count_var = tk.IntVar(value=5)
        self.slider = tk.Scale(container, from_=1, to=50, orient="horizontal", variable=self.count_var, 
                               bg="#161b22", fg="white", highlightthickness=0, troughcolor="#30363d", activebackground="#4ade80")
        self.slider.pack(fill="x", pady=(5, 15))

        tk.Label(container, text="Додаткові побажання (фільтри/тема):", bg="#161b22", fg="white").pack(anchor="w")
        self.context_text = tk.Text(container, height=5, bg="#0d1117", fg="white", insertbackground="white", bd=1, relief="solid")
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
        self.result = {
            "lang": self.lang_var.get(),
            "count": self.count_var.get(),
            "context": self.context_text.get("1.0", "end-1c")
        }
        self.destroy()

class ColumnDialog(tk.Toplevel):
    def __init__(self, parent, lang="UA"):
        super().__init__(parent)
        self.result = None
        self.grab_set()

        txt = {
            "UA": {"t": "Параметри таблиці", "n": "Назва таблиці:", "tp": "Тип колонки:", "pk": "Встановити як Primary Key", "ok": "Створити"},
            "EN": {"t": "Table Parameters", "n": "Table Name:", "tp": "Main Column Type:", "pk": "Set as Primary Key", "ok": "Create"}
        }.get(lang, "UA")

        self.title(txt["t"])
        self.geometry("350x340") 
        self.resizable(False, False)

        container = tk.Frame(self, padx=20, pady=20)
        container.pack(fill="both", expand=True)

        self.lbl_table_name = tk.Label(container, text=txt["n"], font=("Arial", 10))
        self.lbl_table_name.pack(anchor="w")
        
        self.entry_name = ttk.Entry(container, width=40)
        self.entry_name.pack(pady=(5, 10))
        self.entry_name.focus()

        self.lbl_col_type = tk.Label(container, text=txt["tp"], font=("Arial", 10))
        self.lbl_col_type.pack(anchor="w")
        
        self.type_combo = ttk.Combobox(container, values=["INTEGER", "TEXT", "REAL", "BLOB", "DATETIME"], width=37)
        self.type_combo.set("INTEGER")
        self.type_combo.pack(pady=5)

        self.is_pk = tk.BooleanVar(value=True)
        self.chk_pk = tk.Checkbutton(container, text=txt["pk"], variable=self.is_pk)
        self.chk_pk.pack(anchor="w", pady=5)

        self.lbl_desc = tk.Label(container, text="Опис (для ШІ):", font=("Arial", 10))
        self.lbl_desc.pack(anchor="w", pady=(5, 0))
        
        self.entry_desc = ttk.Entry(container, width=40)
        self.entry_desc.pack(pady=5)

        btn_frame = tk.Frame(container)
        btn_frame.pack(pady=15)
        
        self.btn_ok = ttk.Button(btn_frame, text=txt["ok"], command=self.on_ok)
        self.btn_ok.pack(side="left", padx=10)
        
        self.btn_cancel = ttk.Button(btn_frame, text="Cancel" if lang=="EN" else "Скасувати", command=self.destroy)
        self.btn_cancel.pack(side="left", padx=10)

    def on_ok(self):
        name = self.entry_name.get().strip()
        desc = self.entry_desc.get().strip()
        if name:
            self.result = (name, self.type_combo.get(), self.is_pk.get(), desc)
            self.destroy()

class LoginFrame(tk.Frame):
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

        tk.Label(self.form_container, text="Forgot Password?", font=("Segoe UI", 9), 
                 bg="#161b22", fg="#8b949e", cursor="hand2").pack()

    def show_register_form(self):
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
    def __init__(self, parent, controller):
        super().__init__(parent, bg="#0d1117")
        self.controller = controller
        
        # --- ТЕМНА ТЕМА ДЛЯ TOOLBAR ---
        self.toolbar = tk.Frame(self, bg="#161b22", height=50, bd=1, relief="flat")
        self.toolbar.pack(side="top", fill="x")

        # Використовуємо кастомні темні кнопки
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
        export_style.update({"bg": "#238636", "fg": "white"}) # Зелена кнопка для експорту
        self.btn_export_sql = tk.Button(self.toolbar, text="⚡ Експорт SQL", **export_style)
        self.btn_export_sql.pack(side="right", padx=10, pady=8)

        self.main_content = tk.Frame(self, bg="#0d1117")
        self.main_content.pack(fill="both", expand=True)

        # --- ТЕМНА ТЕМА ДЛЯ SIDEBAR ---
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
        t = {
            "UA": {"new": "📄 Новий", "open": "📂 Відкрити", "save": "💾 Зберегти (JSON)", "cloud": "☁️ В хмару", "tab": "＋ Таблиця", "fk": "🔗 Foreign Key", "export": "⚡ Експорт SQL", "search": "ПОШУК ПРОЕКТІВ", "my_projs": "МОЇ ПРОЕКТИ", "arch_tab": "📐 Database Architect", "api_tab": "🌐 API Client", "del_proj": "Видалити проект", "url": "URL:", "send": "Send Request"},
            "EN": {"new": "📄 New", "open": "📂 Open", "save": "💾 Save (JSON)", "cloud": "☁️ Cloud Save", "tab": "＋ Table", "fk": "🔗 Relation", "export": "⚡ Export SQL", "search": "SEARCH PROJECTS", "my_projs": "MY PROJECTS", "arch_tab": "📐 Architect", "api_tab": "🌐 API Client", "del_proj": "Delete Project", "url": "URL:", "send": "Send Request"}
        }.get(lang, "UA")
        
        self.btn_new.config(text=t["new"]); self.btn_open.config(text=t["open"]); self.btn_save.config(text=t["save"])
        self.btn_db_save.config(text=t["cloud"]); self.btn_add_table.config(text=t["tab"]); self.btn_fk.config(text=t["fk"])
        self.btn_export_sql.config(text=t["export"]); self.lbl_search_title.config(text=t["search"])
        self.lbl_my_projects.config(text=t["my_projs"]); self.notebook.tab(0, text=t["arch_tab"])
        self.notebook.tab(1, text=t["api_tab"]); self.p_menu.entryconfigure(0, label=t["del_proj"])
        self.lbl_url.config(text=t["url"]); self.btn_send.config(text=t["send"])

    def set_fk_button_state(self, active=False):
        if active:
            self.btn_fk.configure(bg="#1f6feb", fg="white") # Синя підсвітка
        else:
            self.btn_fk.configure(bg="#21262d", fg="#c9d1d9")

    def _draw_grid(self):
        self.canvas.delete("grid")
        for i in range(0, 2000, 25):
            self.canvas.create_line(i, 0, i, 2000, fill="#161b22", tags="grid") # Темна сітка
            self.canvas.create_line(0, i, 2000, i, fill="#161b22", tags="grid")
        self.canvas.tag_lower("grid")

    def toggle_sidebar(self):
        if self.sidebar_visible: self.sidebar.pack_forget()
        else: self.sidebar.pack(side="left", fill="y", before=self.notebook)
        self.sidebar_visible = not self.sidebar_visible

    def _setup_api_ui(self):
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
        width, header_h, row_h = 160, 30, 25
        total_h = header_h + (len(columns) if columns else 1) * row_h + 5
        
        # Тінь/Бордер
        self.canvas.create_rectangle(x+2, y+2, x+width+2, y+total_h+2, fill="#000000", outline="", tags=(table_id, "table"))
        # Тіло таблиці
        self.canvas.create_rectangle(x, y, x+width, y+total_h, fill="#161b22", outline="#30363d", tags=(table_id, "table"))
        # Заголовок таблиці
        self.canvas.create_rectangle(x, y, x+width, y+header_h, fill="#21262d", outline="#30363d", tags=(table_id, "table"))
        # Текст заголовка
        self.canvas.create_text(x+width/2, y+header_h/2, text=name.upper(), fill="#58a6ff", font=("Segoe UI", 9, "bold"), tags=(table_id, "table"))
        
        if columns:
             for i, (col_name, col_type, desc) in enumerate(columns):
                 prefix = "🔑 " if "PRIMARY KEY" in col_type.upper() else "• "
                 self.canvas.create_text(x+10, y+header_h+12+(i*row_h), text=f"{prefix}{col_name}: {col_type}", fill="#c9d1d9", anchor="w", font=("Segoe UI", 9), tags=(table_id, "table"))

    def draw_connection(self, from_id, from_col, cols_f, to_id, to_col, cols_t):
        items_f = self.canvas.find_withtag(from_id); items_t = self.canvas.find_withtag(to_id)
        if items_f and items_t:
            c1 = self.canvas.coords(items_f[1]); c2 = self.canvas.coords(items_t[1])
            idx_f = next((i for i, col in enumerate(cols_f) if col[0] == from_col), 0)
            idx_t = next((i for i, col in enumerate(cols_t) if col[0] == to_col), 0)
            y1 = c1[1] + 30 + (idx_f * 25) + 12; y2 = c2[1] + 30 + (idx_t * 25) + 12
            x1 = c1[2] if c1[0] < c2[0] else c1[0]; x2 = c2[0] if c1[0] < c2[0] else c2[2]
            
            # Змінили колір лінії на гарний синій
            line = self.canvas.create_line(x1, y1, x2, y2, fill="#58a6ff", width=1.5, arrow=tk.LAST, dash=(4, 2), tags=("connection"))
            self.canvas.tag_lower(line)