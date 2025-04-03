import tkinter as tk
from tkinter import ttk, filedialog
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
        self.setup_cache()  # 添加這行
        self.create_main_window()
        self.create_frames()
        self.create_sections()
        self.create_buttons()
        self.setup_bindings()
        self.setup_menu()
        atexit.register(self.cleanup_cache)  # 添加這行

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
            "LEH Count", "LEH Type", "CEJ Visible", "Notes", "Pathology", 
            "Photo ID (Buccal)", "Photo ID (Lingual)", "Photo ID (Occlusal)"
        ]
        
        # 分區欄位
        self.basic_fields = self.LABELS[:9]
        self.measurement_fields = self.LABELS[9:19]
        self.initial_leh_fields = self.LABELS[19:25]
        self.leh_count_type = self.LABELS[25:27]
        self.other_fields = self.LABELS[27:]

    def setup_variables(self):
        """初始化變數"""
        self.entries = {}
        self.averages = {}
        self.records = []
        self.all_data = []
        self.current_file = None
        self.additional_leh_fields = []
        self.row_map = {}
        self.current_record_index = -1
        self.all_leh_fields = self.initial_leh_fields.copy()

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

    def create_frames(self):
        """創建主要框架"""
        # 外層框架
        self.outer_frame = tk.Frame(self.root)
        self.outer_frame.pack(fill="both", expand=True)

        # 創建左側記錄框架
        self.create_record_frame()
        
        # 創建主框架
        self.create_main_frame()
        
        # 創建按鈕框架
        self.button_frame = tk.Frame(self.root)
        self.button_frame.pack(side="bottom", pady=10)

        # 創建狀態標籤
        self.status_label = tk.Label(self.root, text="", font=self.FONT_CONFIG)
        self.status_label.pack(side="bottom", pady=5)

    def create_record_frame(self):
        """創建左側記錄框架"""
        self.record_frame = ttk.LabelFrame(self.outer_frame, text="Previous Records", padding=10)
        self.record_frame.pack(side="left", fill="y", padx=10, pady=10)

        self.record_canvas = tk.Canvas(self.record_frame, width=200)
        self.record_canvas.pack(side="left", fill="both", expand=True)

        record_scrollbar = ttk.Scrollbar(self.record_frame, orient="vertical", 
                                       command=self.record_canvas.yview)
        record_scrollbar.pack(side="right", fill="y")

        self.record_canvas.configure(yscrollcommand=record_scrollbar.set)

        self.record_inner_frame = tk.Frame(self.record_canvas)
        self.record_canvas.create_window((0, 0), window=self.record_inner_frame, anchor="nw")

        self.tree = ttk.Treeview(self.record_inner_frame, columns=("Name",), 
                                show="headings", height=20)
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

        v_scrollbar = ttk.Scrollbar(self.main_frame, orient="vertical", 
                                  command=self.canvas.yview)
        v_scrollbar.pack(side="right", fill="y")

        self.canvas.configure(yscrollcommand=v_scrollbar.set)

        self.inner_frame = tk.Frame(self.canvas)
        self.canvas.create_window((0, 0), window=self.inner_frame, anchor="nw")

    def create_sections(self):
        """創建各個區段"""
        # 創建頂部框架
        self.top_frame = tk.Frame(self.inner_frame)
        self.top_frame.grid(row=0, column=0, sticky="ew")

        # 創建各個區段
        self.create_basic_section()
        self.create_measurement_section()
        self.create_leh_section()
        self.create_other_section()

    def create_basic_section(self):
        """創建基本資訊區域"""
        basic_frame = ttk.LabelFrame(self.top_frame, text="Basic Information", padding=10)
        basic_frame.pack(side="left", fill="y", padx=10, pady=10)
        
        for i, field in enumerate(self.basic_fields):
            tk.Label(basic_frame, text=field, font=self.FONT_CONFIG).grid(
                row=i, column=0, padx=5, pady=2, sticky="e")
            entry = tk.Entry(basic_frame, width=30, font=self.FONT_CONFIG)
            entry.grid(row=i, column=1, padx=5, pady=2)
            self.entries[field] = entry

    def create_measurement_section(self):
        """創建測量區域"""
        measurement_frame = ttk.LabelFrame(self.top_frame, text="Measurements", padding=10)
        measurement_frame.pack(side="left", fill="y", padx=10, pady=10)
        
        for i, field in enumerate(self.measurement_fields):
            short_label = self.get_short_label(field)
            tk.Label(measurement_frame, text=short_label, font=self.FONT_CONFIG).grid(
                row=i, column=0, padx=5, pady=2, sticky="e")
            
            # 創建三個輸入框和平均值標籤
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
        
        # 添加表頭
        headers = ["LEH Count", "LEH Type", "Photo ID"]
        for i, header in enumerate(headers):
            tk.Label(self.leh_frame, text=header, font=self.FONT_CONFIG).grid(
                row=0, column=i+5, padx=5, pady=2, sticky="w")
        
        # 添加初始LEH欄位
        for i, field in enumerate(self.initial_leh_fields, 1):
            self.add_leh_field(field, i)

    def add_leh_field(self, label, row, suffix=""):
        """添加單個LEH欄位行"""
        unique_label = f"{label}_{suffix}" if suffix else label
        short_label = self.get_short_label(label)
        
        tk.Label(self.leh_frame, text=short_label, font=self.FONT_CONFIG).grid(
            row=row, column=0, padx=5, pady=2, sticky="e")
        
        # 創建測量值輸入框
        entries = []
        for i in range(3):
            entry = tk.Entry(self.leh_frame, width=8, font=self.FONT_CONFIG)
            entry.grid(row=row, column=i+1, padx=2, pady=2)
            self.entries[f"{unique_label}{i+1}"] = entry
            entries.append(entry)
            self.setup_measurement_bindings(entry, unique_label)
        
        # 創建平均值標籤
        avg_label = tk.Label(self.leh_frame, text="N/A", font=self.FONT_CONFIG)
        avg_label.grid(row=row, column=4, padx=5, pady=2)
        self.averages[unique_label] = avg_label
        
        # 創建其他輸入框
        count_entry = tk.Entry(self.leh_frame, width=10, font=self.FONT_CONFIG)
        type_entry = tk.Entry(self.leh_frame, width=10, font=self.FONT_CONFIG)
        photo_entry = tk.Entry(self.leh_frame, width=15, font=self.FONT_CONFIG)
        
        count_entry.grid(row=row, column=5, padx=2, pady=2)
        type_entry.grid(row=row, column=6, padx=2, pady=2)
        photo_entry.grid(row=row, column=7, padx=2, pady=2)
        
        self.entries[f"{unique_label} LEH Count"] = count_entry
        self.entries[f"{unique_label} LEH Type"] = type_entry
        self.entries[f"{unique_label} Photo ID"] = photo_entry
        
        # 添加"+"按鈕
        add_button = ttk.Button(self.leh_frame, text="+", width=2,
                            command=lambda l=label, r=row: self.add_new_leh_field(l, r))
        add_button.grid(row=row, column=8, padx=2, pady=2)
        
        # 設置所有元件的 takefocus
        all_widgets = entries + [count_entry, type_entry, photo_entry, add_button]
        for widget in all_widgets:
            widget.configure(takefocus=1)
        
        # 設置方向鍵導航
        for widget in entries + [count_entry, type_entry, photo_entry]:
            for direction in ["Up", "Down", "Left", "Right"]:
                widget.bind(f"<{direction}>", 
                        lambda e, w=widget: self.handle_arrow_key(e, w))
        
        # 設置特定的 tab 順序
        def next_focus(event, next_widget):
            next_widget.focus_set()
            return "break"
        
        # 設置每個輸入框的 tab 順序
        photo_entry.bind('<Tab>', lambda e: next_focus(e, add_button))
        
        # 修改 add_button 的 tab 鍵綁定
        if label == "Buccal Peak c LEH Height" and suffix:  # 如果是 Bc 的額外行
            # 檢查是否是最後一個額外行
            bc_fields = [f for f in self.additional_leh_fields 
                        if f.startswith("Buccal Peak c LEH Height_")]
            if suffix == str(len(bc_fields)):  # 如果是最後一個額外行
                # 連接到 CEJ Visible
                cej_entry = self.entries.get("CEJ Visible")
                if cej_entry:
                    add_button.bind('<Tab>', lambda e: next_focus(e, cej_entry))
        elif suffix:  # 如果是其他字段的額外行
            # 找到原始標籤在 initial_leh_fields 中的位置
            if label in self.initial_leh_fields:
                idx = self.initial_leh_fields.index(label)
                if idx < len(self.initial_leh_fields) - 1:
                    # 如果不是最後一個類型，則連接到下一個類型的第一個輸入框
                    next_field = self.initial_leh_fields[idx + 1]
                    next_entry = self.entries.get(f"{next_field}1")
                    if next_entry:
                        add_button.bind('<Tab>', lambda e: next_focus(e, next_entry))
        else:  # 如果是初始行
            if row < len(self.initial_leh_fields):
                next_field = self.initial_leh_fields[self.initial_leh_fields.index(label) + 1]
                next_entry = self.entries.get(f"{next_field}1")
                if next_entry:
                    add_button.bind('<Tab>', lambda e: next_focus(e, next_entry))
        
        self.row_map[unique_label] = row

    def add_new_leh_field(self, label, row):
        """添加新的 LEH 欄位行"""
        # 找到相同類型的最後一行
        same_type_fields = [f for f in self.additional_leh_fields 
                        if f.startswith(label)]
        
        # 計算新的後綴
        suffix = str(len(same_type_fields) + 1)
        unique_label = f"{label}_{suffix}"
        
        # 先更新欄位列表
        self.additional_leh_fields.append(unique_label)
        self.all_leh_fields = self.initial_leh_fields + self.additional_leh_fields
        
        # 找到插入位置（在同類型字段的最後一行之後）
        insert_row = row
        for field in self.all_leh_fields:
            if field.startswith(label):
                field_row = self.row_map.get(field, 0)
                insert_row = max(insert_row, field_row)
        insert_row += 1
        
        # 更新後續行的位置
        affected_fields = []
        for field in self.all_leh_fields:
            if self.row_map.get(field, 0) >= insert_row:
                affected_fields.append(field)
        
        # 從下往上移動行，避免覆蓋
        for field in reversed(affected_fields):
            current_row = self.row_map[field]
            widgets = [w for w in self.leh_frame.grid_slaves() 
                    if w.grid_info()["row"] == current_row]
            widgets.sort(key=lambda w: w.grid_info()["column"])
            for widget in widgets:
                widget.grid(row=current_row + 1)
            self.row_map[field] = current_row + 1
        
        # 添加新欄位
        self.add_leh_field(label, insert_row, suffix)
        
        # 設置焦點到新行的第一個輸入框
        first_entry = self.entries.get(f"{unique_label}1")
        if first_entry:
            first_entry.focus_set()

    def create_other_section(self):
        """創建其他資訊區域"""
        other_frame = ttk.LabelFrame(self.inner_frame, text="Other Information", padding=10)
        other_frame.grid(row=2, column=0, sticky="ew", padx=10, pady=10)
        
        for i, field in enumerate(self.other_fields):
            tk.Label(other_frame, text=field, font=self.FONT_CONFIG).grid(
                row=i, column=0, padx=5, pady=2, sticky="ne")
                
            if field in ["Notes", "Pathology"]:
                # 多行文本框
                text_frame = tk.Frame(other_frame)
                text_frame.grid(row=i, column=1, padx=5, pady=2, sticky="w")
                
                text_widget = tk.Text(text_frame, width=40, height=5, font=self.FONT_CONFIG)
                text_widget.pack(side="left", fill="y")
                
                scrollbar = tk.Scrollbar(text_frame, orient="vertical", command=text_widget.yview)
                scrollbar.pack(side="right", fill="y")
                
                text_widget.configure(yscrollcommand=scrollbar.set)
                
                # 修改 Tab 鍵處理
                def next_widget(event, current_field=field):
                    next_field_index = self.other_fields.index(current_field) + 1
                    if next_field_index < len(self.other_fields):
                        next_field = self.other_fields[next_field_index]
                        self.entries[next_field].focus_set()
                    return "break"
                
                text_widget.bind("<Tab>", next_widget)
                self.entries[field] = text_widget
            else:
                # 單行輸入框
                entry = tk.Entry(other_frame, width=30, font=self.FONT_CONFIG)
                entry.grid(row=i, column=1, padx=5, pady=2, sticky="w")
                self.entries[field] = entry

    def setup_navigation(self, widgets):
        """設置tab順序和方向鍵導航"""
        for widget in widgets:
            widget.configure(takefocus=1)
            if isinstance(widget, tk.Entry):
                for direction in ["Up", "Down", "Left", "Right"]:
                    widget.bind(f"<{direction}>", 
                              lambda e, w=widget: self.handle_arrow_key(e, w))

    def setup_measurement_bindings(self, entry, field):
        """設置測量值輸入框的事件綁定"""
        entry.bind("<KeyRelease>", lambda e, f=field: self.calculate_avg(f))
        entry.bind("<KeyPress>", lambda e, f=field: self.calculate_avg(f))
        entry.bind("<Key>", lambda e, ent=entry, f=field: self.handle_decimal_input(e, ent, f))

    def create_buttons(self):
        """創建按鈕"""
        save_button = ttk.Button(self.button_frame, text="Save", command=self.save_and_clear)
        save_button.pack(side="left", padx=5)
        
        prev_button = ttk.Button(self.button_frame, text="Previous Record", 
                                command=self.show_previous_record)
        prev_button.pack(side="left", padx=5)
        
        next_button = ttk.Button(self.button_frame, text="Next Record", 
                                command=self.next_record)
        next_button.pack(side="left", padx=5)
        
        new_button = ttk.Button(self.button_frame, text="New Record", 
                            command=self.new_record)
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
        
        self.record_inner_frame.bind("<Configure>", 
                                   lambda e: self.record_canvas.configure(
                                       scrollregion=self.record_canvas.bbox("all")))
        
        self.inner_frame.bind("<Configure>", 
                            lambda e: self.canvas.configure(
                                scrollregion=self.canvas.bbox("all")))

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
        if event.char in [".", "。"]:
            current_pos = entry.index(tk.INSERT)
            entry.insert(current_pos, ".")
            self.calculate_avg(unique_label)
            return "break"
        elif event.keysym == "KP_Decimal":
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
        """儲存並清空輸入框"""
        self.root.focus_set()
        
        if self.current_file is None:
            current_date = datetime.now().strftime("%Y%m%d")
            script_dir = os.path.dirname(os.path.abspath(__file__))
            self.current_file = os.path.join(script_dir, f"LEHrec_{current_date}.csv")
        
        # 收集資料
        data = self.collect_data()
        if not data:
            return
        
        # 儲存資料
        if self.current_record_index >= 0:
            # 覆蓋現有紀錄
            self.save_data(data, True)
        else:
            # 儲存新紀錄
            self.save_data(data, False)
        
        # 保存部分基本資料
        saved_data = {
            "Sample ID": self.entries["Sample ID"].get(),
            "Context": self.entries["Context"].get(),
            "Sample Type": self.entries["Sample Type"].get(),
            "Sample Side": self.entries["Sample Side"].get()
        }
        
        # 清空輸入框
        self.clear_entries()
        
        # 恢復保存的基本資料
        for field, value in saved_data.items():
            self.entries[field].insert(0, value)
        
        # 重置額外的 LEH 欄位
        self.reset_leh_fields()

    def collect_data(self):
        """收集所有輸入資料"""
        # 收集基本資料
        base_data = {}
        for label in self.basic_fields:
            base_data[label] = self.entries[label].get() if self.entries[label].get() else "n/a"
        
        sample_id = base_data["Sample ID"]
        tooth_type = base_data["Tooth Type"]
        if not sample_id or not tooth_type:
            self.status_label.config(text="Sample ID and Tooth Type are required!")
            return None
        
        # 收集測量值
        measurement_data = {}
        for field in self.measurement_fields:
            short_field = self.get_short_label(field)
            for i in ["1", "2", "3"]:
                key = f"{field}{i}"
                measurement_data[f"{short_field}{i}"] = (
                    self.entries[key].get() if self.entries[key].get() else "n/a"
                )
        
        # 收集其他欄位
        other_data = {}
        for label in self.other_fields:
            if label in self.entries:
                if isinstance(self.entries[label], tk.Text):
                    other_data[label] = (
                        self.entries[label].get("1.0", tk.END).strip() or "n/a"
                    )
                else:
                    other_data[label] = self.entries[label].get() or "n/a"

        # 收集 LEH 資料
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
                    "Photo ID": self.entries[f"{field} Photo ID"].get() or "n/a"
                })
                
                values = [float(v) for v in [val1, val2, val3] if v and v != "n/a"]
                row_data["Avg"] = f"{sum(values) / len(values):.2f}" if values else "n/a"
                leh_rows.append(row_data)
        
        return {"base_data": base_data, "leh_rows": leh_rows}

    def save_data(self, data, is_update=False):
        """儲存資料到檔案和快取"""
        base_data = data["base_data"]
        leh_rows = data["leh_rows"]
        
        if is_update:
            record_num = self.records[self.current_record_index].split(".")[0]
            self.all_data = [row for row in self.all_data if row["Record Number"] != record_num]
            self.tree.delete(self.tree.get_children()[self.current_record_index])
            self.records.pop(self.current_record_index)
        else:
            record_num = str(len(self.records) + 1)
        
        # 準備要保存的數據
        record_data = []
        
        # 收集所有數據
        common_data = base_data.copy()
        
        # 收集測量資料
        measurement_data = {}
        for field in self.measurement_fields:
            short_field = self.get_short_label(field)
            for i in ["1", "2", "3"]:
                entry_key = f"{field}{i}"
                if entry_key in self.entries:
                    value = self.entries[entry_key].get()
                    measurement_data[f"{short_field}{i}"] = value if value else "n/a"
        common_data.update(measurement_data)
        
        # 收集其他資料
        other_data = {}
        for field in self.other_fields:
            if field in self.entries:
                if isinstance(self.entries[field], tk.Text):
                    value = self.entries[field].get("1.0", tk.END).strip()
                else:
                    value = self.entries[field].get()
                other_data[field] = value if value else "n/a"
        common_data.update(other_data)
        
        # 如果沒有 LEH 資料，至少保存一行基本資料
        if not leh_rows:
            row_data = {
                "Record Number": record_num,
                "LEH Side": "",
                "Value 1": "n/a",
                "Value 2": "n/a",
                "Value 3": "n/a",
                "Avg": "n/a",
                "LEH Count": "n/a",
                "LEH Type": "n/a",
                "Photo ID": "n/a"
            }
            row_data.update(common_data)
            record_data.append(row_data)
            self.all_data.append(row_data)
        else:
            for row in leh_rows:
                row_data = row.copy()
                row_data["Record Number"] = record_num
                row_data.update(common_data)
                record_data.append(row_data)
                self.all_data.append(row_data)

        # 保存到快取並輸出調試信息
        print(f"準備快取的數據: {record_data}")  # 調試信息
        self.save_to_cache(record_num, record_data)
        
        # 更新 tree
        record_name = f"{record_num}. {base_data['Sample ID']} - {base_data['Tooth Type']}"
        if is_update:
            self.tree.insert("", self.current_record_index, values=(record_name,))
            self.records.insert(self.current_record_index, record_name)
        else:
            self.tree.insert("", "end", values=(record_name,))
            self.records.append(record_name)
        
        # 儲存到檔案
        self.save_to_file()
        self.status_label.config(text=f"[{record_name}] {'Updated' if is_update else 'Saved'}")
        
        if not is_update:
            self.current_record_index = -1

    def save_to_file(self):
        """將資料寫入CSV檔案"""
        try:
            # 重新排序欄位
            fieldnames = (self.basic_fields +  # 基本資料
                        [self.get_short_label(field) + i 
                        for field in self.measurement_fields 
                        for i in ["1", "2", "3"]] +  # 測量資料
                        ["LEH Side", "Value 1", "Value 2", "Value 3", 
                        "Avg", "LEH Count", "LEH Type", "Photo ID"] +  # LEH資料
                        ["CEJ Visible"] +  # CEJ Visible 移到 LEH 資料後
                        [field for field in self.other_fields if field != "CEJ Visible"])  # 其他欄位
            
            # 添加 Record Number 到開頭
            fieldnames = ["Record Number"] + fieldnames
            
            # 處理資料，簡化 LEH Side 標籤
            processed_data = []
            for row in self.all_data:
                new_row = row.copy()
                if "_" in row.get("LEH Side", ""):
                    leh_side = row["LEH Side"]
                    original_label = leh_side.split("_")[0]
                    short_label = self.get_short_label(original_label)
                    new_row["LEH Side"] = short_label
                processed_data.append(new_row)
            
            with open(self.current_file, "w", newline="", encoding="utf-8") as file:
                writer = csv.DictWriter(file, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(processed_data)
                
        except PermissionError:
            # 如果原始位置無法寫入，嘗試保存到使用者的文件夾
            user_documents = os.path.expanduser("~/Documents")
            filename = os.path.basename(self.current_file)
            new_path = os.path.join(user_documents, filename)
            
            try:
                with open(new_path, "w", newline="", encoding="utf-8") as file:
                    writer = csv.DictWriter(file, fieldnames=fieldnames)
                    writer.writeheader()
                    writer.writerows(processed_data)
                
                self.current_file = new_path
                self.status_label.config(text=f"File saved to Documents folder: {filename}")
                
            except Exception as e:
                self.status_label.config(text=f"Error saving file: {str(e)}")
                return False
                
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
        
        # 重置平均值標籤
        for avg_label in self.averages.values():
            avg_label.config(text="N/A")

    def reset_leh_fields(self):
        """重置額外的 LEH 欄位"""
        # 移除額外的 LEH 欄位
        for field in self.additional_leh_fields:
            for widget in self.leh_frame.grid_slaves():
                if widget.grid_info()["row"] == self.row_map[field]:
                    widget.destroy()
        
        # 重置變數
        self.additional_leh_fields = []
        self.all_leh_fields = self.initial_leh_fields.copy()
        
        # 重新排列剩餘的欄位
        for i, field in enumerate(self.initial_leh_fields, 1):
            self.row_map[field] = i

    def open_file(self):
        """開啟檔案"""
        file_path = filedialog.askopenfilename(
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")])
        if not file_path:
            return
        
        try:
            with open(file_path, "r", encoding="utf-8") as file:
                reader = csv.DictReader(file)
                self.all_data = list(reader)
            
            self.current_file = file_path
            self.records = []
            self.tree.delete(*self.tree.get_children())
            
            # 按記錄編號分組
            records_by_num = {}
            for row in self.all_data:
                record_num = row["Record Number"]
                if record_num not in records_by_num:
                    records_by_num[record_num] = row
            
            # 添加到樹狀圖
            for record_num, row in records_by_num.items():
                record_name = f"{record_num}. {row['Sample ID']} - {row['Tooth Type']}"
                self.tree.insert("", "end", values=(record_name,))
                self.records.append(record_name)
            
            self.status_label.config(text=f"Loaded file: {os.path.basename(file_path)}")
            
        except Exception as e:
            self.status_label.config(text=f"Error loading file: {str(e)}")

    def save_as(self):
        """另存新檔"""
        file_path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")])
        
        if file_path:
            self.current_file = file_path
            self.save_and_clear()

    def show_record(self, event=None):
        """顯示選定的記錄"""
        selection = self.tree.selection()
        if not selection:
            return
        
        item = selection[0]
        index = self.tree.index(item)
        self.current_record_index = index
        
        # 清空當前輸入
        self.clear_entries()
        self.reset_leh_fields()
        
        # 獲取記錄編號
        record_num = self.records[index].split(".")[0]
        print(f"正在讀取記錄編號: {record_num}")  # 調試信息
        
        # 從 all_data 中獲取數據
        record_data = [row for row in self.all_data if row["Record Number"] == record_num]
        print(f"找到的記錄數據: {record_data}")  # 調試信息
        
        if not record_data:
            print("未找到記錄數據")  # 調試信息
            return
        
        first_row = record_data[0]
        print(f"第一行數據: {first_row}")  # 調試信息
        
        try:
            # 填充基本資料
            print("開始填充基本資料")  # 調試信息
            for field in self.basic_fields:
                if field in first_row and first_row[field] != "n/a":
                    print(f"填充 {field}: {first_row[field]}")  # 調試信息
                    self.entries[field].insert(0, first_row[field])
            
            # 填充測量資料
            print("開始填充測量資料")  # 調試信息
            for field in self.measurement_fields:
                short_field = self.get_short_label(field)
                print(f"處理測量欄位: {field} (簡短標籤: {short_field})")  # 調試信息
                for i in ["1", "2", "3"]:
                    key = f"{short_field}{i}"
                    if key in first_row and first_row[key] != "n/a":
                        entry_key = f"{field}{i}"
                        print(f"填充 {entry_key}: {first_row[key]}")  # 調試信息
                        if entry_key in self.entries:
                            self.entries[entry_key].insert(0, first_row[key])
                self.calculate_avg(field)
            
            # 填充其他資料
            print("開始填充其他資料")  # 調試信息
            for field in self.other_fields:
                if field in first_row and first_row[field] != "n/a":
                    print(f"填充 {field}: {first_row[field]}")  # 調試信息
                    if field in self.entries:
                        if isinstance(self.entries[field], tk.Text):
                            self.entries[field].delete("1.0", tk.END)
                            self.entries[field].insert("1.0", first_row[field])
                        else:
                            self.entries[field].insert(0, first_row[field])
            
            # 填充 LEH 資料
            print("開始填充 LEH 資料")  # 調試信息
            for row in record_data:
                leh_side = row.get("LEH Side", "")
                print(f"處理 LEH 行: {leh_side}")  # 調試信息
                if not leh_side or leh_side == "n/a":
                    continue
                
                # 找到對應的完整標籤
                full_label = None
                for field in self.initial_leh_fields:
                    if self.get_short_label(field) == leh_side:
                        full_label = field
                        break
                
                print(f"找到完整標籤: {full_label}")  # 調試信息
                if not full_label:
                    continue
                
                # 填充 LEH 數據
                for i in ["1", "2", "3"]:
                    value_key = f"Value {i}"
                    if value_key in row and row[value_key] != "n/a":
                        entry_key = f"{full_label}{i}"
                        print(f"填充 {entry_key}: {row[value_key]}")  # 調試信息
                        if entry_key in self.entries:
                            self.entries[entry_key].insert(0, row[value_key])
                
                # 填充其他 LEH 相關欄位
                for field_type in ["LEH Count", "LEH Type", "Photo ID"]:
                    if field_type in row and row[field_type] != "n/a":
                        entry_key = f"{full_label} {field_type}"
                        print(f"填充 {entry_key}: {row[field_type]}")  # 調試信息
                        if entry_key in self.entries:
                            self.entries[entry_key].insert(0, row[field_type])
                
                self.calculate_avg(full_label)
            
        except Exception as e:
            print(f"顯示記錄時發生錯誤: {str(e)}")  # 調試信息
            import traceback
            traceback.print_exc()
        
        print("記錄顯示完成")  # 調試信息

    def show_previous_record(self):
        """顯示上一筆記錄"""
        if self.current_record_index > 0:
            self.current_record_index -= 1
            self.tree.selection_set(self.tree.get_children()[self.current_record_index])
            self.show_record()

    def next_record(self):
        """顯示下一筆記錄"""
        if self.current_record_index < len(self.records) - 1:
            self.current_record_index += 1
            self.tree.selection_set(self.tree.get_children()[self.current_record_index])
            self.show_record()

    def new_record(self):
        """開始新記錄"""
        self.current_record_index = -1
        self.clear_entries()
        self.reset_leh_fields()
        self.status_label.config(text="Started new record")

if __name__ == "__main__":
    app = LEHRecordProgram()
    app.root.mainloop()
