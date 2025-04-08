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

        # 強制設置快照資料夾
        self.data_dir = r"C:\Users\shiqi\Desktop\code_test"

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
        self.leh_field_order = self.initial_leh_fields.copy()
        self.context_fields = []
        self.record_number = 1
        self.sample_number = 1  # 新增 sample number
        self.record_order = []

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
            print(f"Failed to save cache: {e}")

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
                self.load_existing_file()
                self.load_metadata()
                file_window.destroy()

        tk.Button(file_window, text="Create New Folder", command=new_folder).pack(pady=5)
        tk.Button(file_window, text="Open Existing File", command=open_file).pack(pady=5)
        file_window.wait_window()

    def setup_context_fields(self):
        if not self.context_fields:
            context_window = tk.Toplevel(self.root)
            context_window.title("Set Context Fields")
            context_window.geometry("300x150")
            context_window.transient(self.root)
            context_window.grab_set()

            tk.Label(context_window, text="Enter Context subfields (comma-separated, e.g., Site, Layer):").pack(pady=10)
            entry = tk.Entry(context_window, width=40, font=self.FONT_CONFIG)
            entry.pack(pady=5)
            entry.focus_set()

            def save_context_fields():
                fields = entry.get().strip()
                if fields:
                    self.context_fields = [f.strip() for f in fields.split(",") if f.strip()]
                    self.basic_fields = self.LABELS[:1] + self.context_fields + self.LABELS[2:9]
                context_window.destroy()

            tk.Button(context_window, text="Save", command=save_context_fields).pack(pady=10)
            entry.bind("<Return>", lambda e: save_context_fields())
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
        self.tree = ttk.Treeview(self.record_inner_frame, columns=("Record Number", "Sample ID", "Tooth Type", "Snapshot File"), show="headings", height=20)
        self.tree.heading("Record Number", text="Record Number")
        self.tree.heading("Sample ID", text="Sample ID")
        self.tree.heading("Tooth Type", text="Tooth Type")
        self.tree.heading("Snapshot File", text="Snapshot File")
        self.tree.column("Record Number", width=80, anchor="w")
        self.tree.column("Sample ID", width=100, anchor="w")
        self.tree.column("Tooth Type", width=100, anchor="w")
        self.tree.column("Snapshot File", width=200, anchor="w")
        self.tree["displaycolumns"] = ("Record Number", "Sample ID", "Tooth Type")
        self.tree.pack(fill="y", expand=True)
        self.tree.bind("<Double-1>", self.show_record)

        # 載入索引檔，重建Treeview
        try:
            import os, json
            snapshot_dir = os.path.join(self.data_dir if self.data_dir else ".", "snapshots")
            index_path = os.path.join(snapshot_dir, "index.json")
            if os.path.exists(index_path):
                with open(index_path, "r", encoding="utf-8") as f:
                    index_list = json.load(f)
                for item in index_list:
                    self.tree.insert("", "end", values=(
                        item.get("record_number", ""),
                        item.get("sample_id", ""),
                        item.get("tooth_type", ""),
                        item.get("snapshot_file", item.get("uuid", "") + ".json")
                    ))
            print(f"Loaded index: {index_path}")
        except Exception as e:
            print(f"Failed to load index: {e}")

        self.update_treeview()

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
        saved_values = {}
        for field in self.leh_field_order:
            for suffix in ["1", "2", "3", " LEH Count", " LEH Type", " CEJ Visible", " Photo ID"]:
                key = f"{field}{suffix}"
                if key in self.entries and self.entries[key].winfo_exists():
                    saved_values[key] = self.entries[key].get()
            if field in self.averages and self.averages[field].winfo_exists():
                saved_values[f"{field}_avg"] = self.averages[field].cget("text")

        for widget in self.leh_frame.grid_slaves():
            if int(widget.grid_info()["row"]) > 0:
                widget.grid_forget()

        self.entries = {k: v for k, v in self.entries.items() if not any(k.startswith(f) for f in self.leh_field_order)}
        self.averages = {k: v for k, v in self.averages.items() if not any(k.startswith(f) for f in self.leh_field_order)}
        self.row_map.clear()

        for i, field in enumerate(self.leh_field_order, 1):
            self.add_leh_field(field, i)
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

        # 找到最後一個同名欄位，插入其後
        last_index = max(i for i, f in enumerate(self.leh_field_order) if f.startswith(label))
        self.leh_field_order.insert(last_index + 1, unique_label)

        self.render_leh_fields()
        self.canvas.update_idletasks()
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        self.entries[f"{unique_label}1"].focus_set()

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
        entry.bind("<KeyPress>", self.validate_numeric_input)

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

    def validate_numeric_input(self, event):
        allowed_keys = ("BackSpace", "Tab", "Left", "Right", "Delete", "KP_Decimal", "Return")
        if event.keysym in allowed_keys:
            return
        if event.char.isdigit() or event.char in (".", "。"):
            return
        return "break"

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
            messagebox.showerror("錯誤", "未選擇檔案！")
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
            messagebox.showerror("錯誤", "未選擇檔案！")
            self.status_label.config(text="No file selected!")
            return
        try:
            # 確保匯出最新資料
            self.all_data = self.records.copy()
            success = self.save_to_file()
            if success:
                self.save_metadata()
                self.status_label.config(text=f"Exported to {os.path.basename(self.current_file)}")
            else:
                messagebox.showerror("錯誤", "匯出檔案失敗！請檢查日誌。")
                self.status_label.config(text="Failed to export file! Check logs for details.")
        except Exception as e:
            messagebox.showerror("錯誤", f"匯出過程發生錯誤：{str(e)}")
            self.status_label.config(text=f"Export error: {str(e)}")

    def update_treeview(self):
        self.tree.delete(*self.tree.get_children())

        for rec in self.records:
            uuid_str = rec.get("uuid", "")
            record_num = rec.get("record_id", "")
            basic_info = rec.get("basic_info", {})
            sample_id = basic_info.get("Sample ID", "N/A")
            tooth_type = basic_info.get("Tooth Type", "N/A")
            snapshot_filename = f"{uuid_str}.json"
            # 顯示record_number數字，隱藏完整快照檔名
            self.tree.insert("", "end", values=(record_num, sample_id, tooth_type, snapshot_filename))

        # 設定Treeview只顯示前三欄
        self.tree["displaycolumns"] = (0, 1, 2)

        print(f"Treeview updated. Total nested records: {len(self.records)}")

    def collect_data(self):
        basic_info = {label: self.entries[label].get() for label in self.basic_fields}
        sample_id = basic_info.get("Sample ID", "")
        tooth_type = basic_info.get("Tooth Type", "")
        if not sample_id or not tooth_type:
            messagebox.showerror("錯誤", "Sample ID 與 Tooth Type 為必填欄位！")
            self.status_label.config(text="Sample ID and Tooth Type are required!")
            return None

        measurements = {}
        for field in self.measurement_fields:
            short_field = self.get_short_label(field)
            measurements[short_field] = [
                self.entries[f"{field}1"].get(),
                self.entries[f"{field}2"].get(),
                self.entries[f"{field}3"].get()
            ]

        other_info = {field: self.entries[field].get("1.0", tk.END).strip() for field in self.other_fields}

        photos = []
        for key in self.entries:
            if key.startswith("Image ID (") and not key.endswith("_type)") and not key.endswith("_type"):
                pid = self.entries[key].get()
                ptype_key = f"{key}_type"
                ptype = self.entries.get(ptype_key, tk.Entry()).get() if ptype_key in self.entries else ""
                photos.append({
                    "id": key,  # 使用完整欄位名稱
                    "type": ptype,
                    "image_id": pid
                })

        leh_list = []
        all_leh_fields = self.initial_leh_fields + self.additional_leh_fields
        for field in all_leh_fields:
            val1 = self.entries[f"{field}1"].get()
            val2 = self.entries[f"{field}2"].get()
            val3 = self.entries[f"{field}3"].get()
            if val1 or val2 or val3:
                try:
                    values = [float(v) for v in [val1, val2, val3] if v]
                    avg = sum(values) / len(values) if values else ""
                except:
                    avg = ""
                leh_list.append({
                    "id": field,  # 唯一ID
                    "leh_side": self.get_short_label(field),
                    "values": [val1, val2, val3],
                    "avg": f"{avg:.2f}" if avg != "" else "",
                    "count": self.entries[f"{field} LEH Count"].get(),
                    "type": self.entries[f"{field} LEH Type"].get(),
                    "cej_visible": self.entries[f"{field} CEJ Visible"].get(),
                    "photo_id": self.entries[f"{field} Photo ID"].get()
                })

        import re
        sample_id_str = basic_info.get("Sample ID", "").replace(" ", "_")
        # 移除特殊字元，僅保留字母數字底線
        sample_id_str = re.sub(r'[^\w]', '_', sample_id_str)
        uuid_str = f"R{self.record_number}_S{self.sample_number}_{sample_id_str}"
        # 生成正確順序的leh_fields
        ordered_leh_fields = self.initial_leh_fields.copy()
        for add_field in self.additional_leh_fields:
            base_label = add_field.split("_")[0]
            # 找最後一個同名欄位
            last_idx = -1
            for idx, f in enumerate(ordered_leh_fields):
                if f.startswith(base_label):
                    last_idx = idx
            insert_pos = last_idx + 1
            ordered_leh_fields.insert(insert_pos, add_field)

        # 生成完整photo_fields
        photo_fields_combined = []
        for key in self.entries:
            if key.startswith("Image ID (") and not key.endswith("_type)") and not key.endswith("_type"):
                label = key[10:-1]
                if label not in photo_fields_combined:
                    photo_fields_combined.append(label)

        print("[DEBUG] current additional_photo_fields:", self.additional_photo_fields)
        print("[DEBUG] combined photo_fields:", photo_fields_combined)
        print("[DEBUG] photos list before save:", photos)
        print("[DEBUG] basic_info:", basic_info)
        print("[DEBUG] measurements:", measurements)
        print("[DEBUG] other_info:", other_info)
        print("[DEBUG] leh_list:", leh_list)

        record = {
            "uuid": uuid_str,
            "record_id": self.record_number,
            "sample_number": self.sample_number,
            "basic_info": basic_info,
            "measurements": measurements,
            "other_info": other_info,
            "photos": photos,
            "leh_list": leh_list,
            "leh_fields": ordered_leh_fields,
            "photo_fields": photo_fields_combined
        }
        print("[DEBUG] Saving record photo_fields:", record["photo_fields"])
        print("[DEBUG] Saving record photos:", record["photos"])
        return record

    def save_data(self, data, is_update=False, new_record=False):
        # 先用當前record_number生成uuid
        sample_id_str = data.get("basic_info", {}).get("Sample ID", "").replace(" ", "_")
        uuid_str = f"R{self.record_number}_S{self.sample_number}_{sample_id_str}"
        snapshot_filename = f"{uuid_str}.json"
        data["uuid"] = uuid_str
        data["record_id"] = self.record_number

        record = data

        # 保存快照
        try:
            import os, json
            snapshot_dir = os.path.join(self.data_dir if self.data_dir else ".", "snapshots")
            os.makedirs(snapshot_dir, exist_ok=True)
            snapshot_path = os.path.join(snapshot_dir, snapshot_filename)
            snapshot_path = os.path.abspath(snapshot_path)
            with open(snapshot_path, "w", encoding="utf-8") as f:
                json.dump(record, f, ensure_ascii=False, indent=2)
            print(f"Saved snapshot: {snapshot_path}")

            # 檢查快照是否存在
            if not os.path.exists(snapshot_path):
                print(f"ERROR: Snapshot file not found after save: {snapshot_path}")
            else:
                print(f"Snapshot file confirmed: {snapshot_path}")

            # 更新索引檔
            index_path = os.path.join(snapshot_dir, "index.json")
            if os.path.exists(index_path):
                with open(index_path, "r", encoding="utf-8") as f:
                    index_list = json.load(f)
            else:
                index_list = []
            # 新增索引
            index_list.append({
                "uuid": uuid_str,
                "snapshot_file": snapshot_path,
                "record_number": record.get("record_id", ""),
                "sample_number": record.get("sample_number", ""),
                "sample_id": record.get("basic_info", {}).get("Sample ID", ""),
                "tooth_type": record.get("basic_info", {}).get("Tooth Type", ""),
                "timestamp": datetime.now().isoformat()
            })
            with open(index_path, "w", encoding="utf-8") as f:
                json.dump(index_list, f, ensure_ascii=False, indent=2)
            print(f"Updated index: {index_path}")

        except Exception as e:
            print(f"Failed to save snapshot or index: {e}")

        except Exception as e:
            print(f"Failed to save snapshot or index: {e}")

        if is_update and self.current_record_index >= 0:
            # 更新現有紀錄
            self.records[self.current_record_index] = record
        else:
            # 新增新紀錄
            self.records.append(record)
            self.record_order.append(snapshot_filename)

        # 儲存完後再自增record_number
        self.record_number += 1

        print(f"Saved nested record: {uuid_str}, Total records: {len(self.records)}, Next record number: {self.record_number}")

    def save_to_file(self):
        try:
            if not self.current_file or not os.path.isdir(os.path.dirname(self.current_file)):
                raise ValueError("Invalid file path or directory")

            fieldnames = ["Record ID"] + self.basic_fields + \
                         [self.get_short_label(f) + i for f in self.measurement_fields for i in ["1", "2", "3"]] + \
                         ["LEH Side", "Value 1", "Value 2", "Value 3", "Avg", "LEH Count", "LEH Type", "CEJ Visible", "Photo ID"] + \
                         self.other_fields + ["Photo Type", "Photo ID"]

            with open(self.current_file, "w", newline="", encoding="utf-8") as file:
                writer = csv.DictWriter(file, fieldnames=fieldnames)
                writer.writeheader()

                for rec in self.records:
                    base_row = {
                        "Record ID": rec.get("record_id", ""),
                    }
                    # 基本資訊
                    base_row.update(rec.get("basic_info", {}))

                    # 測量
                    for key, vals in rec.get("measurements", {}).items():
                        for idx, val in enumerate(vals, 1):
                            base_row[f"{key}{idx}"] = val

                    # 其他資訊
                    base_row.update(rec.get("other_info", {}))

                    # 照片
                    photos = rec.get("photos", [])
                    photo_map = {}
                    for p in photos:
                        photo_map[p.get("type", "")] = p.get("image_id", "")

                    # 若無LEH，輸出一行
                    leh_list = rec.get("leh_list", [])
                    if not leh_list:
                        row = base_row.copy()
                        row.update({
                            "LEH Side": "",
                            "Value 1": "",
                            "Value 2": "",
                            "Value 3": "",
                            "Avg": "",
                            "LEH Count": "",
                            "LEH Type": "",
                            "CEJ Visible": "",
                            "Photo ID": ""
                        })
                        # 只輸出第一張照片
                        if photos:
                            row["Photo Type"] = photos[0].get("type", "")
                            row["Photo ID"] = photos[0].get("image_id", "")
                        writer.writerow(row)
                    else:
                        for leh in leh_list:
                            row = base_row.copy()
                            row.update({
                                "LEH Side": leh.get("leh_side", ""),
                                "Value 1": leh.get("values", ["", "", ""])[0],
                                "Value 2": leh.get("values", ["", "", ""])[1],
                                "Value 3": leh.get("values", ["", "", ""])[2],
                                "Avg": leh.get("avg", ""),
                                "LEH Count": leh.get("count", ""),
                                "LEH Type": leh.get("type", ""),
                                "CEJ Visible": leh.get("cej_visible", ""),
                                "Photo ID": leh.get("photo_id", "")
                            })
                            # 只輸出第一張照片
                            if photos:
                                row["Photo Type"] = photos[0].get("type", "")
                                row["Photo ID"] = photos[0].get("image_id", "")
                            writer.writerow(row)
            return True
        except Exception as e:
            self.status_label.config(text=f"Error exporting file: {str(e)}")
            return False

    def save_metadata(self):
        if not self.data_dir:
            return
        metadata_dir = os.path.join(self.data_dir, "metadata")
        os.makedirs(metadata_dir, exist_ok=True)
        metadata_file = os.path.join(metadata_dir, "metadata.pkl")
        metadata = {
            "records": self.records,
            "record_order": self.record_order,
            "record_number": self.record_number,
            "context_fields": self.context_fields
        }
        try:
            with open(metadata_file, "wb") as f:
                pickle.dump(metadata, f)
            print(f"Metadata saved to {metadata_file}")
            print(f"Saved records: {len(self.records)}, Fields in first record: {self.records[0].keys() if self.records else 'No records'}")
        except Exception as e:
            print(f"Failed to save metadata: {e}")

    def load_metadata(self):
        if not self.data_dir:
            return
        metadata_file = os.path.join(self.data_dir, "metadata", "metadata.pkl")
        if os.path.exists(metadata_file):
            try:
                with open(metadata_file, "rb") as f:
                    metadata = pickle.load(f)
                    self.records = metadata["records"]
                    self.record_order = metadata["record_order"]
                    self.record_number = metadata["record_number"]
                    self.context_fields = metadata.get("context_fields", [])
                    self.basic_fields = self.LABELS[:1] + self.context_fields + self.LABELS[2:9]
                    self.all_data = self.records.copy()
                print(f"Metadata loaded from {metadata_file}")
                print(f"Loaded records: {len(self.records)}, Fields in first record: {self.records[0].keys() if self.records else 'No records'}")
            except Exception as e:
                print(f"Failed to load metadata: {e}")

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
        self.add_photo_id_field(4)
        self.canvas.update_idletasks()
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def open_file(self):
        file_path = filedialog.askopenfilename(filetypes=[("CSV files", "*.csv"), ("All files", "*.*")])
        if not file_path:
            return
        self.current_file = file_path
        self.data_dir = os.path.dirname(file_path)
        self.load_existing_file()
        self.load_metadata()
        self.update_treeview()

    def load_existing_file(self):
        try:
            with open(self.current_file, "r", encoding="utf-8") as file:
                reader = csv.DictReader(file)
                self.all_data = list(reader)
                for row in self.all_data:
                    if "Field Mapping" not in row:
                        row["Field Mapping"] = {"LEH": self.initial_leh_fields, "Photo": self.fixed_photo_types}
                if not self.records:
                    self.records = self.all_data.copy()
                    if self.records:
                        self.record_number = max([int(row["Record Number"]) for row in self.records if row["Record Number"].isdigit()], default=0) + 1
                    else:
                        self.record_number = 1
                    self.record_order = [row["Record Number"] for row in self.records if row["Record Number"] not in self.record_order]
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
            self.save_metadata()
            self.status_label.config(text=f"Saved as {os.path.basename(self.current_file)}")

    def show_record(self, event=None):
        selection = self.tree.selection()
        if not selection:
            return
        item = selection[0]
        values = self.tree.item(item)["values"]
        print(f"[DEBUG] Treeview values: {values}")
        if len(values) < 4:
            self.status_label.config(text="Snapshot filename missing")
            return
        snapshot_filename = values[3]
        print(f"[DEBUG] Snapshot filename from Treeview: {snapshot_filename}")

        # 載入對應快照
        try:
            import os, json
            snapshot_dir = os.path.join(self.data_dir if self.data_dir else ".", "snapshots")
            snapshot_path = os.path.join(snapshot_dir, snapshot_filename)
            print(f"[DEBUG] Snapshot full path: {snapshot_path}")
            print(f"[DEBUG] Snapshot exists? {os.path.exists(snapshot_path)}")
            if not os.path.exists(snapshot_path):
                self.status_label.config(text="Snapshot not found")
                return
            with open(snapshot_path, "r", encoding="utf-8") as f:
                target_record = json.load(f)
            print(f"Loaded snapshot: {snapshot_path}")
        except Exception as e:
            self.status_label.config(text=f"Failed to load snapshot: {e}")
            return

        print(f"Showing nested record {snapshot_filename}")

        self.clear_entries()

        # 刪除所有LEH動態欄位元件
        for widget in self.leh_frame.grid_slaves():
            if int(widget.grid_info().get("row", 0)) > 0:
                widget.destroy()
        self.additional_leh_fields = []
        self.all_leh_fields = self.initial_leh_fields.copy()
        self.leh_field_order = self.initial_leh_fields.copy()

        # 根據快照中的leh_fields重建欄位順序
        leh_fields = target_record.get("leh_fields", self.initial_leh_fields.copy())
        self.all_leh_fields = leh_fields.copy()
        self.leh_field_order = leh_fields.copy()
        self.additional_leh_fields = [f for f in leh_fields if f not in self.initial_leh_fields]

        # 重新渲染LEH欄位
        self.render_leh_fields()

        # 刪除所有Photo動態欄位元件
        for widget in self.photo_frame.grid_slaves():
            if int(widget.grid_info().get("row", 0)) > len(self.fixed_photo_types):
                widget.destroy()
        self.additional_photo_fields = []
        self.all_photo_fields = self.fixed_photo_types.copy()

        # 根據快照中的photo_fields重建欄位順序
        photo_fields = target_record.get("photo_fields", self.fixed_photo_types.copy())
        print("[DEBUG] Loaded photo_fields:", photo_fields)
        self.all_photo_fields = photo_fields.copy()
        self.additional_photo_fields = [f for f in photo_fields if f not in self.fixed_photo_types]

        # 刪除所有Photo動態欄位元件
        for widget in self.photo_frame.grid_slaves():
            if int(widget.grid_info().get("row", 0)) > len(self.fixed_photo_types):
                widget.destroy()

        # 重新渲染Photo欄位
        for i, ptype in enumerate(self.fixed_photo_types, 1):
            # 固定欄位已存在
            pass
        base_row = len(self.fixed_photo_types) + 1
        for idx, add_field in enumerate(self.additional_photo_fields, base_row):
            self.add_photo_id_field(idx, add_field.split("add")[1] if "add" in add_field else "")

        # 重新渲染LEH欄位
        self.render_leh_fields()

        # 填入Photo資料
        photos = target_record.get("photos", [])
        for p in photos:
            pid = p.get("image_id", "")
            pid_type = p.get("type", "")
            pid_id = p.get("id", pid_type)
            if f"Image ID ({pid_id})" in self.entries:
                self.entries[f"Image ID ({pid_id})"].insert(0, pid)
            if f"Image ID ({pid_id})_type" in self.entries:
                self.entries[f"Image ID ({pid_id})_type"].insert(0, pid_type)


        # 基本資訊
        basic_info = target_record.get("basic_info", {})
        for field in self.basic_fields:
            if field in basic_info:
                self.entries[field].insert(0, basic_info[field])

        # 測量
        measurements = target_record.get("measurements", {})
        for key, vals in measurements.items():
            for idx, val in enumerate(vals, 1):
                entry_key = None
                for f in self.measurement_fields:
                    if self.get_short_label(f) == key:
                        entry_key = f"{f}{idx}"
                        break
                if entry_key and entry_key in self.entries:
                    self.entries[entry_key].insert(0, val)
            # 計算平均
            for f in self.measurement_fields:
                if self.get_short_label(f) == key:
                    self.calculate_avg(f)

        # 其他資訊
        other_info = target_record.get("other_info", {})
        for field in self.other_fields:
            if field in other_info:
                self.entries[field].insert("1.0", other_info[field])

        # 照片
        photos = target_record.get("photos", [])
        for p in photos:
            ptype = p.get("type", "")
            pid = p.get("image_id", "")
            for key in self.entries:
                if key.endswith("_type") and self.entries[key].winfo_exists():
                    continue
                if key.endswith("_type") or key.endswith("_id"):
                    continue
            if f"Image ID ({ptype})" in self.entries:
                self.entries[f"Image ID ({ptype})"].insert(0, pid)
            if f"Image ID ({ptype})_type" in self.entries:
                self.entries[f"Image ID ({ptype})_type"].insert(0, ptype)

        # LEH
        leh_list = target_record.get("leh_list", [])
        for leh in leh_list:
            leh_id = leh.get("id", "")
            # 找對應欄位
            if leh_id not in self.all_leh_fields:
                # 動態新增
                base_label = leh.get("leh_side", "")
                suffix_num = len([f for f in self.additional_leh_fields if f.startswith(base_label)]) + 1
                unique_label = f"{base_label}_{suffix_num}"
                self.additional_leh_fields.append(unique_label)
                self.all_leh_fields.append(unique_label)
                self.leh_field_order.append(unique_label)
                self.render_leh_fields()
            # 重新整理欄位
            self.all_leh_fields = self.initial_leh_fields + self.additional_leh_fields

        # 重新渲染
        self.render_leh_fields()

        # 填入LEH資料
        for leh in leh_list:
            leh_id = leh.get("id", "")
            full_label = leh_id if leh_id in self.all_leh_fields else None
            if not full_label:
                continue
            vals = leh.get("values", ["", "", ""])
            for idx, val in enumerate(vals, 1):
                key = f"{full_label}{idx}"
                if key in self.entries:
                    self.entries[key].insert(0, val)
            self.averages[full_label].config(text=leh.get("avg", "N/A"))
            for suffix, k in [(" LEH Count", "count"), (" LEH Type", "type"), (" CEJ Visible", "cej_visible"), (" Photo ID", "photo_id")]:
                key = f"{full_label}{suffix}"
                if key in self.entries:
                    self.entries[key].insert(0, leh.get(k, ""))

        self.canvas.update_idletasks()
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        self.status_label.config(text=f"Showing record {target_record.get('record_id', '')}")

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
            if value and field in self.entries:
                self.entries[field].insert(0, value)
        for field, value in saved_photo_data.items():
            if value and field in self.entries:
                self.entries[field].insert(0, value)
        for field, value in saved_photo_types.items():
            if value and field in self.entries:
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

if __name__ == "__main__":
    app = LEHRecordProgram()
    app.root.mainloop()
