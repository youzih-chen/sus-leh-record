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
        """設置常數"""
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
            "LEH Count", "LEH Type", "Notes", "Pathology", 
            "Photo ID (Buccal)", "Photo ID (Lingual)", "Photo ID (Occlusal)"
        ]
        
        self.basic_fields = self.LABELS[:9]
        self.measurement_fields = self.LABELS[9:19]
        self.initial_leh_fields = self.LABELS[19:25]
        self.leh_count_type = self.LABELS[25:27]
        self.other_fields = self.LABELS[27:]

    def setup_variables(self):
        """初始化變數"""
        self.entries = {}
        self.averages = {}
        self.records = []  # 儲存所有記錄的內部列表
        self.all_data = []  # 用於最終寫入 CSV
        self.current_file = None
        self.data_dir = None
        self.additional_leh_fields = []
        self.row_map = {}
        self.current_record_index = -1
        self.all_leh_fields = self.initial_leh_fields.copy()
        self.context_fields = []

    def setup_cache(self):
        """設置快取機制"""
        self.cache_file = os.path.join(tempfile.gettempdir(), 'leh_record_cache.pkl')
        self.record_cache = {}
        if os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, 'rb') as f:
                    self.record_cache = pickle.load(f)
            except:
                self.record_cache = {}

    def save_to_cache(self, record_num, data):
        """保存數據到快取"""
        self.record_cache[record_num] = data
        try:
            with open(self.cache_file, 'wb') as f:
                pickle.dump(self.record_cache, f)
        except Exception as e:
            print(f"快取保存失敗: {e}")

    def get_from_cache(self, record_num):
        """從快取獲取數據"""
        return self.record_cache.get(record_num)

    def cleanup_cache(self):
        """清理快取文件"""
        try:
            if os.path.exists(self.cache_file):
                os.remove(self.cache_file)
        except:
            pass

    def create_main_window(self):
        """創建主視窗"""
        self.root = tk.Tk()
        self.root.title("LEH Record Program")
        self.root.geometry("1400x800")
        self.root.resizable(True, True)

    def setup_file_location(self):
        """選擇檔案儲存位置或開啟舊檔"""
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
        """設定 Context 相關欄位"""
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
        """創建主要框架"""
        self.outer_frame = tk.Frame(self.root)
        self.outer_frame.pack(fill="both", expand=True)
        self.create_record_frame()
        self.create_main_frame()
        self.button_frame = tk.Frame(self.root)
        self.button_frame.pack(side="bottom", pady=10)
        self.status_label = tk.Label(self.root, text="", font=self.FONT_CONFIG)
        self.status_label.pack(side="bottom", pady=5)

    def create_record_frame(self):
        """創建左側記錄框架"""
        self.record_frame = ttk.LabelFrame(self.outer_frame, text="Previous Records", padding=10)
        self.record_frame.pack(side="left", fill="y", padx=10, pady=10)
        self.record_canvas = tk.Canvas(self.record_frame, width=200)
        self.record_canvas.pack(side="left", fill="both", expand=True)
        record_scrollbar = ttk.Scrollbar(self.record_frame, orient="vertical", command=self.record_canvas.yview)
        record_scrollbar.pack(side="right", fill="y")
        self.record_canvas.configure(yscrollcommand=record_scrollbar.set)
        self.record_inner_frame = tk.Frame(self.record_canvas)
        self.record_canvas.create_window((0, 0), window=self.record_inner_frame, anchor="nw")
        self.tree = ttk.Treeview(self.record_inner_frame, columns=("Name",), show="headings", height=20)
        self.tree.heading("Name", text="Sample ID + Tooth Type")
        self.tree.column("Name", width=180, anchor="w")
        self.tree.pack(fill="y", expand=True)
        self.tree.bind("<Double-1>", self.show_record)

    def create_main_frame(self):
        """創建主框架"""
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
        """創建各個區段"""
        self.top_frame = tk.Frame(self.inner_frame)
        self.top_frame.grid(row=0, column=0, sticky="ew")
        self.create_basic_section()
        self.create_measurement_section()
        self.create_leh_section()
        self.create_other_section()

    def create_basic_section(self):
        """創建基本資訊區域"""
        basic_frame = ttk.LabelFrame(self.top_frame, text="Basic Information", padding=10)
        basic_frame.pack(side="left", fill="y", padx=10, pady=10)
        for i, field in enumerate(self.basic_fields):
            tk.Label(basic_frame, text=field, font=self.FONT_CONFIG).grid(row=i, column=0, padx=5, pady=2, sticky="e")
            entry = tk.Entry(basic_frame, width=30, font=self.FONT_CONFIG)
            entry.grid(row=i, column=1, padx=5, pady=2)
            self.entries[field] = entry

    def create_measurement_section(self):
        """創建測量區域"""
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
        """創建LEH記錄區域"""
        self.leh_frame = ttk.LabelFrame(self.inner_frame, text="LEH Records", padding=10)
        self.leh_frame.grid(row=1, column=0, sticky="ew", padx=10, pady=10)
        headers = ["LEH Count", "LEH Type", "CEJ Visible", "Photo ID"]
        for i, header in enumerate(headers):
            tk.Label(self.leh_frame, text=header, font=self.FONT_CONFIG).grid(row=0, column=i+5, padx=5, pady=2, sticky="w")
        for i, field in enumerate(self.initial_leh_fields, 1):
            self.add_leh_field(field, i)

    def add_leh_field(self, label, row, suffix=""):
        """添加單個LEH欄位行"""
        unique_label = f"{label}_{suffix}" if suffix else label
        short_label = self.get_short_label(label)
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
        add_button = ttk.Button(self.leh_frame, text="+", width=2, command=lambda l=label, r=row: self.add_new_leh_field(l, r))
        add_button.grid(row=row, column=9, padx=2, pady=2)
        all_widgets = entries + [count_entry, type_entry, cej_entry, photo_entry, add_button]
        self.setup_navigation(all_widgets)

    def add_new_leh_field(self, label, row):
        """添加新的 LEH 欄位行"""
        suffix = str(len([f for f in self.additional_leh_fields if f.startswith(label)]) + 1)
        unique_label = f"{label}_{suffix}"
        self.additional_leh_fields.append(unique_label)
        self.all_leh_fields = self.initial_leh_fields + self.additional_leh_fields
        insert_row = row + 1
        for field in sorted(self.row_map.keys(), key=lambda x: self.row_map[x], reverse=True):
            if self.row_map[field] >= insert_row:
                for widget in self.leh_frame.grid_slaves(row=self.row_map[field]):
                    widget.grid(row=self.row_map[field] + 1)
                self.row_map[field] += 1
        self.add_leh_field(label, insert_row, suffix)
        self.canvas.update_idletasks()
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        self.entries[f"{unique_label}1"].focus_set()

    def create_other_section(self):
        """創建其他資訊區域"""
        other_frame = ttk.LabelFrame(self.inner_frame, text="Other Information", padding=10)
        other_frame.grid(row=2, column=0, sticky="ew", padx=10, pady=10)
        for i, field in enumerate(self.other_fields):
            tk.Label(other_frame, text=field, font=self.FONT_CONFIG).grid(row=i, column=0, padx=5, pady=2, sticky="ne")
            if field in ["Notes", "Pathology"]:
                text_frame = tk.Frame(other_frame)
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
                    return "break"
                text_widget.bind("<Tab>", handle_tab)
                self.entries[field] = text_widget
            else:
                entry = tk.Entry(other_frame, width=30, font=self.FONT_CONFIG)
                entry.grid(row=i, column=1, padx=5, pady=2, sticky="w")
                self.entries[field] = entry

    def setup_navigation(self, widgets):
        """設置tab順序和方向鍵導航"""
        for widget in widgets:
            widget.configure(takefocus=1)
            if isinstance(widget, tk.Entry):
                for direction in ["Up", "Down", "Left", "Right"]:
                    widget.bind(f"<{direction}>", lambda e, w=widget: self.handle_arrow_key(e, w))

    def setup_measurement_bindings(self, entry, field):
        """設置測量值輸入框的事件綁定"""
        entry.bind("<KeyRelease>", lambda e, f=field: self.calculate_avg(f))
        entry.bind("<KeyPress>", lambda e, f=field: self.calculate_avg(f))
        entry.bind("<Key>", lambda e, ent=entry, f=field: self.handle_decimal_input(e, ent, f))

    def create_buttons(self):
        """創建按鈕"""
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

    def setup_menu(self):
        """設置選單"""
        menu_bar = tk.Menu(self.root)
        self.root.config(menu=menu_bar)
        file_menu = tk.Menu(menu_bar, tearoff=0)
        menu_bar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Open File", command=self.open_file)
        file_menu.add_command(label="Save As", command=self.save_as)

    def setup_bindings(self):
        """設置全局事件綁定"""
        self.canvas.bind_all("<MouseWheel>", self.on_mouse_wheel)
        self.canvas.bind_all("<Button-4>", self.on_mouse_wheel)
        self.canvas.bind_all("<Button-5>", self.on_mouse_wheel)
        self.record_inner_frame.bind("<Configure>", lambda e: self.record_canvas.configure(scrollregion=self.record_canvas.bbox("all")))
        self.inner_frame.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))

    def calculate_avg(self, unique_label):
        """計算平均值"""
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
        """處理小數點輸入"""
        if event.char in [".", "。"] or event.keysym == "KP_Decimal":
            current_pos = entry.index(tk.INSERT)
            entry.insert(current_pos, ".")
            self.calculate_avg(unique_label)
            return "break"
        return None

    def handle_arrow_key(self, event, current_widget):
        """處理方向鍵導航"""
        if not isinstance(current_widget, tk.Entry):
            return
        current_key = [key for key, widget in self.entries.items() if widget == current_widget][0]
        if event.keysym == "Up":
            prev_row = self.row_map.get(current_key, 1) - 1
            if prev_row >= 1:
                for key, row in self.row_map.items():
                    if row == prev_row:
                        self.entries[key].focus_set()
                        break
        elif event.keysym == "Down":
            next_row = self.row_map.get(current_key, 1) + 1
            if next_row <= max(self.row_map.values()):
                for key, row in self.row_map.items():
                    if row == next_row:
                        self.entries[key].focus_set()
                        break
        elif event.keysym == "Left":
            if current_key.endswith("2"):
                self.entries[current_key[:-1] + "1"].focus_set()
            elif current_key.endswith("3"):
                self.entries[current_key[:-1] + "2"].focus_set()
        elif event.keysym == "Right":
            if current_key.endswith("1"):
                self.entries[current_key[:-1] + "2"].focus_set()
            elif current_key.endswith("2"):
                self.entries[current_key[:-1] + "3"].focus_set()

    def on_mouse_wheel(self, event):
        """處理滑鼠滾輪事件"""
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
        """從標籤中提取括號內的簡短標籤"""
        if "(" in label and ")" in label:
            return label[label.index("(")+1:label.index(")")]
        return label

    def save_and_clear(self):
        """儲存到 CSV 並清空輸入框"""
        self.root.focus_set()
        if not self.current_file:
            return
        data = self.collect_data()
        if not data:
            return
        self.save_data(data, self.current_record_index >= 0)  # 更新內部記錄
        self.all_data = self.records.copy()  # 準備寫入 CSV 的資料
        self.save_to_file()  # 寫入 CSV
        saved_data = {field: self.entries[field].get() for field in self.basic_fields}
        self.clear_entries()
        for field, value in saved_data.items():
            self.entries[field].insert(0, value)
        self.reset_leh_fields()
        self.status_label.config(text=f"Saved to {os.path.basename(self.current_file)}")

    def collect_data(self):
        """收集所有輸入資料"""
        base_data = {label: self.entries[label].get() or "n/a" for label in self.basic_fields}
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
                measurement_data[f"{short_field}{i}"] = self.entries[key].get() or "n/a"
        other_data = {}
        for label in self.other_fields:
            if isinstance(self.entries[label], tk.Text):
                other_data[label] = self.entries[label].get("1.0", tk.END).strip() or "n/a"
            else:
                other_data[label] = self.entries[label].get() or "n/a"
        leh_rows = []
        all_leh_fields = self.initial_leh_fields + self.additional_leh_fields
        common_data = {**base_data, **measurement_data, **other_data}
        for field in all_leh_fields:
            val1 = self.entries[f"{field}1"].get()
            val2 = self.entries[f"{field}2"].get()
            val3 = self.entries[f"{field}3"].get()
            if val1 or val2 or val3:
                row_data = common_data.copy()
                row_data.update({
                    "LEH Side": field,
                    "Value 1": val1 or "n/a",
                    "Value 2": val2 or "n/a",
                    "Value 3": val3 or "n/a",
                    "LEH Count": self.entries[f"{field} LEH Count"].get() or "n/a",
                    "LEH Type": self.entries[f"{field} LEH Type"].get() or "n/a",
                    "CEJ Visible": self.entries[f"{field} CEJ Visible"].get() or "n/a",
                    "Photo ID": self.entries[f"{field} Photo ID"].get() or "n/a"
                })
                values = [float(v) for v in [val1, val2, val3] if v and v != "n/a"]
                row_data["Avg"] = f"{sum(values) / len(values):.2f}" if values else "n/a"
                leh_rows.append(row_data)
        return {"base_data": base_data, "leh_rows": leh_rows}

    def save_data(self, data, is_update=False):
        """儲存資料到內部記錄列表"""
        base_data = data["base_data"]
        leh_rows = data["leh_rows"]
        record_num = self.records[self.current_record_index]["Record Number"] if is_update else str(len([r for r in self.records if "Record Number" in r]) + 1)
        if is_update:
            self.records = [r for r in self.records if r["Record Number"] != record_num]
            self.tree.delete(self.tree.get_children()[self.current_record_index])
        
        record_data = []
        common_data = base_data.copy()
        measurement_data = {f"{self.get_short_label(field)}{i}": self.entries[f"{field}{i}"].get() or "n/a" 
                            for field in self.measurement_fields for i in ["1", "2", "3"]}
        common_data.update(measurement_data)
        other_data = {field: (self.entries[field].get("1.0", tk.END).strip() if isinstance(self.entries[field], tk.Text) else self.entries[field].get()) or "n/a" 
                      for field in self.other_fields}
        common_data.update(other_data)
        if not leh_rows:
            row_data = {"Record Number": record_num, "LEH Side": "", "Value 1": "n/a", "Value 2": "n/a", "Value 3": "n/a",
                        "Avg": "n/a", "LEH Count": "n/a", "LEH Type": "n/a", "CEJ Visible": "n/a", "Photo ID": "n/a"}
            row_data.update(common_data)
            record_data.append(row_data)
        else:
            for row in leh_rows:
                row_data = row.copy()
                row_data["Record Number"] = record_num
                row_data.update(common_data)
                record_data.append(row_data)
        
        self.records.extend(record_data)
        record_name = f"{record_num}. {base_data['Sample ID']} - {base_data['Tooth Type']}"
        if is_update:
            self.tree.insert("", self.current_record_index, values=(record_name,))
        else:
            self.tree.insert("", "end", values=(record_name,))
        self.status_label.config(text=f"[{record_name}] {'Updated' if is_update else 'Saved'}")

    def save_to_file(self):
        """將資料寫入CSV檔案"""
        try:
            fieldnames = ["Record Number"] + self.basic_fields + \
                         [self.get_short_label(field) + i for field in self.measurement_fields for i in ["1", "2", "3"]] + \
                         ["LEH Side", "Value 1", "Value 2", "Value 3", "Avg", "LEH Count", "LEH Type", "CEJ Visible", "Photo ID"] + \
                         self.other_fields
            with open(self.current_file, "w", newline="", encoding="utf-8") as file:
                writer = csv.DictWriter(file, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(self.all_data)
        except Exception as e:
            self.status_label.config(text=f"Error saving file: {str(e)}")
            return False
        return True

    def clear_entries(self):
        """清空所有輸入框"""
        for entry in self.entries.values():
            if isinstance(entry, tk.Text):
                entry.delete("1.0", tk.END)
            else:
                entry.delete(0, tk.END)
        for avg_label in self.averages.values():
            avg_label.config(text="N/A")

    def clear_leh_entries(self):
        """僅清空LEH記錄相關欄位"""
        for field in self.all_leh_fields:
            for i in ["1", "2", "3"]:
                if f"{field}{i}" in self.entries:
                    self.entries[f"{field}{i}"].delete(0, tk.END)
            if f"{field} LEH Count" in self.entries:
                self.entries[f"{field} LEH Count"].delete(0, tk.END)
            if f"{field} LEH Type" in self.entries:
                self.entries[f"{field} LEH Type"].delete(0, tk.END)
            if f"{field} CEJ Visible" in self.entries:
                self.entries[f"{field} CEJ Visible"].delete(0, tk.END)
            if f"{field} Photo ID" in self.entries:
                self.entries[f"{field} Photo ID"].delete(0, tk.END)
            if field in self.averages:
                self.averages[field].config(text="N/A")
        for field in self.other_fields:
            if isinstance(self.entries[field], tk.Text):
                self.entries[field].delete("1.0", tk.END)
            else:
                self.entries[field].delete(0, tk.END)

    def reset_leh_fields(self):
        """重置額外的 LEH 欄位"""
        for field in self.additional_leh_fields:
            for widget in self.leh_frame.grid_slaves():
                if widget.grid_info()["row"] == self.row_map[field]:
                    widget.destroy()
        for field in list(self.entries.keys()):
            if field.startswith(tuple(self.additional_leh_fields)):
                del self.entries[field]
        for field in list(self.averages.keys()):
            if field in self.additional_leh_fields:
                del self.averages[field]
        self.additional_leh_fields = []
        self.all_leh_fields = self.initial_leh_fields.copy()
        for i, field in enumerate(self.initial_leh_fields, 1):
            self.row_map[field] = i

    def open_file(self):
        """開啟檔案（從選單）"""
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
        """載入現有檔案數據"""
        try:
            with open(self.current_file, "r", encoding="utf-8") as file:
                reader = csv.DictReader(file)
                self.all_data = list(reader)
                self.records = self.all_data.copy()
            self.tree.delete(*self.tree.get_children())
            records_by_num = {}
            for row in self.records:
                record_num = row["Record Number"]
                if record_num not in records_by_num:
                    records_by_num[record_num] = row
            for record_num, row in records_by_num.items():
                record_name = f"{record_num}. {row['Sample ID']} - {row['Tooth Type']}"
                self.tree.insert("", "end", values=(record_name,))
            self.status_label.config(text=f"Loaded file: {os.path.basename(self.current_file)}")
        except Exception as e:
            self.status_label.config(text=f"Error loading file: {str(e)}")

    def save_as(self):
        """另存新檔"""
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
        """顯示選定的記錄"""
        selection = self.tree.selection()
        if not selection:
            return
        item = selection[0]
        self.current_record_index = self.tree.index(item)
        self.clear_entries()
        self.reset_leh_fields()
        record_num = self.records[self.current_record_index]["Record Number"]
        record_data = [row for row in self.records if row["Record Number"] == record_num]
        if not record_data:
            return
        first_row = record_data[0]
        for field in self.basic_fields + self.other_fields:
            if field in first_row and first_row[field] != "n/a":
                if isinstance(self.entries[field], tk.Text):
                    self.entries[field].insert("1.0", first_row[field])
                else:
                    self.entries[field].insert(0, first_row[field])
        for field in self.measurement_fields:
            short_field = self.get_short_label(field)
            for i in ["1", "2", "3"]:
                key = f"{short_field}{i}"
                if key in first_row and first_row[key] != "n/a":
                    self.entries[f"{field}{i}"].insert(0, first_row[key])
            self.calculate_avg(field)
        for row in record_data:
            leh_side = row.get("LEH Side", "")
            if not leh_side or leh_side == "n/a":
                continue
            full_label = next((f for f in self.initial_leh_fields if self.get_short_label(f) == leh_side), leh_side)
            if "_" in leh_side and leh_side not in self.all_leh_fields:
                base_label = leh_side.split("_")[0]
                for f in self.initial_leh_fields:
                    if self.get_short_label(f) == base_label:
                        self.add_new_leh_field(f, self.row_map[f])
                        full_label = leh_side
                        break
            for i in ["1", "2", "3"]:
                if f"Value {i}" in row and row[f"Value {i}"] != "n/a":
                    self.entries[f"{full_label}{i}"].insert(0, row[f"Value {i}"])
            for field_type in ["LEH Count", "LEH Type", "CEJ Visible", "Photo ID"]:
                if field_type in row and row[field_type] != "n/a":
                    self.entries[f"{full_label} {field_type}"].insert(0, row[field_type])
            self.calculate_avg(full_label)

    def show_previous_record(self):
        """顯示上一筆記錄"""
        if self.current_record_index > 0:
            self.current_record_index -= 1
            self.tree.selection_set(self.tree.get_children()[self.current_record_index])
            self.show_record()

    def next_record(self):
        """顯示下一筆記錄（僅保留基本資訊，清空測量值、LEH 和其他資訊）"""
        data = self.collect_data()
        if data:
            self.save_data(data, self.current_record_index >= 0)  # 儲存到內部記錄
        
        # 儲存基本資訊
        saved_data = {field: self.entries[field].get() for field in self.basic_fields}
        # 清空所有欄位
        self.clear_entries()
        # 恢復基本資訊
        for field, value in saved_data.items():
            self.entries[field].delete(0, tk.END)
            self.entries[field].insert(0, value)
        # 重設 LEH 欄位
        self.reset_leh_fields()
        self.current_record_index = -1
        self.status_label.config(text="Ready for next record (same context)")

    def next_another_record(self):
        """顯示下一筆記錄（保留Context，其他清空）"""
        data = self.collect_data()
        if data:
            self.save_data(data, self.current_record_index >= 0)
        
        saved_context = {field: self.entries[field].get() for field in self.context_fields}
        self.clear_entries()
        self.reset_leh_fields()
        for field, value in saved_context.items():
            self.entries[field].insert(0, value)
        self.current_record_index = -1
        self.status_label.config(text="Ready for next record (new context)")

    def new_record(self):
        """開始新記錄"""
        self.current_record_index = -1
        self.clear_entries()
        self.reset_leh_fields()
        self.status_label.config(text="Started new record")

if __name__ == "__main__":
    app = LEHRecordProgram()
    app.root.mainloop()