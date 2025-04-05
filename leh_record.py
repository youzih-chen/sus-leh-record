import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import csv
import os
import platform
from datetime import datetime
import pickle
import tempfile
import atexit

class LEHRecordProgram:
    def __init__(self):
        self.setup_constants()
        self.setup_variables()
        self.setup_cache()
        self.create_main_window()
        self.setup_file_location()
        self.setup_context_fields()
        self.create_frames()
        self.create_sections()
        self.create_buttons()
        self.setup_bindings()
        self.setup_menu()
        atexit.register(self.cleanup_cache)

    def setup_constants(self):
        self.FONT_CONFIG = ("Calibri", 11)
        self.LABELS = [
            "Sample ID", "Context", "Sample Type", "Sample Side", 
            "Jaw Type", "Tooth Type", "Wear Level", "Age Group", "Sex", 
            "Greatest Length (GL)", "Anterior Width (WA)", "Middle Width (WM)", "Posterior Width (WP)", 
            "Anterior Lingual Crown Height (CAL)", "Middle Lingual Crown Height (CML)", 
            "Posterior Lingual Crown Height (CPL)", 
            "Anterior Buccal Crown Height (CAB)", "Middle Buccal Crown Height (CMB)", 
            "Posterior Buccal Crown Height (CPB)", 
            "Lingual Peak a LEH Height (La)", "Lingual Peak b LEH Height (Lb)", 
            "Lingual Peak c LEH Height (Lc)", 
            "Buccal Peak a LEH Height (Ba)", "Buccal Peak b LEH Height (Bb)", 
            "Buccal Peak c LEH Height (Bc)", 
            "LEH Count", "LEH Type", "Notes", "Pathology"
        ]
        self.basic_fields = self.LABELS[:9]
        self.measurement_fields = self.LABELS[9:19]
        self.initial_leh_fields = self.LABELS[19:25]
        self.leh_count_type = self.LABELS[25:27]
        self.other_fields = self.LABELS[27:]
        self.fixed_photo_types = ["Buccal", "Lingual", "Occlusal"]

    def setup_variables(self):
        self.entries = {}
        self.averages = {}
        self.records = []
        self.all_data = []
        self.current_file = None
        self.data_dir = None
        self.additional_leh_fields = []
        self.additional_photo_fields = []
        self.all_photo_fields = self.fixed_photo_types.copy()
        self.row_map = {}
        self.photo_row_map = {}
        self.current_record_index = -1
        self.all_leh_fields = self.initial_leh_fields.copy()
        self.leh_field_order = self.initial_leh_fields.copy()  # 維護欄位順序
        self.context_fields = []
        self.record_number = 1

    def setup_cache(self):
        self.cache_file = os.path.join(tempfile.gettempdir(), 'leh_record_cache.pkl')
        self.record_cache = {}
        if os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, 'rb') as f:
                    self.record_cache = pickle.load(f)
            except:
                self.record_cache = {}

    def save_to_cache(self, record_num, entries):
        cache_data = {}
        for key, widget in entries.items():
            if widget.winfo_exists():
                if isinstance(widget, tk.Text):
                    cache_data[key] = widget.get("1.0", tk.END).strip()
                else:
                    cache_data[key] = widget.get()
        self.record_cache[record_num] = cache_data
        try:
            with open(self.cache_file, 'wb') as f:
                pickle.dump(self.record_cache, f)
            print(f"Cached record {record_num}")
        except Exception as e:
            print(f"快取保存失敗: {e}")

    def cleanup_cache(self):
        try:
            if os.path.exists(self.cache_file):
                os.remove(self.cache_file)
        except:
            pass

    def create_main_window(self):
        self.root = tk.Tk()
        self.root.title("LEH Record Program")
        self.root.geometry("1400x800")
        self.root.resizable(True, True)

    def setup_file_location(self):
        file_window = tk.Toplevel(self.root)
        file_window.title("Setup File Location")
        file_window.geometry("400x200")
        file_window.transient(self.root)
        file_window.grab_set()

        tk.Label(file_window, text="Choose an option:").pack(pady=10)

        def new_folder():
            self.data_dir = filedialog.askdirectory(title="Select Directory to Save Data")
            if self.data_dir:
                self.current_file = os.path.join(self.data_dir, f"LEHrec_{datetime.now().strftime('%Y%m%d')}.csv")
                file_window.destroy()

        def open_file():
            file_path = filedialog.askopenfilename(filetypes=[("CSV files", "*.csv"), ("All files", "*.*")])
            if file_path:
                self.current_file = file_path
                self.data_dir = os.path.dirname(file_path)
                context_file = os.path.join(self.data_dir, "context_config.pkl")
                if os.path.exists(context_file):
                    with open(context_file, 'rb') as f:
                        self.context_fields = pickle.load(f)
                        self.basic_fields = self.LABELS[:1] + self.context_fields + self.LABELS[2:9]
                self.load_existing_file()
                file_window.destroy()

        tk.Button(file_window, text="Create New Folder", command=new_folder).pack(pady=5)
        tk.Button(file_window, text="Open Existing File", command=open_file).pack(pady=5)
        file_window.wait_window()

    def setup_context_fields(self):
        if not self.context_fields:
            context_window = tk.Toplevel(self.root)
            context_window.title("Set Context Fields")
            context_window.geometry("400x300")
            context_window.transient(self.root)
            context_window.grab_set()

            tk.Label(context_window, text="Enter Context subfields (one per line):").pack(pady=5)
            text_area = tk.Text(context_window, height=10, width=40)
            text_area.pack(pady=5)

            def save_context_fields():
                fields = text_area.get("1.0", tk.END).strip().split("\n")
                self.context_fields = [f.strip() for f in fields if f.strip()]
                self.basic_fields = self.LABELS[:1] + self.context_fields + self.LABELS[2:9]
                if self.data_dir:
                    with open(os.path.join(self.data_dir, "context_config.pkl"), 'wb') as f:
                        pickle.dump(self.context_fields, f)
                context_window.destroy()

            tk.Button(context_window, text="Save", command=save_context_fields).pack(pady=5)
            context_window.wait_window()

    def create_frames(self):
        self.outer_frame = tk.Frame(self.root)
        self.outer_frame.pack(fill="both", expand=True)
        self.create_record_frame()
        self.create_main_frame()
        self.button_frame = tk.Frame(self.root)
        self.button_frame.pack(side="bottom", pady=10)
        self.status_label = tk.Label(self.root, text="", font=self.FONT_CONFIG)
        self.status_label.pack(side="bottom", pady=5)

    def create_record_frame(self):
        self.record_frame = ttk.LabelFrame(self.outer_frame, text="Previous Records", padding=10)
        self.record_frame.pack(side="left", fill="y", padx=10, pady=10)
        self.record_canvas = tk.Canvas(self.record_frame, width=300)
        self.record_canvas.pack(side="left", fill="both", expand=True)
        record_scrollbar = ttk.Scrollbar(self.record_frame, orient="vertical", command=self.record_canvas.yview)
        record_scrollbar.pack(side="right", fill="y")
        self.record_canvas.configure(yscrollcommand=record_scrollbar.set)
        self.record_inner_frame = tk.Frame(self.record_canvas)
        self.record_canvas.create_window((0, 0), window=self.record_inner_frame, anchor="nw")
        self.tree = ttk.Treeview(self.record_inner_frame, columns=("Record", "Sample ID", "Tooth Type"), show="headings", height=20)
        self.tree.heading("Record", text="Record Number")
        self.tree.heading("Sample ID", text="Sample ID")
        self.tree.heading("Tooth Type", text="Tooth Type")
        self.tree.column("Record", width=100, anchor="w")
        self.tree.column("Sample ID", width=100, anchor="w")
        self.tree.column("Tooth Type", width=100, anchor="w")
        self.tree.pack(fill="y", expand=True)
        self.tree.bind("<Double-1>", self.show_record)

    def create_main_frame(self):
        self.main_frame = tk.Frame(self.outer_frame)
        self.main_frame.pack(side="left", fill="both", expand=True)
        self.canvas = tk.Canvas(self.main_frame)
        self.canvas.pack(side="left", fill="both", expand=True)
        v_scrollbar = ttk.Scrollbar(self.main_frame, orient="vertical", command=self.canvas.yview)
        v_scrollbar.pack(side="right", fill="y")
        self.canvas.configure(yscrollcommand=v_scrollbar.set)
        self.inner_frame = tk.Frame(self.canvas)
        self.canvas.create_window((0, 0), window=self.inner_frame, anchor="nw")

    def create_sections(self):
        self.top_frame = tk.Frame(self.inner_frame)
        self.top_frame.grid(row=0, column=0, sticky="ew")
        self.create_basic_section()
        self.create_measurement_section()
        self.create_leh_section()
        self.other_photo_frame = tk.Frame(self.inner_frame)
        self.other_photo_frame.grid(row=2, column=0, sticky="ew")
        self.create_other_section()
        self.create_photo_section()

    def create_basic_section(self):
        basic_frame = ttk.LabelFrame(self.top_frame, text="Basic Information", padding=10)
        basic_frame.pack(side="left", fill="y", padx=10, pady=10)
        for i, field in enumerate(self.basic_fields):
            tk.Label(basic_frame, text=field, font=self.FONT_CONFIG).grid(row=i, column=0, padx=5, pady=2, sticky="e")
            entry = tk.Entry(basic_frame, width=30, font=self.FONT_CONFIG)
            entry.grid(row=i, column=1, padx=5, pady=2)
            self.entries[field] = entry

    def create_measurement_section(self):
        measurement_frame = ttk.LabelFrame(self.top_frame, text="Measurements", padding=10)
        measurement_frame.pack(side="left", fill="y", padx=10, pady=10)
        for i, field in enumerate(self.measurement_fields):
            short_label = self.get_short_label(field)
            tk.Label(measurement_frame, text=short_label, font=self.FONT_CONFIG).grid(row=i, column=0, padx=5, pady=2, sticky="e")
            for j in range(3):
                entry = tk.Entry(measurement_frame, width=8, font=self.FONT_CONFIG)
                entry.grid(row=i, column=j+1, padx=2, pady=2)
                self.entries[f"{field}{j+1}"] = entry
                self.setup_measurement_bindings(entry, field)
            avg_label = tk.Label(measurement_frame, text="N/A", font=self.FONT_CONFIG)
            avg_label.grid(row=i, column=4, padx=5, pady=2)
            self.averages[field] = avg_label

    def create_leh_section(self):
        self.leh_frame = ttk.LabelFrame(self.inner_frame, text="LEH Records", padding=10)
        self.leh_frame.grid(row=1, column=0, sticky="ew", padx=10, pady=10)
        headers = ["LEH Count", "LEH Type", "CEJ Visible", "Photo ID"]
        for i, header in enumerate(headers):
            tk.Label(self.leh_frame, text=header, font=self.FONT_CONFIG).grid(row=0, column=i+5, padx=5, pady=2, sticky="w")
        self.render_leh_fields()

    def render_leh_fields(self):
        # 保存現有值
        saved_values = {}
        for field in self.leh_field_order:
            for suffix in ["1", "2", "3", " LEH Count", " LEH Type", " CEJ Visible", " Photo ID"]:
                key = f"{field}{suffix}"
                if key in self.entries and self.entries[key].winfo_exists():
                    saved_values[key] = self.entries[key].get()
            if field in self.averages and self.averages[field].winfo_exists():
                saved_values[f"{field}_avg"] = self.averages[field].cget("text")

        # 清空現有欄位（保留標題行）
        for widget in self.leh_frame.grid_slaves():
            if int(widget.grid_info()["row"]) > 0:
                widget.grid_forget()

        # 重新渲染欄位並恢復值
        self.entries = {k: v for k, v in self.entries.items() if not any(k.startswith(f) for f in self.leh_field_order)}
        self.averages = {k: v for k, v in self.averages.items() if not any(k.startswith(f) for f in self.leh_field_order)}
        self.row_map.clear()

        for i, field in enumerate(self.leh_field_order, 1):
            self.add_leh_field(field, i)
            # 恢復值
            for suffix in ["1", "2", "3", " LEH Count", " LEH Type", " CEJ Visible", " Photo ID"]:
                key = f"{field}{suffix}"
                if key in saved_values and key in self.entries:
                    self.entries[key].insert(0, saved_values[key])
            if f"{field}_avg" in saved_values and field in self.averages:
                self.averages[field].config(text=saved_values[f"{field}_avg"])

    def add_leh_field(self, unique_label, row):
        short_label = self.get_short_label(unique_label)
        tk.Label(self.leh_frame, text=short_label, font=self.FONT_CONFIG).grid(row=row, column=0, padx=5, pady=2, sticky="e")
        entries = []
        for i in range(3):
            entry = tk.Entry(self.leh_frame, width=8, font=self.FONT_CONFIG)
            entry.grid(row=row, column=i+1, padx=2, pady=2)
            self.entries[f"{unique_label}{i+1}"] = entry
            entries.append(entry)
            self.setup_measurement_bindings(entry, unique_label)
        avg_label = tk.Label(self.leh_frame, text="N/A", font=self.FONT_CONFIG)
        avg_label.grid(row=row, column=4, padx=5, pady=2)
        self.averages[unique_label] = avg_label
        count_entry = tk.Entry(self.leh_frame, width=10, font=self.FONT_CONFIG)
        type_entry = tk.Entry(self.leh_frame, width=10, font=self.FONT_CONFIG)
        cej_entry = tk.Entry(self.leh_frame, width=10, font=self.FONT_CONFIG)
        photo_entry = tk.Entry(self.leh_frame, width=15, font=self.FONT_CONFIG)
        count_entry.grid(row=row, column=5, padx=2, pady=2)
        type_entry.grid(row=row, column=6, padx=2, pady=2)
        cej_entry.grid(row=row, column=7, padx=2, pady=2)
        photo_entry.grid(row=row, column=8, padx=2, pady=2)
        self.entries[f"{unique_label} LEH Count"] = count_entry
        self.entries[f"{unique_label} LEH Type"] = type_entry
        self.entries[f"{unique_label} CEJ Visible"] = cej_entry
        self.entries[f"{unique_label} Photo ID"] = photo_entry
        base_label = unique_label.split("_")[0] if "_" in unique_label else unique_label
        add_button = ttk.Button(self.leh_frame, text="+", width=2, command=lambda l=base_label: self.add_new_leh_field(l))
        add_button.grid(row=row, column=9, padx=2, pady=2)
        all_widgets = entries + [count_entry, type_entry, cej_entry, photo_entry, add_button]
        self.setup_navigation(all_widgets)
        self.row_map[unique_label] = row

    def add_new_leh_field(self, label):
        suffix = str(len([f for f in self.additional_leh_fields if f.startswith(label)]) + 1)
        unique_label = f"{label}_{suffix}"
        self.additional_leh_fields.append(unique_label)
        self.all_leh_fields = self.initial_leh_fields + self.additional_leh_fields
        
        # 在 leh_field_order 中插入新欄位到原始欄位後
        insert_index = self.leh_field_order.index(label) + 1
        self.leh_field_order.insert(insert_index, unique_label)
        
        print(f"Adding {unique_label}, current row_map: {self.row_map}")
        
        # 重新渲染所有欄位並保留值
        self.render_leh_fields()
        self.canvas.update_idletasks()
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        self.entries[f"{unique_label}1"].focus_set()
        print(f"After adding {unique_label}, updated row_map: {self.row_map}")

    def create_other_section(self):
        self.other_frame = ttk.LabelFrame(self.other_photo_frame, text="Other Information", padding=10)
        self.other_frame.pack(side="left", fill="y", padx=10, pady=10)
        for i, field in enumerate(self.other_fields):
            tk.Label(self.other_frame, text=field, font=self.FONT_CONFIG).grid(row=i, column=0, padx=5, pady=2, sticky="ne")
            text_frame = tk.Frame(self.other_frame)
            text_frame.grid(row=i, column=1, padx=5, pady=2, sticky="w")
            text_widget = tk.Text(text_frame, width=40, height=5, font=self.FONT_CONFIG)
            text_widget.pack(side="left", fill="y")
            scrollbar = tk.Scrollbar(text_frame, orient="vertical", command=text_widget.yview)
            scrollbar.pack(side="right", fill="y")
            text_widget.configure(yscrollcommand=scrollbar.set)
            def handle_tab(event, next_field_idx=i+1):
                if next_field_idx < len(self.other_fields):
                    next_field = self.other_fields[next_field_idx]
                    self.entries[next_field].focus_set()
                elif next_field_idx == len(self.other_fields):
                    self.entries[f"Image ID ({self.fixed_photo_types[0]})"].focus_set()
                return "break"
            text_widget.bind("<Tab>", handle_tab)
            self.entries[field] = text_widget

    def create_photo_section(self):
        self.photo_frame = ttk.LabelFrame(self.other_photo_frame, text="Photo", padding=10)
        self.photo_frame.pack(side="left", fill="y", padx=10, pady=10)
        tk.Label(self.photo_frame, text="Type", font=self.FONT_CONFIG).grid(row=0, column=0, padx=5, pady=2, sticky="e")
        tk.Label(self.photo_frame, text="Image ID", font=self.FONT_CONFIG).grid(row=0, column=1, padx=5, pady=2, sticky="e")
        for i, type_name in enumerate(self.fixed_photo_types, 1):
            tk.Label(self.photo_frame, text=type_name, font=self.FONT_CONFIG).grid(row=i, column=0, padx=5, pady=2, sticky="e")
            entry = tk.Entry(self.photo_frame, width=10, font=self.FONT_CONFIG)
            entry.grid(row=i, column=1, padx=5, pady=2)
            self.entries[f"Image ID ({type_name})"] = entry
            self.photo_row_map[f"Image ID ({type_name})"] = i
            self.setup_navigation([entry])
        self.add_photo_id_field(4)

    def add_photo_id_field(self, row, suffix=""):
        unique_label = f"Image ID (add{suffix})" if suffix else f"Image ID (add1)"
        type_entry = tk.Entry(self.photo_frame, width=10, font=self.FONT_CONFIG)
        type_entry.grid(row=row, column=0, padx=5, pady=2)
        image_entry = tk.Entry(self.photo_frame, width=10, font=self.FONT_CONFIG)
        image_entry.grid(row=row, column=1, padx=5, pady=2)
        self.entries[f"{unique_label}_type"] = type_entry
        self.entries[unique_label] = image_entry
        add_button = ttk.Button(self.photo_frame, text="+", width=2, command=lambda r=row: self.add_new_photo_id_field(r))
        add_button.grid(row=row, column=2, padx=2, pady=2)
        self.photo_row_map[unique_label] = row
        self.setup_navigation([type_entry, image_entry, add_button])

    def add_new_photo_id_field(self, row):
        suffix = len(self.additional_photo_fields) + 1
        unique_label = f"Image ID (add{suffix})"
        self.additional_photo_fields.append(unique_label)
        self.all_photo_fields = self.fixed_photo_types + self.additional_photo_fields
        insert_row = row + 1
        for field in sorted(self.photo_row_map.keys(), key=lambda x: self.photo_row_map[x], reverse=True):
            if self.photo_row_map[field] >= insert_row:
                for widget in self.photo_frame.grid_slaves(row=self.photo_row_map[field]):
                    widget.grid(row=self.photo_row_map[field] + 1)
                self.photo_row_map[field] += 1
        self.add_photo_id_field(insert_row, suffix)
        self.canvas.update_idletasks()
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        self.entries[f"Image ID (add{suffix})_type"].focus_set()

    def setup_navigation(self, widgets):
        for widget in widgets:
            widget.configure(takefocus=1)
            if isinstance(widget, tk.Entry):
                for direction in ["Up", "Down", "Left", "Right"]:
                    widget.bind(f"<{direction}>", lambda e, w=widget: self.handle_arrow_key(e, w))

    def setup_measurement_bindings(self, entry, field):
        entry.bind("<KeyRelease>", lambda e, f=field: self.calculate_avg(f))
        entry.bind("<KeyPress>", lambda e, f=field: self.calculate_avg(f))
        entry.bind("<Key>", lambda e, ent=entry, f=field: self.handle_decimal_input(e, ent, f))

    def create_buttons(self):
        save_button = ttk.Button(self.button_frame, text="Save", command=self.save_and_clear)
        save_button.pack(side="left", padx=5)
        prev_button = ttk.Button(self.button_frame, text="Previous Record", command=self.show_previous_record)
        prev_button.pack(side="left", padx=5)
        next_same_button = ttk.Button(self.button_frame, text="NEXT(same)", command=self.next_record)
        next_same_button.pack(side="left", padx=5)
        next_another_button = ttk.Button(self.button_frame, text="NEXT(another)", command=self.next_another_record)
        next_another_button.pack(side="left", padx=5)
        new_button = ttk.Button(self.button_frame, text="New Record", command=self.new_record)
        new_button.pack(side="left", padx=5)
        export_button = ttk.Button(self.button_frame, text="Export CSV", command=self.export_csv)
        export_button.pack(side="left", padx=5)
        view_cache_button = ttk.Button(self.button_frame, text="View Cache", command=self.view_cache)
        view_cache_button.pack(side="left", padx=5)

    def setup_menu(self):
        menu_bar = tk.Menu(self.root)
        self.root.config(menu=menu_bar)
        file_menu = tk.Menu(menu_bar, tearoff=0)
        menu_bar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Open File", command=self.open_file)
        file_menu.add_command(label="Save As", command=self.save_as)

    def setup_bindings(self):
        self.canvas.bind_all("<MouseWheel>", self.on_mouse_wheel)
        self.canvas.bind_all("<Button-4>", self.on_mouse_wheel)
        self.canvas.bind_all("<Button-5>", self.on_mouse_wheel)
        self.record_inner_frame.bind("<Configure>", lambda e: self.record_canvas.configure(scrollregion=self.record_canvas.bbox("all")))
        self.inner_frame.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))

    def calculate_avg(self, unique_label):
        values = []
        for i in ["1", "2", "3"]:
            val = self.entries[f"{unique_label}{i}"].get().strip().replace("。", ".")
            if val:
                try:
                    values.append(float(val))
                except ValueError:
                    self.averages[unique_label].config(text="N/A")
                    return
        if values:
            avg = sum(values) / len(values)
            self.averages[unique_label].config(text=f"{avg:.2f}")
        else:
            self.averages[unique_label].config(text="N/A")

    def handle_decimal_input(self, event, entry, unique_label):
        if event.char in [".", "。"] or event.keysym == "KP_Decimal":
            current_pos = entry.index(tk.INSERT)
            entry.insert(current_pos, ".")
            self.calculate_avg(unique_label)
            return "break"
        return None

    def handle_arrow_key(self, event, current_widget):
        if not isinstance(current_widget, tk.Entry):
            return
        current_key = [key for key, widget in self.entries.items() if widget == current_widget][0]
        if event.keysym == "Up":
            prev_row = self.row_map.get(current_key, self.photo_row_map.get(current_key, 1)) - 1
            if prev_row >= 1:
                for key, row in {**self.row_map, **self.photo_row_map}.items():
                    if row == prev_row:
                        self.entries[key].focus_set()
                        break
        elif event.keysym == "Down":
            next_row = self.row_map.get(current_key, self.photo_row_map.get(current_key, 1)) + 1
            if next_row <= max({**self.row_map, **self.photo_row_map}.values()):
                for key, row in {**self.row_map, **self.photo_row_map}.items():
                    if row == next_row:
                        self.entries[key].focus_set()
                        break
        elif event.keysym == "Left":
            if current_key.endswith("_type"):
                self.entries[current_key[:-5]].focus_set()
        elif event.keysym == "Right":
            if not current_key.endswith("_type") and f"{current_key}_type" in self.entries:
                self.entries[f"{current_key}_type"].focus_set()

    def on_mouse_wheel(self, event):
        if platform.system() == "Windows":
            self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        elif platform.system() == "Darwin":
            self.canvas.yview_scroll(int(-1 * event.delta), "units")
        else:
            if event.num == 4:
                self.canvas.yview_scroll(-1, "units")
            elif event.num == 5:
                self.canvas.yview_scroll(1, "units")

    @staticmethod
    def get_short_label(label):
        if "(" in label and ")" in label:
            return label[label.index("(")+1:label.index(")")]
        return label

    def save_and_clear(self):
        self.root.focus_set()
        if not self.current_file:
            self.status_label.config(text="No file selected!")
            return
        data = self.collect_data()
        if not data:
            return
        if self.current_record_index >= 0:
            self.save_data(data, is_update=True)
        else:
            self.save_data(data, is_update=False, new_record=True)
        self.save_to_cache(str(self.record_number), self.entries)
        self.all_data = self.records.copy()
        self.update_treeview()
        self.clear_entries()
        self.current_record_index = -1
        self.status_label.config(text="Data saved internally and cached")

    def export_csv(self):
        if not self.current_file:
            self.status_label.config(text="No file selected!")
            return
        if self.save_to_file():
            self.status_label.config(text=f"Exported to {os.path.basename(self.current_file)}")
        else:
            self.status_label.config(text="Failed to export file! Check logs for details.")

    def update_treeview(self):
        self.tree.delete(*self.tree.get_children())
        records_by_num = {}
        for row in self.records:
            record_num = row["Record Number"]
            if record_num not in records_by_num:
                records_by_num[record_num] = row
        for record_num, row in records_by_num.items():
            sample_id = row["Sample ID"]
            tooth_type = row["Tooth Type"]
            self.tree.insert("", "end", values=(record_num, sample_id, tooth_type))

    def collect_data(self):
        base_data = {label: self.entries[label].get() for label in self.basic_fields}
        sample_id = base_data["Sample ID"]
        tooth_type = base_data["Tooth Type"]
        if not sample_id or not tooth_type:
            self.status_label.config(text="Sample ID and Tooth Type are required!")
            return None
        measurement_data = {}
        for field in self.measurement_fields:
            short_field = self.get_short_label(field)
            for i in ["1", "2", "3"]:
                key = f"{field}{i}"
                measurement_data[f"{short_field}{i}"] = self.entries[key].get()
        other_data = {field: self.entries[field].get("1.0", tk.END).strip() for field in self.other_fields}
        photo_data = {}
        for label in self.fixed_photo_types:
            photo_data[f"Image ID ({label})"] = self.entries[f"Image ID ({label})"].get()
        for label in self.additional_photo_fields:
            type_val = self.entries[f"{label}_type"].get().strip()
            image_val = self.entries[label].get().strip()
            photo_data[f"{label}_type"] = type_val
            photo_data[label] = image_val
        leh_rows = []
        all_leh_fields = self.initial_leh_fields + self.additional_leh_fields
        common_data = {**base_data, **measurement_data, **other_data, **photo_data}
        for field in all_leh_fields:
            val1 = self.entries[f"{field}1"].get()
            val2 = self.entries[f"{field}2"].get()
            val3 = self.entries[f"{field}3"].get()
            if val1 or val2 or val3:
                row_data = common_data.copy()
                row_data.update({
                    "LEH Side": self.get_short_label(field),
                    "Value 1": val1,
                    "Value 2": val2,
                    "Value 3": val3,
                    "LEH Count": self.entries[f"{field} LEH Count"].get(),
                    "LEH Type": self.entries[f"{field} LEH Type"].get(),
                    "CEJ Visible": self.entries[f"{field} CEJ Visible"].get(),
                    "Photo ID": self.entries[f"{field} Photo ID"].get()
                })
                values = [float(v) for v in [val1, val2, val3] if v]
                row_data["Avg"] = f"{sum(values) / len(values):.2f}" if values else ""
                leh_rows.append(row_data)
        return {"base_data": base_data, "leh_rows": leh_rows}

    def save_data(self, data, is_update=False, new_record=False):
        base_data = data["base_data"]
        leh_rows = data["leh_rows"]
        if new_record:
            self.record_number += 1
        record_num = self.records[self.current_record_index]["Record Number"] if is_update else str(self.record_number)
        if is_update:
            self.records = [r for r in self.records if r["Record Number"] != record_num]
        
        record_data = []
        common_data = base_data.copy()
        measurement_data = {f"{self.get_short_label(field)}{i}": self.entries[f"{field}{i}"].get() 
                            for field in self.measurement_fields for i in ["1", "2", "3"]}
        common_data.update(measurement_data)
        other_data = {field: self.entries[field].get("1.0", tk.END).strip() for field in self.other_fields}
        photo_data = {f"Image ID ({label})": self.entries[f"Image ID ({label})"].get() for label in self.fixed_photo_types}
        photo_data.update({field: self.entries[field].get() for field in self.additional_photo_fields})
        photo_data.update({f"{field}_type": self.entries[f"{field}_type"].get() for field in self.additional_photo_fields})
        common_data.update(other_data)
        common_data.update(photo_data)
        if not leh_rows:
            row_data = {"Record Number": record_num, "LEH Side": "", "Value 1": "", "Value 2": "", "Value 3": "",
                        "Avg": "", "LEH Count": "", "LEH Type": "", "CEJ Visible": "", "Photo ID": ""}
            row_data.update(common_data)
            record_data.append(row_data)
        else:
            for row in leh_rows:
                row_data = row.copy()
                row_data["Record Number"] = record_num
                row_data.update(common_data)
                record_data.append(row_data)
        
        self.records.extend(record_data)
        print(f"Saved record: {record_num}, Total records: {len(self.records)}")

    def save_to_file(self):
        try:
            if not self.current_file or not os.path.isdir(os.path.dirname(self.current_file)):
                raise ValueError("Invalid file path or directory")
            fieldnames = ["Record Number"] + self.basic_fields + \
                         [self.get_short_label(field) + i for field in self.measurement_fields for i in ["1", "2", "3"]] + \
                         ["LEH Side", "Value 1", "Value 2", "Value 3", "Avg", "LEH Count", "LEH Type", "CEJ Visible", "Photo ID"] + \
                         self.other_fields + \
                         [f"Image ID ({label})" for label in self.fixed_photo_types] + \
                         [field for field in self.additional_photo_fields] + \
                         [f"{field}_type" for field in self.additional_photo_fields]
            with open(self.current_file, "w", newline="", encoding="utf-8") as file:
                writer = csv.DictWriter(file, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(self.all_data)
            return True
        except Exception as e:
            self.status_label.config(text=f"Error exporting file: {str(e)}")
            return False

    def clear_entries(self, preserve_fields=None):
        if preserve_fields is None:
            preserve_fields = []
        for key, entry in list(self.entries.items()):
            if key not in preserve_fields and entry.winfo_exists():
                if isinstance(entry, tk.Text):
                    entry.delete("1.0", tk.END)
                elif isinstance(entry, tk.Entry):
                    entry.delete(0, tk.END)
        for avg_label in self.averages.values():
            if avg_label.winfo_exists():
                avg_label.config(text="N/A")

    def reset_leh_fields(self):
        for field in self.additional_leh_fields[:]:
            if field in self.row_map:
                del self.row_map[field]
            if field in self.entries:
                del self.entries[field]
            if field in self.averages:
                del self.averages[field]
        self.additional_leh_fields = []
        self.all_leh_fields = self.initial_leh_fields.copy()
        self.leh_field_order = self.initial_leh_fields.copy()
        self.render_leh_fields()

    def reset_photo_fields(self):
        for field in self.additional_photo_fields[:]:
            row = self.photo_row_map.get(field)
            if row:
                for widget in self.photo_frame.grid_slaves(row=row):
                    widget.destroy()
            if field in self.photo_row_map:
                del self.photo_row_map[field]
            if field in self.entries:
                del self.entries[field]
            if f"{field}_type" in self.entries:
                del self.entries[f"{field}_type"]
        self.additional_photo_fields = []
        self.all_photo_fields = self.fixed_photo_types.copy()
        for i, type_name in enumerate(self.fixed_photo_types, 1):
            self.photo_row_map[f"Image ID ({type_name})"] = i
        self.canvas.update_idletasks()
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def open_file(self):
        file_path = filedialog.askopenfilename(filetypes=[("CSV files", "*.csv"), ("All files", "*.*")])
        if not file_path:
            return
        self.current_file = file_path
        self.data_dir = os.path.dirname(file_path)
        self.load_existing_file()
        context_file = os.path.join(self.data_dir, "context_config.pkl")
        if os.path.exists(context_file):
            with open(context_file, 'rb') as f:
                self.context_fields = pickle.load(f)
                self.basic_fields = self.LABELS[:1] + self.context_fields + self.LABELS[2:9]

    def load_existing_file(self):
        try:
            with open(self.current_file, "r", encoding="utf-8") as file:
                reader = csv.DictReader(file)
                self.all_data = list(reader)
                self.records = self.all_data.copy()
                self.record_number = max([int(row["Record Number"]) for row in self.records if row["Record Number"].isdigit()], default=0) + 1
            self.update_treeview()
            self.status_label.config(text=f"Loaded file: {os.path.basename(self.current_file)}")
        except Exception as e:
            self.status_label.config(text=f"Error loading file: {str(e)}")

    def save_as(self):
        file_path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV files", "*.csv"), ("All files", "*.*")])
        if file_path:
            self.current_file = file_path
            self.data_dir = os.path.dirname(file_path)
            self.all_data = self.records.copy()
            self.save_to_file()
            with open(os.path.join(self.data_dir, "context_config.pkl"), 'wb') as f:
                pickle.dump(self.context_fields, f)
            self.status_label.config(text=f"Saved as {os.path.basename(self.current_file)}")

    def show_record(self, event=None):
        selection = self.tree.selection()
        if not selection:
            return
        item = selection[0]
        self.current_record_index = self.tree.index(item)
        selected_record_num = self.tree.item(item)["values"][0]
        record_data = [row for row in self.records if row["Record Number"] == str(selected_record_num)]
        print(f"Showing record {selected_record_num}, data: {record_data}")
        if not record_data:
            return
        
        self.reset_leh_fields()
        self.reset_photo_fields()
        self.clear_entries()
        
        first_row = record_data[0]
        for field in self.basic_fields + self.other_fields:
            if field in first_row and first_row[field]:
                if isinstance(self.entries[field], tk.Text):
                    self.entries[field].insert("1.0", first_row[field])
                else:
                    self.entries[field].insert(0, first_row[field])
        
        for field in self.measurement_fields:
            short_field = self.get_short_label(field)
            for i in ["1", "2", "3"]:
                key = f"{short_field}{i}"
                if key in first_row and first_row[key]:
                    self.entries[f"{field}{i}"].insert(0, first_row[key])
            self.calculate_avg(field)
        
        for label in self.fixed_photo_types:
            key = f"Image ID ({label})"
            if key in first_row and first_row[key]:
                self.entries[key].insert(0, first_row[key])
        
        dynamic_photos_added = set()
        for field in first_row:
            if field.startswith("Image ID (add") and field.endswith("_type"):
                base_field = field[:-5]
                if base_field not in self.all_photo_fields and base_field not in dynamic_photos_added:
                    self.add_new_photo_id_field(self.photo_row_map[self.all_photo_fields[-1]])
                    dynamic_photos_added.add(base_field)
                if first_row[field]:
                    self.entries[field].insert(0, first_row[field])
                if base_field in first_row and first_row[base_field]:
                    self.entries[base_field].insert(0, first_row[base_field])
        
        dynamic_leh_added = set()
        for row in record_data:
            leh_side = row.get("LEH Side", "")
            if not leh_side:
                continue
            full_label = None
            if "_" in leh_side:
                base_label, suffix = leh_side.rsplit("_", 1)
                full_label = next((f for f in self.initial_leh_fields if self.get_short_label(f) == base_label), None)
                if full_label and f"{full_label}_{suffix}" not in self.all_leh_fields and f"{full_label}_{suffix}" not in dynamic_leh_added:
                    self.add_new_leh_field(full_label)
                    dynamic_leh_added.add(f"{full_label}_{suffix}")
                    full_label = f"{full_label}_{suffix}"
            else:
                full_label = next((f for f in self.initial_leh_fields if self.get_short_label(f) == leh_side), None)
            
            if full_label:
                for i in ["1", "2", "3"]:
                    key = f"Value {i}"
                    if key in row and row[key]:
                        self.entries[f"{full_label}{i}"].insert(0, row[key])
                for field_type in ["LEH Count", "LEH Type", "CEJ Visible", "Photo ID"]:
                    key = f"{full_label} {field_type}"
                    if field_type in row and row[field_type]:
                        self.entries[key].insert(0, row[field_type])
                self.calculate_avg(full_label)
        
        self.canvas.update_idletasks()
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        self.status_label.config(text=f"Showing record {selected_record_num}")

    def show_previous_record(self):
        if self.current_record_index > 0:
            self.current_record_index -= 1
            self.tree.selection_set(self.tree.get_children()[self.current_record_index])
            self.show_record()

    def next_record(self):
        data = self.collect_data()
        if data:
            self.save_data(data, self.current_record_index >= 0)
            self.save_to_cache(str(self.record_number), self.entries)
            self.update_treeview()
        saved_basic_data = {field: self.entries[field].get() for field in self.basic_fields}
        saved_photo_data = {field: self.entries[field].get() for field in [f"Image ID ({t})" for t in self.fixed_photo_types] + self.additional_photo_fields}
        saved_photo_types = {f"{field}_type": self.entries[f"{field}_type"].get() for field in self.additional_photo_fields}
        self.clear_entries()
        for field, value in saved_basic_data.items():
            if value and field in self.entries and self.entries[field].winfo_exists():
                self.entries[field].insert(0, value)
        for field, value in saved_photo_data.items():
            if value and field in self.entries and self.entries[field].winfo_exists():
                self.entries[field].insert(0, value)
        for field, value in saved_photo_types.items():
            if value and field in self.entries and self.entries[field].winfo_exists():
                self.entries[field].insert(0, value)
        self.reset_leh_fields()
        self.current_record_index = -1
        self.status_label.config(text="Ready for next record (same context)")

    def next_another_record(self):
        data = self.collect_data()
        if data:
            self.save_data(data, self.current_record_index >= 0, new_record=True)
            self.save_to_cache(str(self.record_number), self.entries)
            self.all_data = self.records.copy()
            self.update_treeview()
        saved_context = {field: self.entries[field].get() for field in self.context_fields}
        self.clear_entries(preserve_fields=self.context_fields)
        self.reset_leh_fields()
        self.reset_photo_fields()
        for field, value in saved_context.items():
            if value and self.entries[field].winfo_exists():
                self.entries[field].insert(0, value)
        self.current_record_index = -1
        self.status_label.config(text="Ready for next record (new context)")

    def new_record(self):
        self.current_record_index = -1
        self.clear_entries()
        self.reset_leh_fields()
        self.reset_photo_fields()
        self.status_label.config(text="Started new record")

    def view_cache(self):
        cache_window = tk.Toplevel(self.root)
        cache_window.title("Cached Records")
        cache_window.geometry("600x400")
        cache_window.transient(self.root)
        cache_window.grab_set()

        tree = ttk.Treeview(cache_window, columns=("Record", "Sample ID", "Tooth Type"), show="headings")
        tree.heading("Record", text="Record Number")
        tree.heading("Sample ID", text="Sample ID")
        tree.heading("Tooth Type", text="Tooth Type")
        tree.column("Record", width=100)
        tree.column("Sample ID", width=200)
        tree.column("Tooth Type", width=200)
        tree.pack(fill="both", expand=True, padx=10, pady=10)

        scrollbar = ttk.Scrollbar(cache_window, orient="vertical", command=tree.yview)
        scrollbar.pack(side="right", fill="y")
        tree.configure(yscrollcommand=scrollbar.set)

        for record_num, data in self.record_cache.items():
            sample_id = data.get("Sample ID", "")
            tooth_type = data.get("Tooth Type", "")
            tree.insert("", "end", values=(record_num, sample_id, tooth_type))

        def show_cached_record(event):
            selection = tree.selection()
            if not selection:
                return
            item = tree.item(selection[0])
            record_num = item["values"][0]
            cached_data = self.record_cache.get(str(record_num))
            if cached_data:
                self.reset_leh_fields()
                self.reset_photo_fields()
                self.clear_entries()
                for field, value in cached_data.items():
                    if field in self.entries and value and self.entries[field].winfo_exists():
                        if isinstance(self.entries[field], tk.Text):
                            self.entries[field].insert("1.0", value)
                        else:
                            self.entries[field].insert(0, value)
                        if field.endswith(("1", "2", "3")) and field[:-1] in self.averages:
                            self.calculate_avg(field[:-1])
                self.canvas.update_idletasks()
                self.canvas.configure(scrollregion=self.canvas.bbox("all"))

        tree.bind("<Double-1>", show_cached_record)
        tk.Button(cache_window, text="Close", command=cache_window.destroy).pack(pady=5)

if __name__ == "__main__":
    app = LEHRecordProgram()
    app.root.mainloop()