# ============================================================
# LEH Record Program  —  Optimised Version
# Fixes applied:
#   #1  Duplicate except block removed
#   #2  Hardcoded path removed
#   #3  All imports moved to top of file
#   #4  widget_to_key reverse-lookup dict (O(1) arrow-key nav)
#   #5  setup_measurement_bindings – each event bound only once
#   #6  index.json update replaces existing entry (no duplicates)
#   #7  render_leh_fields cleans widget_to_key on rebuild
#   #8  add_new_photo_id_field always appends (no row-shifting)
#   #9  collect_data uses leh_field_order directly (no recompute)
#  #10  show_record split into focused helper methods
#  #11  all_data removed; self.records is the single source of truth
#  #12  print replaced with logging (set level=INFO to silence debug)
#  #13  cache cleanup only on clean exit; crash-recovery cache survives
# ============================================================

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import csv
import os
import json
import re
import platform
from datetime import datetime
import pickle
import tempfile
import atexit
import logging

# Change level to logging.INFO to suppress debug messages in production
logging.basicConfig(level=logging.DEBUG, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


class LEHRecordProgram:
    def __init__(self):
        self.setup_constants()
        self.setup_variables()
        self.setup_cache()
        self.create_main_window()

        self.setup_file_location()      # Fix #2: hardcoded path removed
        self.setup_context_fields()
        self.create_frames()
        self.create_sections()
        self.create_buttons()
        self.setup_bindings()
        self.setup_menu()
        atexit.register(self.cleanup_cache)   # Fix #13: only clean on normal exit

    # ── Constants ───────────────────────────────────────────────────────────

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
        self.basic_fields        = self.LABELS[:9]
        self.measurement_fields  = self.LABELS[9:19]
        self.initial_leh_fields  = self.LABELS[19:25]
        self.leh_count_type      = self.LABELS[25:27]
        self.other_fields        = self.LABELS[27:]
        self.fixed_photo_types   = ["Buccal", "Lingual", "Occlusal"]

        # Tooth Type 選項（由 wear_class_table 整理，乳齒 + 恆齒）
        self.TOOTH_TYPES = [
            "M1", "M2", "M3", "P1", "P2", "P3", "P4", 
            "I1", "I2", "I3", "C", "dp2", "dp3", "dp4",
            "di1", "di2", "di3", "dc"            
        ]
        self.JAW_TYPES = ["U", "L", "un"]
        self.AGE_GROUPS = ["A", "B", "C", "D", "E", "F", "G"]
        self.WEAR_LEVELS = self.AGE_GROUPS

        # 完整年齡分期表（乳齒與恆齒，區分上顎/下顎）
        self.WEAR_CLASS_TABLE = {
            ("di1", "U"): {"A": list(range(0, 7)), "B": list(range(8, 9))},
            ("di1", "L"): {"A": list(range(0, 7)), "B": list(range(8, 10))},
            ("di2", "U"): {"A": list(range(0, 7)), "B": list(range(7, 10)), "C": list(range(8, 10))},
            ("di2", "L"): {"A": list(range(0, 7)), "B": list(range(8, 9)), "C": list(range(8, 10)), "D": list(range(9, 10))},
            ("di3", "U"): {"A": list(range(0, 7)), "B": list(range(8, 10))},
            ("di3", "L"): {"A": list(range(0, 7)), "B": list(range(8, 10)), "C": list(range(9, 10))},
            ("dc", "U"): {"A": list(range(0, 7)), "B": list(range(8, 10))},
            ("dc", "L"): {"A": list(range(0, 7)), "B": list(range(8, 10))},
            ("dp2", "U"): {"A": list(range(0, 6)), "B": list(range(7, 14)), "C": list(range(8, 14))},
            ("dp2", "L"): {"A": list(range(0, 6)), "B": list(range(7, 14)), "C": list(range(10, 14))},
            ("dp3", "U"): {"A": list(range(0, 7)), "B": list(range(7, 14)), "C": list(range(10, 14))},
            ("dp3", "L"): {"A": list(range(0, 6)), "B": list(range(7, 12)), "C": list(range(10, 14))},
            ("dp4", "U"): {"A": list(range(0, 7)), "B": list(range(8, 11)), "C": list(range(11, 18))},
            ("dp4", "L"): {"A": list(range(0, 7)), "B": list(range(8, 11)), "C": list(range(11, 18)), "D": list(range(15, 18))},
            ("I1", "U"): {"A": [0], "B": list(range(0, 6)), "C": list(range(4, 6)), "D": list(range(5, 8)), "E": list(range(5, 8)), "F": list(range(8, 10)), "G": list(range(9, 10))},
            ("I1", "L"): {"A": [0], "B": list(range(0, 4)), "C": list(range(2, 5)), "D": list(range(5, 8)), "E": list(range(8, 9)), "F": list(range(8, 10)), "G": list(range(9, 10))},
            ("I2", "U"): {"A": [0], "B": list(range(0, 6)), "C": list(range(4, 6)), "D": list(range(4, 8)), "E": list(range(6, 9)), "F": list(range(8, 10)), "G": list(range(9, 10))},
            ("I2", "L"): {"A": [0], "B": list(range(0, 4)), "C": list(range(4, 6)), "D": list(range(7, 8)), "E": list(range(7, 9)), "F": list(range(8, 10)), "G": list(range(9, 10))},
            ("I3", "U"): {"A": [0], "B": list(range(0, 7)), "C": list(range(4, 7)), "D": list(range(7, 8)), "E": list(range(7, 10)), "F": list(range(8, 10)), "G": list(range(8, 10))},
            ("I3", "L"): {"A": [0], "B": list(range(0, 6)), "C": list(range(4, 7)), "D": list(range(7, 8)), "E": list(range(7, 9)), "F": list(range(7, 10)), "G": list(range(8, 9))},
            ("C", "U"): {"A": [0], "B": list(range(0, 5)), "C": list(range(4, 7)), "D": list(range(7, 8)), "E": list(range(7, 9)), "F": list(range(8, 10)), "G": [9]},
            ("C", "L"): {"A": [0], "B": list(range(0, 5)), "C": list(range(4, 7)), "D": list(range(7, 8)), "E": list(range(7, 9)), "F": list(range(8, 10)), "G": [9]},
            ("P1", "U"): {"A": list(range(0, 3)), "B": list(range(4, 7)), "C": list(range(5, 10)), "D": list(range(6, 10)), "E": list(range(6, 13)), "F": list(range(7, 14)), "G": list(range(9, 14))},
            ("P1", "L"): {"A": list(range(0, 4)), "B": list(range(0, 7)), "C": list(range(6, 8)), "D": list(range(7, 8)), "E": list(range(7, 9)), "F": list(range(7, 14)), "G": list(range(8, 14))},
            ("P2", "U"): {"A": [0], "B": [0], "C": list(range(0, 7)), "D": list(range(7, 9)), "E": list(range(7, 10)), "F": list(range(8, 14)), "G": list(range(11, 14))},
            ("P2", "L"): {"A": [0], "B": [0], "C": list(range(0, 7)), "D": list(range(7, 8)), "E": list(range(7, 10)), "F": list(range(8, 14)), "G": list(range(8, 14))},
            ("P3", "U"): {"A": [0], "B": [0], "C": list(range(0, 7)), "D": list(range(7, 10)), "E": list(range(7, 11)), "F": list(range(10, 14)), "G": list(range(12, 14))},
            ("P3", "L"): {"A": [0], "B": [0], "C": list(range(0, 7)), "D": list(range(7, 10)), "E": list(range(7, 11)), "F": list(range(9, 13)), "G": list(range(11, 14))},
            ("P4", "U"): {"A": [0], "B": list(range(0, 3)), "C": list(range(0, 7)), "D": list(range(8, 10)), "E": list(range(8, 12)), "F": list(range(10, 14)), "G": list(range(13, 14))},
            ("P4", "L"): {"A": [0], "B": list(range(0, 3)), "C": list(range(0, 7)), "D": list(range(8, 10)), "E": list(range(8, 12)), "F": list(range(9, 14)), "G": list(range(13, 14))},
            ("M1", "U"): {"A": list(range(0, 2)), "B": list(range(3, 9)), "C": list(range(9, 11)), "D": list(range(9, 12)), "E": list(range(10, 14)), "F": list(range(14, 19)), "G": list(range(18, 19))},
            ("M1", "L"): {"A": list(range(0, 2)), "B": list(range(3, 9)), "C": list(range(9, 11)), "D": list(range(9, 12)), "E": list(range(10, 14)), "F": list(range(14, 19)), "G": list(range(18, 19))},
            ("M2", "U"): {"A": [0], "B": list(range(0, 3)), "C": list(range(4, 7)), "D": list(range(7, 9)), "E": list(range(8, 11)), "F": list(range(10, 16)), "G": list(range(16, 19))},
            ("M2", "L"): {"A": [0], "B": list(range(0, 3)), "C": list(range(4, 7)), "D": list(range(7, 9)), "E": list(range(8, 11)), "F": list(range(10, 16)), "G": list(range(16, 19))},
            ("M3", "U"): {"A": [0], "B": list(range(0, 2)), "C": list(range(0, 3)), "D": list(range(2, 4)), "E": list(range(4, 9)), "F": list(range(7, 12)), "G": list(range(12, 19))},
            ("M3", "L"): {"A": [0], "B": list(range(0, 2)), "C": list(range(0, 3)), "D": list(range(2, 5)), "E": list(range(4, 9)), "F": list(range(7, 12)), "G": list(range(12, 19))},
        }
        self._wear_class_lookup = {
            (tooth.lower(), jaw): wear_map
            for (tooth, jaw), wear_map in self.WEAR_CLASS_TABLE.items()
        }

    # ── Variables ───────────────────────────────────────────────────────────

    def setup_variables(self):
        self.entries               = {}
        self.widget_to_key         = {}   # Fix #4: reverse-lookup widget → key
        self.averages              = {}
        self.records               = []   # Fix #11: single source of truth
        self.current_file          = None
        self.data_dir              = None
        self.additional_leh_fields = []
        self.additional_photo_fields = []
        self.all_photo_fields      = self.fixed_photo_types.copy()
        self.row_map               = {}
        self.photo_row_map         = {}
        self.current_record_index  = -1
        self.all_leh_fields        = self.initial_leh_fields.copy()
        self.leh_field_order       = self.initial_leh_fields.copy()
        self.context_fields        = []
        self.record_number         = 1
        self.sample_number         = 1
        self.record_order          = []

    def _set_entry(self, key, widget):
        """Register a widget in entries dict and in reverse-lookup (Fix #4)."""
        self.entries[key] = widget
        if isinstance(widget, tk.Entry):
            self.widget_to_key[widget] = key

    def _del_entry(self, key):
        """Remove a widget from entries dict and reverse-lookup."""
        widget = self.entries.pop(key, None)
        if widget is not None:
            self.widget_to_key.pop(widget, None)

    # ── Cache ────────────────────────────────────────────────────────────────

    def setup_cache(self):
        self.cache_file   = os.path.join(tempfile.gettempdir(), "leh_record_cache.pkl")
        self.record_cache = {}
        if os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, "rb") as f:
                    self.record_cache = pickle.load(f)
                logger.debug("Cache loaded from previous session.")
            except Exception:
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
            with open(self.cache_file, "wb") as f:
                pickle.dump(self.record_cache, f)
            logger.debug(f"Cached record {record_num}")
        except Exception as e:
            logger.error(f"Failed to save cache: {e}")

    def cleanup_cache(self):
        """Remove cache on clean exit. Crash-recovery cache survives abnormal exit (Fix #13)."""
        try:
            if os.path.exists(self.cache_file):
                os.remove(self.cache_file)
        except Exception:
            pass

    # ── Window / Frame setup ─────────────────────────────────────────────────

    def create_main_window(self):
        self.root = tk.Tk()
        self.root.title("LEH Record Program")
        self.root.geometry("1400x800")
        self.root.resizable(True, True)

    def setup_file_location(self):
        # Fix #2: no hardcoded self.data_dir override
        file_window = tk.Toplevel(self.root)
        file_window.title("Setup File Location")
        file_window.geometry("400x200")
        file_window.transient(self.root)
        file_window.grab_set()

        tk.Label(file_window, text="Choose an option:").pack(pady=10)

        def new_folder():
            self.data_dir = filedialog.askdirectory(title="Select Directory to Save Data")
            if self.data_dir:
                self.current_file = os.path.join(
                    self.data_dir, f"LEHrec_{datetime.now().strftime('%Y%m%d')}.csv"
                )
                file_window.destroy()

        def open_file():
            file_path = filedialog.askopenfilename(
                filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
            )
            if file_path:
                self.current_file = file_path
                self.data_dir     = os.path.dirname(file_path)
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
            context_window.geometry("450x150")
            context_window.transient(self.root)
            context_window.grab_set()

            tk.Label(
                context_window,
                text="Enter Context subfields (comma-separated, e.g., Site, Layer):"
            ).pack(pady=10)
            entry = tk.Entry(context_window, width=40, font=self.FONT_CONFIG)
            entry.pack(pady=5)
            entry.focus_set()

            def save_context_fields():
                fields = entry.get().strip()
                if fields:
                    self.context_fields = [f.strip() for f in fields.split(",") if f.strip()]
                    self.basic_fields   = self.LABELS[:1] + self.context_fields + self.LABELS[2:9]
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

        self.tree = ttk.Treeview(
            self.record_inner_frame,
            columns=("Record Number", "Sample ID", "Tooth Type", "Snapshot File"),
            show="headings",
            height=20
        )
        for col, w in [("Record Number", 80), ("Sample ID", 100), ("Tooth Type", 100), ("Snapshot File", 200)]:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=w, anchor="w")
        self.tree["displaycolumns"] = ("Record Number", "Sample ID", "Tooth Type")
        self.tree.pack(fill="y", expand=True)
        self.tree.bind("<Double-1>", self.show_record)

        # Load index to rebuild Treeview (Fix #3: import moved to top)
        try:
            snapshot_dir = os.path.join(self.data_dir if self.data_dir else ".", "snapshots")
            index_path   = os.path.join(snapshot_dir, "index.json")
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
            logger.debug(f"Loaded index: {index_path}")
        except Exception as e:
            logger.error(f"Failed to load index: {e}")

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

    # ── Section creation ─────────────────────────────────────────────────────

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
        self.pause_age_auto_var = tk.BooleanVar(value=False)
        for i, field in enumerate(self.basic_fields):
            tk.Label(basic_frame, text=field, font=self.FONT_CONFIG).grid(row=i, column=0, padx=5, pady=2, sticky="e")
            if field == "Tooth Type":
                widget = ttk.Combobox(
                    basic_frame,
                    values=self.TOOTH_TYPES,
                    width=28,
                    font=self.FONT_CONFIG
                )
                widget.bind("<<ComboboxSelected>>", self.estimate_age_group)
                widget.bind("<KeyRelease>", self.estimate_age_group)
                widget.bind("<FocusOut>", self.estimate_age_group)
            elif field == "Jaw Type":
                widget = ttk.Combobox(
                    basic_frame,
                    values=self.JAW_TYPES,
                    width=28,
                    font=self.FONT_CONFIG,
                    state="readonly"
                )
                widget.bind("<<ComboboxSelected>>", self.estimate_age_group)
                widget.bind("<FocusOut>", self.estimate_age_group)
            else:
                widget = tk.Entry(basic_frame, width=30, font=self.FONT_CONFIG)
                if field in ("Sample ID", "Wear Level"):
                    widget.bind("<KeyRelease>", self.estimate_age_group)
                    widget.bind("<FocusOut>", self.estimate_age_group)
            widget.grid(row=i, column=1, padx=5, pady=2)
            self._set_entry(field, widget)
            if field == "Age Group":
                pause_cb = ttk.Checkbutton(
                    basic_frame,
                    text="Pause Auto",
                    variable=self.pause_age_auto_var,
                    command=self._on_toggle_pause_age_auto
                )
                pause_cb.grid(row=i, column=2, padx=5, pady=2, sticky="w")

    def _on_toggle_pause_age_auto(self):
        """切換暫停自動更新 Age Group 的選取格。"""
        if self.pause_age_auto_var.get():
            if hasattr(self, "status_label"):
                self.status_label.config(text="Age Group auto-update paused")
        else:
            self.estimate_age_group()

    @staticmethod
    def _normalize_jaw(jaw_raw):
        """標準化 Jaw Type（支援 U/L、Upper/Lower、Maxilla/Mandible、上/下）。"""
        jaw_upper = jaw_raw.strip().upper()
        if jaw_upper in ("U", "UPPER", "MAXILLA", "MAX", "上", "上顎"):
            return "U"
        if jaw_upper in ("L", "LOWER", "MANDIBLE", "MAND", "下", "下顎"):
            return "L"
        return jaw_upper

    def _lookup_ages(self, tooth, jaw_raw, wear_raw):
        """查詢單顆牙齒在 WEAR_CLASS_TABLE 中對應的 Age Group 集合（A-G）。
        WEAR_CLASS_TABLE 的 key 為 Age Group (A-G)，value 為 Wear Level 數字範圍。
        """
        tooth_clean = (tooth or "").strip()
        jaw = self._normalize_jaw(jaw_raw or "")
        wear_str = (wear_raw or "").strip()
        if not (tooth_clean and jaw and wear_str):
            return None
        try:
            wear_num = int(wear_str)
        except ValueError:
            return None

        lookup = getattr(self, "_wear_class_lookup", None)
        if lookup is not None:
            wear_map = lookup.get((tooth_clean.lower(), jaw), {})
        else:
            wear_map = self.WEAR_CLASS_TABLE.get((tooth_clean, jaw), {})

        matched = {
            age_grp for age_grp, wear_nums in wear_map.items()
            if wear_num in wear_nums
        }
        return matched if matched else None

    def _format_age_range(self, ages):
        """將 Age Group 集合依 A-G 順序格式化（連續區間顯示如 D-E，單一顯示如 D）。"""
        order = getattr(self, "AGE_GROUPS", ["A", "B", "C", "D", "E", "F", "G"])
        sorted_groups = [g for g in order if g in ages]
        if not sorted_groups:
            return ""
        if len(sorted_groups) == 1:
            return sorted_groups[0]
        indices = [order.index(g) for g in sorted_groups]
        if indices == list(range(indices[0], indices[-1] + 1)):
            return f"{sorted_groups[0]}-{sorted_groups[-1]}"
        return ", ".join(sorted_groups)

    def _compute_sample_age_group(self, sample_id, tooth, jaw_raw, wear_raw, exclude_index=-1):
        """計算當下牙齒與同 Sample ID 已存紀錄的年齡交集。
        回傳 (age_text, has_conflict, status_text)；若當下牙齒資料不完整則回傳 (None, False, None)。
        """
        current_ages = self._lookup_ages(tooth, jaw_raw, wear_raw)
        if not current_ages:
            return None, False, None

        tooth_clean = tooth.strip()
        jaw_clean = self._normalize_jaw(jaw_raw)
        wear_clean = wear_raw.strip().upper()

        matched_teeth = []
        combined_ages = set(current_ages)

        if sample_id:
            for idx, rec in enumerate(self.records):
                if idx == exclude_index:
                    continue
                basic = rec.get("basic_info") if isinstance(rec.get("basic_info"), dict) else rec
                if (basic.get("Sample ID") or "").strip() != sample_id:
                    continue
                rec_tooth = (basic.get("Tooth Type") or "").strip()
                rec_ages = self._lookup_ages(
                    rec_tooth,
                    basic.get("Jaw Type", ""),
                    basic.get("Wear Level", "")
                )
                if rec_ages:
                    matched_teeth.append(rec_tooth)
                    combined_ages &= rec_ages

        if combined_ages:
            age_text = self._format_age_range(combined_ages)
            if matched_teeth:
                teeth_str = ", ".join(matched_teeth + [tooth_clean])
                status = f"Estimated Age Group: {age_text} (Sample {sample_id}: {teeth_str})"
            else:
                status = f"Estimated Age Group: {age_text} ({tooth_clean}, {jaw_clean}, {wear_clean})"
            return age_text, False, status

        # 交集為空：維持當下牙齒區間並在狀態列提示衝突
        age_text = self._format_age_range(current_ages)
        status = (
            f"Age Group 衝突！維持當下牙齒區間 {age_text} ({tooth_clean})，"
            f"與同 Sample ID ({sample_id}) 先前紀錄無交集"
        )
        return age_text, True, status

    def _sync_sample_age_group(self, sample_id, age_text):
        """將更新後的 Age Group 同步寫回同 Sample ID 的已存紀錄與 snapshot 檔案。"""
        if not sample_id or not age_text:
            return
        snapshot_dir = os.path.join(self.data_dir or ".", "snapshots")
        for rec in self.records:
            basic = rec.get("basic_info") if isinstance(rec.get("basic_info"), dict) else rec
            if (basic.get("Sample ID") or "").strip() != sample_id:
                continue
            if basic.get("Age Group") == age_text:
                continue
            basic["Age Group"] = age_text
            uuid_str = rec.get("uuid")
            if uuid_str:
                snapshot_path = os.path.join(snapshot_dir, f"{uuid_str}.json")
                if os.path.exists(snapshot_path):
                    try:
                        with open(snapshot_path, "r", encoding="utf-8") as f:
                            snap = json.load(f)
                        if isinstance(snap.get("basic_info"), dict):
                            snap["basic_info"]["Age Group"] = age_text
                        with open(snapshot_path, "w", encoding="utf-8") as f:
                            json.dump(snap, f, ensure_ascii=False, indent=2)
                    except Exception as e:
                        logger.error(f"Failed to sync Age Group to snapshot {snapshot_path}: {e}")

    def estimate_age_group(self, event=None):
        """根據當下牙齒與同 Sample ID 已存牙齒紀錄的交集自動推算 Age Group。"""
        if getattr(self, "pause_age_auto_var", None) and self.pause_age_auto_var.get():
            return
        tooth_widget  = self.entries.get("Tooth Type")
        jaw_widget    = self.entries.get("Jaw Type")
        wear_widget   = self.entries.get("Wear Level")
        age_widget    = self.entries.get("Age Group")
        sample_widget = self.entries.get("Sample ID")
        if not all([tooth_widget, jaw_widget, wear_widget, age_widget]):
            return

        tooth_val = tooth_widget.get()
        jaw_val   = jaw_widget.get()
        wear_val  = wear_widget.get()
        sample_id = sample_widget.get().strip() if sample_widget else ""
        age_text, _, status = self._compute_sample_age_group(
            sample_id=sample_id,
            tooth=tooth_val,
            jaw_raw=jaw_val,
            wear_raw=wear_val,
            exclude_index=self.current_record_index
        )
        if not age_text:
            if tooth_val.strip() and jaw_val.strip() and wear_val.strip() and hasattr(self, "status_label"):
                self.status_label.config(
                    text=f"No Age Group match for ({tooth_val.strip()}, {jaw_val.strip()}, {wear_val.strip()})"
                )
            return

        age_widget.delete(0, tk.END)
        age_widget.insert(0, age_text)
        if hasattr(self, "status_label") and status:
            self.status_label.config(text=status)

    def create_measurement_section(self):
        measurement_frame = ttk.LabelFrame(self.top_frame, text="Measurements", padding=10)
        measurement_frame.pack(side="left", fill="y", padx=10, pady=10)
        for i, field in enumerate(self.measurement_fields):
            short_label = self.get_short_label(field)
            tk.Label(measurement_frame, text=short_label, font=self.FONT_CONFIG).grid(row=i, column=0, padx=5, pady=2, sticky="e")
            for j in range(3):
                entry = tk.Entry(measurement_frame, width=8, font=self.FONT_CONFIG)
                entry.grid(row=i, column=j + 1, padx=2, pady=2)
                self._set_entry(f"{field}{j + 1}", entry)
                self.setup_measurement_bindings(entry, field)
            avg_label = tk.Label(measurement_frame, text="N/A", font=self.FONT_CONFIG)
            avg_label.grid(row=i, column=4, padx=5, pady=2)
            self.averages[field] = avg_label

    def create_leh_section(self):
        self.leh_frame = ttk.LabelFrame(self.inner_frame, text="LEH Records", padding=10)
        self.leh_frame.grid(row=1, column=0, sticky="ew", padx=10, pady=10)
        headers = ["LEH Count", "LEH Type", "CEJ Visible", "Photo ID"]
        for i, header in enumerate(headers):
            tk.Label(self.leh_frame, text=header, font=self.FONT_CONFIG).grid(row=0, column=i + 5, padx=5, pady=2, sticky="w")
        self.render_leh_fields()

    def render_leh_fields(self):
        """Destroy and recreate all LEH rows, preserving current values (Fix #7: also cleans widget_to_key)."""
        # Save current values
        saved_values = {}
        for field in self.leh_field_order:
            for suffix in ["1", "2", "3", " LEH Count", " LEH Type", " CEJ Visible", " Photo ID"]:
                key = f"{field}{suffix}"
                if key in self.entries and self.entries[key].winfo_exists():
                    saved_values[key] = self.entries[key].get()
            if field in self.averages and self.averages[field].winfo_exists():
                saved_values[f"{field}_avg"] = self.averages[field].cget("text")

        # Destroy non-header widgets
        for widget in self.leh_frame.grid_slaves():
            if int(widget.grid_info()["row"]) > 0:
                widget.grid_forget()

        # Clean up entries + reverse-lookup (Fix #7)
        for field in self.leh_field_order:
            for suffix in ["1", "2", "3", " LEH Count", " LEH Type", " CEJ Visible", " Photo ID"]:
                self._del_entry(f"{field}{suffix}")
            self.averages.pop(field, None)
        self.row_map.clear()

        # Recreate rows
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

        sub_entries = []
        for i in range(3):
            entry = tk.Entry(self.leh_frame, width=8, font=self.FONT_CONFIG)
            entry.grid(row=row, column=i + 1, padx=2, pady=2)
            self._set_entry(f"{unique_label}{i + 1}", entry)
            sub_entries.append(entry)
            self.setup_measurement_bindings(entry, unique_label)

        avg_label = tk.Label(self.leh_frame, text="N/A", font=self.FONT_CONFIG)
        avg_label.grid(row=row, column=4, padx=5, pady=2)
        self.averages[unique_label] = avg_label

        count_entry = tk.Entry(self.leh_frame, width=10, font=self.FONT_CONFIG)
        type_entry  = tk.Entry(self.leh_frame, width=10, font=self.FONT_CONFIG)
        cej_entry   = tk.Entry(self.leh_frame, width=10, font=self.FONT_CONFIG)
        photo_entry = tk.Entry(self.leh_frame, width=15, font=self.FONT_CONFIG)
        for col, (label_suffix, widget) in enumerate(
            [(" LEH Count", count_entry), (" LEH Type", type_entry),
             (" CEJ Visible", cej_entry), (" Photo ID", photo_entry)], start=5
        ):
            widget.grid(row=row, column=col, padx=2, pady=2)
            self._set_entry(f"{unique_label}{label_suffix}", widget)

        base_label = unique_label.split("_")[0] if "_" in unique_label else unique_label
        add_button = ttk.Button(
            self.leh_frame, text="+", width=2,
            command=lambda l=base_label: self.add_new_leh_field(l)
        )
        add_button.grid(row=row, column=9, padx=2, pady=2)
        self.setup_navigation(sub_entries + [count_entry, type_entry, cej_entry, photo_entry, add_button])
        self.row_map[unique_label] = row

    def add_new_leh_field(self, label):
        suffix       = str(len([f for f in self.additional_leh_fields if f.startswith(label)]) + 1)
        unique_label = f"{label}_{suffix}"
        self.additional_leh_fields.append(unique_label)
        self.all_leh_fields = self.initial_leh_fields + self.additional_leh_fields

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
            text_frame  = tk.Frame(self.other_frame)
            text_frame.grid(row=i, column=1, padx=5, pady=2, sticky="w")
            text_widget = tk.Text(text_frame, width=40, height=5, font=self.FONT_CONFIG)
            text_widget.pack(side="left", fill="y")
            scrollbar   = tk.Scrollbar(text_frame, orient="vertical", command=text_widget.yview)
            scrollbar.pack(side="right", fill="y")
            text_widget.configure(yscrollcommand=scrollbar.set)

            def handle_tab(event, next_field_idx=i + 1):
                if next_field_idx < len(self.other_fields):
                    self.entries[self.other_fields[next_field_idx]].focus_set()
                elif next_field_idx == len(self.other_fields):
                    self.entries[f"Image ID ({self.fixed_photo_types[0]})"].focus_set()
                return "break"

            text_widget.bind("<Tab>", handle_tab)
            self.entries[field] = text_widget   # Text widgets are not in widget_to_key

    def create_photo_section(self):
        self.photo_frame = ttk.LabelFrame(self.other_photo_frame, text="Photo", padding=10)
        self.photo_frame.pack(side="left", fill="y", padx=10, pady=10)
        tk.Label(self.photo_frame, text="Type",     font=self.FONT_CONFIG).grid(row=0, column=0, padx=5, pady=2, sticky="e")
        tk.Label(self.photo_frame, text="Image ID", font=self.FONT_CONFIG).grid(row=0, column=1, padx=5, pady=2, sticky="e")
        self._build_fixed_photo_rows()
        # Initial blank additional field
        self._add_photo_id_field_at_row(len(self.fixed_photo_types) + 1, "Image ID (add1)")

    def _build_fixed_photo_rows(self):
        """Create the three fixed photo rows (Buccal / Lingual / Occlusal)."""
        for i, type_name in enumerate(self.fixed_photo_types, 1):
            tk.Label(self.photo_frame, text=type_name, font=self.FONT_CONFIG).grid(row=i, column=0, padx=5, pady=2, sticky="e")
            entry = tk.Entry(self.photo_frame, width=10, font=self.FONT_CONFIG)
            entry.grid(row=i, column=1, padx=5, pady=2)
            self._set_entry(f"Image ID ({type_name})", entry)
            self.photo_row_map[f"Image ID ({type_name})"] = i
            self.setup_navigation([entry])

    def _add_photo_id_field_at_row(self, row, unique_label):
        """Create one additional photo field (type + image_id + '+' button) at the given row (Fix #8)."""
        type_entry  = tk.Entry(self.photo_frame, width=10, font=self.FONT_CONFIG)
        image_entry = tk.Entry(self.photo_frame, width=10, font=self.FONT_CONFIG)
        type_entry.grid(row=row,  column=0, padx=5, pady=2)
        image_entry.grid(row=row, column=1, padx=5, pady=2)
        self._set_entry(f"{unique_label}_type", type_entry)
        self._set_entry(unique_label,           image_entry)
        add_button = ttk.Button(self.photo_frame, text="+", width=2, command=self.add_new_photo_id_field)
        add_button.grid(row=row, column=2, padx=2, pady=2)
        self.photo_row_map[unique_label] = row
        self.setup_navigation([type_entry, image_entry, add_button])

    def add_new_photo_id_field(self):
        """Always append at end — no row-shifting required (Fix #8)."""
        n            = len(self.additional_photo_fields) + 2   # add1 is the initial placeholder
        unique_label = f"Image ID (add{n})"
        self.additional_photo_fields.append(unique_label)
        self.all_photo_fields = self.fixed_photo_types + self.additional_photo_fields
        max_row = max(self.photo_row_map.values(), default=len(self.fixed_photo_types)) + 1
        self._add_photo_id_field_at_row(max_row, unique_label)
        self.canvas.update_idletasks()
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        self.entries[f"{unique_label}_type"].focus_set()

    # ── Navigation / input bindings ──────────────────────────────────────────

    def setup_navigation(self, widgets):
        for widget in widgets:
            widget.configure(takefocus=1)
            if isinstance(widget, tk.Entry):
                for direction in ["Up", "Down", "Left", "Right"]:
                    widget.bind(f"<{direction}>", lambda e, w=widget: self.handle_arrow_key(e, w))

    def setup_measurement_bindings(self, entry, field):
        # Fix #5: each event bound exactly once, no overlap
        entry.bind("<KeyRelease>", lambda e, f=field: self.calculate_avg(f))
        entry.bind("<KeyPress>",   self.validate_numeric_input)
        entry.bind("<Key>",        lambda e, ent=entry, f=field: self.handle_decimal_input(e, ent, f))

    def create_buttons(self):
        buttons = [
            ("Save",            self.save_and_clear),
            ("Previous Record", self.show_previous_record),
            ("NEXT(same)",      self.next_record),
            ("NEXT(another)",   self.next_another_record),
            ("New Record",      self.new_record),
            ("Export CSV",      self.export_csv),
        ]
        for text, cmd in buttons:
            ttk.Button(self.button_frame, text=text, command=cmd).pack(side="left", padx=5)

    def setup_menu(self):
        menu_bar  = tk.Menu(self.root)
        self.root.config(menu=menu_bar)
        file_menu = tk.Menu(menu_bar, tearoff=0)
        menu_bar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Open File", command=self.open_file)
        file_menu.add_command(label="Save As",   command=self.save_as)

    def setup_bindings(self):
        self.canvas.bind_all("<MouseWheel>", self.on_mouse_wheel)
        self.canvas.bind_all("<Button-4>",   self.on_mouse_wheel)
        self.canvas.bind_all("<Button-5>",   self.on_mouse_wheel)
        self.record_inner_frame.bind("<Configure>", lambda e: self.record_canvas.configure(scrollregion=self.record_canvas.bbox("all")))
        self.inner_frame.bind("<Configure>",        lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))

    # ── Calculations / input handling ────────────────────────────────────────

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
            self.averages[unique_label].config(text=f"{sum(values) / len(values):.2f}")
        else:
            self.averages[unique_label].config(text="N/A")

    def handle_decimal_input(self, event, entry, unique_label):
        if event.char in [".", "。"] or event.keysym == "KP_Decimal":
            entry.insert(entry.index(tk.INSERT), ".")
            self.calculate_avg(unique_label)
            return "break"
        return None

    def validate_numeric_input(self, event):
        allowed = ("BackSpace", "Tab", "Left", "Right", "Delete", "KP_Decimal", "Return")
        if event.keysym in allowed or event.char.isdigit() or event.char in (".", "。"):
            return
        return "break"

    def handle_arrow_key(self, event, current_widget):
        if not isinstance(current_widget, tk.Entry):
            return
        # Fix #4: O(1) reverse lookup instead of full-dict scan
        current_key = self.widget_to_key.get(current_widget)
        if not current_key:
            return

        combined = {**self.row_map, **self.photo_row_map}
        current_row = combined.get(current_key, 1)

        if event.keysym in ("Up", "Down"):
            target_row = current_row + (-1 if event.keysym == "Up" else 1)
            max_row = max(combined.values(), default=1)
            if 1 <= target_row <= max_row:
                for key, row in combined.items():
                    if row == target_row and key in self.entries:
                        self.entries[key].focus_set()
                        break
        elif event.keysym == "Left":
            if current_key.endswith("_type"):
                base = current_key[:-5]
                if base in self.entries:
                    self.entries[base].focus_set()
        elif event.keysym == "Right":
            type_key = f"{current_key}_type"
            if type_key in self.entries:
                self.entries[type_key].focus_set()

    def on_mouse_wheel(self, event):
        widget = getattr(event, "widget", None)
        if widget is not None:
            if isinstance(widget, ttk.Combobox) or "popdown" in str(widget).lower():
                return
        sys = platform.system()
        if sys == "Windows":
            self.canvas.yview_scroll(int(-1 * event.delta / 120), "units")
        elif sys == "Darwin":
            self.canvas.yview_scroll(int(-1 * event.delta), "units")
        else:
            self.canvas.yview_scroll(-1 if event.num == 4 else 1, "units")

    @staticmethod
    def get_short_label(label):
        if "(" in label and ")" in label:
            return label[label.index("(") + 1: label.index(")")]
        return label

    # ── Save / export ────────────────────────────────────────────────────────

    def save_and_clear(self):
        self.root.focus_set()
        if not self.current_file:
            messagebox.showerror("錯誤", "未選擇檔案！")
            self.status_label.config(text="No file selected!")
            return
        data = self.collect_data()
        if not data:
            return
        self.save_data(data, is_update=(self.current_record_index >= 0))
        self.save_to_cache(str(self.record_number), self.entries)
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
            if self.save_to_file():
                self.save_metadata()
                self.status_label.config(text=f"Exported to {os.path.basename(self.current_file)}")
            else:
                messagebox.showerror("錯誤", "匯出檔案失敗！請檢查日誌。")
                self.status_label.config(text="Failed to export file!")
        except Exception as e:
            messagebox.showerror("錯誤", f"匯出過程發生錯誤：{e}")
            self.status_label.config(text=f"Export error: {e}")

    def update_treeview(self):
        self.tree.delete(*self.tree.get_children())
        for rec in self.records:
            uuid_str   = rec.get("uuid", "")
            basic_info = rec.get("basic_info", {})
            self.tree.insert("", "end", values=(
                rec.get("record_id", ""),
                basic_info.get("Sample ID", "N/A"),
                basic_info.get("Tooth Type", "N/A"),
                f"{uuid_str}.json"
            ))
        self.tree["displaycolumns"] = (0, 1, 2)
        logger.debug(f"Treeview updated — {len(self.records)} records")

    def collect_data(self):
        basic_info = {label: self.entries[label].get() for label in self.basic_fields}
        if not basic_info.get("Sample ID") or not basic_info.get("Tooth Type"):
            messagebox.showerror("錯誤", "Sample ID 與 Tooth Type 為必填欄位！")
            self.status_label.config(text="Sample ID and Tooth Type are required!")
            return None

        measurements = {
            self.get_short_label(field): [
                self.entries[f"{field}1"].get(),
                self.entries[f"{field}2"].get(),
                self.entries[f"{field}3"].get()
            ]
            for field in self.measurement_fields
        }

        other_info = {field: self.entries[field].get("1.0", tk.END).strip() for field in self.other_fields}

        photos = []
        for key in self.entries:
            if key.startswith("Image ID (") and not key.endswith("_type"):
                ptype_key = f"{key}_type"
                photos.append({
                    "id":       key,
                    "type":     self.entries[ptype_key].get() if ptype_key in self.entries else "",
                    "image_id": self.entries[key].get()
                })

        # Fix #9: use leh_field_order directly — no recomputation
        leh_list = []
        for field in self.leh_field_order:
            vals = [self.entries[f"{field}{i}"].get() for i in [1, 2, 3]]
            if any(vals):
                try:
                    nums = [float(v) for v in vals if v]
                    avg  = f"{sum(nums) / len(nums):.2f}" if nums else ""
                except Exception:
                    avg = ""
                leh_list.append({
                    "id":          field,
                    "leh_side":    self.get_short_label(field),
                    "values":      vals,
                    "avg":         avg,
                    "count":       self.entries[f"{field} LEH Count"].get(),
                    "type":        self.entries[f"{field} LEH Type"].get(),
                    "cej_visible": self.entries[f"{field} CEJ Visible"].get(),
                    "photo_id":    self.entries[f"{field} Photo ID"].get()
                })

        sample_id_str = re.sub(r"[^\w]", "_", basic_info.get("Sample ID", "").replace(" ", "_"))
        uuid_str      = f"R{self.record_number}_S{self.sample_number}_{sample_id_str}"

        photo_fields_combined = [
            k for k in self.entries if k.startswith("Image ID (") and not k.endswith("_type")
        ]

        logger.debug(f"Collected record uuid={uuid_str}, leh={len(leh_list)}, photos={len(photos)}")
        return {
            "uuid":          uuid_str,
            "record_id":     self.record_number,
            "sample_number": self.sample_number,
            "basic_info":    basic_info,
            "measurements":  measurements,
            "other_info":    other_info,
            "photos":        photos,
            "leh_list":      leh_list,
            "leh_fields":    self.leh_field_order.copy(),
            "photo_fields":  photo_fields_combined
        }

    def save_data(self, data, is_update=False, new_record=False):
        updating = is_update and 0 <= self.current_record_index < len(self.records)
        if updating:
            existing = self.records[self.current_record_index]
            record_id     = existing.get("record_id", data.get("record_id", self.record_number))
            sample_number = existing.get("sample_number", data.get("sample_number", self.sample_number))
            uuid_str      = existing.get("uuid") or (
                f"R{record_id}_S{sample_number}_"
                + re.sub(r"[^\w]", "_", data.get("basic_info", {}).get("Sample ID", "").replace(" ", "_"))
            )
            data["sample_number"] = sample_number
        else:
            record_id     = self.record_number
            sample_id_str = re.sub(r"[^\w]", "_", data.get("basic_info", {}).get("Sample ID", "").replace(" ", "_"))
            uuid_str      = f"R{record_id}_S{self.sample_number}_{sample_id_str}"

        snapshot_filename = f"{uuid_str}.json"
        data["uuid"]      = uuid_str
        data["record_id"] = record_id

        # Save snapshot + update index (Fix #1 / Fix #6)
        try:
            snapshot_dir  = os.path.join(self.data_dir or ".", "snapshots")
            os.makedirs(snapshot_dir, exist_ok=True)
            snapshot_path = os.path.abspath(os.path.join(snapshot_dir, snapshot_filename))

            with open(snapshot_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            logger.debug(f"Saved snapshot: {snapshot_path}")

            index_path = os.path.join(snapshot_dir, "index.json")
            index_list = []
            if os.path.exists(index_path):
                with open(index_path, "r", encoding="utf-8") as f:
                    index_list = json.load(f)

            new_entry = {
                "uuid":            uuid_str,
                "snapshot_file":   snapshot_path,
                "record_number":   data.get("record_id", ""),
                "sample_number":   data.get("sample_number", ""),
                "sample_id":       data.get("basic_info", {}).get("Sample ID", ""),
                "tooth_type":      data.get("basic_info", {}).get("Tooth Type", ""),
                "timestamp":       datetime.now().isoformat()
            }

            # Fix #6: replace existing entry when updating (no duplicate accumulation)
            if is_update:
                for idx, entry in enumerate(index_list):
                    if entry.get("uuid") == uuid_str:
                        index_list[idx] = new_entry
                        break
                else:
                    index_list.append(new_entry)
            else:
                index_list.append(new_entry)

            with open(index_path, "w", encoding="utf-8") as f:
                json.dump(index_list, f, ensure_ascii=False, indent=2)
            logger.debug(f"Updated index: {index_path}")

        except Exception as e:
            logger.error(f"Failed to save snapshot or index: {e}")
            # Fix #1: single except block — no duplicate

        if is_update and self.current_record_index >= 0:
            self.records[self.current_record_index] = data
        else:
            self.records.append(data)
            self.record_order.append(snapshot_filename)

        # 若無年齡衝突或使用者手動暫停自動推算，將 Age Group 同步回同 Sample ID 的先前紀錄
        basic_info = data.get("basic_info", {})
        sample_id = (basic_info.get("Sample ID") or "").strip()
        if sample_id and basic_info.get("Age Group"):
            is_paused = getattr(self, "pause_age_auto_var", None) and self.pause_age_auto_var.get()
            if is_paused:
                self._sync_sample_age_group(sample_id, basic_info["Age Group"])
            else:
                _, has_conflict, _ = self._compute_sample_age_group(
                    sample_id=sample_id,
                    tooth=basic_info.get("Tooth Type", ""),
                    jaw_raw=basic_info.get("Jaw Type", ""),
                    wear_raw=basic_info.get("Wear Level", ""),
                    exclude_index=len(self.records) - 1 if not (is_update and self.current_record_index >= 0) else self.current_record_index
                )
                if not has_conflict:
                    self._sync_sample_age_group(sample_id, basic_info["Age Group"])

        if not updating:
            self.record_number += 1
        logger.debug(f"{'Updated' if updating else 'Saved'} {uuid_str}  total={len(self.records)}  next#={self.record_number}")

    def save_to_file(self):
        try:
            if not self.current_file or not os.path.isdir(os.path.dirname(self.current_file)):
                raise ValueError("Invalid file path or directory")

            fieldnames = (
                ["Record ID"] + self.basic_fields
                + [self.get_short_label(f) + i for f in self.measurement_fields for i in ["1", "2", "3"]]
                + ["LEH Side", "Value 1", "Value 2", "Value 3", "Avg", "LEH Count", "LEH Type", "CEJ Visible", "Photo ID"]
                + self.other_fields
                + ["Photo Type", "Photo ID"]
            )

            with open(self.current_file, "w", newline="", encoding="utf-8") as fh:
                writer = csv.DictWriter(fh, fieldnames=fieldnames)
                writer.writeheader()

                for rec in self.records:
                    base_row = {"Record ID": rec.get("record_id", "")}
                    base_row.update(rec.get("basic_info", {}))
                    for key, vals in rec.get("measurements", {}).items():
                        for idx, val in enumerate(vals, 1):
                            base_row[f"{key}{idx}"] = val
                    base_row.update(rec.get("other_info", {}))

                    photos   = rec.get("photos", [])
                    leh_list = rec.get("leh_list", [])
                    empty_leh = {
                        "LEH Side": "", "Value 1": "", "Value 2": "", "Value 3": "",
                        "Avg": "", "LEH Count": "", "LEH Type": "", "CEJ Visible": "", "Photo ID": ""
                    }

                    rows = [empty_leh] if not leh_list else [
                        {
                            "LEH Side": leh.get("leh_side", ""),
                            "Value 1":  leh.get("values", ["", "", ""])[0],
                            "Value 2":  leh.get("values", ["", "", ""])[1],
                            "Value 3":  leh.get("values", ["", "", ""])[2],
                            "Avg":      leh.get("avg", ""),
                            "LEH Count": leh.get("count", ""),
                            "LEH Type": leh.get("type", ""),
                            "CEJ Visible": leh.get("cej_visible", ""),
                            "Photo ID": leh.get("photo_id", "")
                        }
                        for leh in leh_list
                    ]

                    for leh_row in rows:
                        row = base_row.copy()
                        row.update(leh_row)
                        if photos:
                            row["Photo Type"] = photos[0].get("type", "")
                            row["Photo ID"]   = photos[0].get("image_id", "")
                        writer.writerow(row)
            return True
        except Exception as e:
            logger.error(f"save_to_file error: {e}")
            self.status_label.config(text=f"Error exporting file: {e}")
            return False

    def save_metadata(self):
        if not self.data_dir:
            return
        metadata_dir  = os.path.join(self.data_dir, "metadata")
        os.makedirs(metadata_dir, exist_ok=True)
        metadata_file = os.path.join(metadata_dir, "metadata.pkl")
        try:
            with open(metadata_file, "wb") as f:
                pickle.dump({
                    "records":        self.records,
                    "record_order":   self.record_order,
                    "record_number":  self.record_number,
                    "context_fields": self.context_fields
                }, f)
            logger.debug(f"Metadata saved — {len(self.records)} records")
        except Exception as e:
            logger.error(f"Failed to save metadata: {e}")

    def load_metadata(self):
        if not self.data_dir:
            return
        metadata_file = os.path.join(self.data_dir, "metadata", "metadata.pkl")
        if os.path.exists(metadata_file):
            try:
                with open(metadata_file, "rb") as f:
                    meta = pickle.load(f)
                self.records        = meta["records"]
                self.record_order   = meta["record_order"]
                self.record_number  = meta["record_number"]
                self.context_fields = meta.get("context_fields", [])
                self.basic_fields   = self.LABELS[:1] + self.context_fields + self.LABELS[2:9]
                logger.debug(f"Metadata loaded — {len(self.records)} records")
            except Exception as e:
                logger.error(f"Failed to load metadata: {e}")

    def clear_entries(self, preserve_fields=None):
        preserve_fields = preserve_fields or []
        for key, entry in list(self.entries.items()):
            if key not in preserve_fields and entry.winfo_exists():
                if isinstance(entry, tk.Text):
                    entry.delete("1.0", tk.END)
                elif isinstance(entry, ttk.Combobox):
                    entry.set("")
                elif isinstance(entry, tk.Entry):
                    entry.delete(0, tk.END)
        for avg_label in self.averages.values():
            if avg_label.winfo_exists():
                avg_label.config(text="N/A")

    def reset_leh_fields(self):
        self.additional_leh_fields = []
        self.all_leh_fields        = self.initial_leh_fields.copy()
        self.leh_field_order       = self.initial_leh_fields.copy()
        self.render_leh_fields()

    def reset_photo_fields(self):
        """Fully destroy and recreate the photo section to avoid stale widgets."""
        for widget in self.photo_frame.grid_slaves():
            widget.destroy()
        # Clean all photo entries from dicts
        for key in [k for k in list(self.entries.keys()) if k.startswith("Image ID (")]:
            self._del_entry(key)
        self.photo_row_map           = {}
        self.additional_photo_fields = []
        self.all_photo_fields        = self.fixed_photo_types.copy()
        # Recreate headers + fixed rows + initial add field
        tk.Label(self.photo_frame, text="Type",     font=self.FONT_CONFIG).grid(row=0, column=0, padx=5, pady=2, sticky="e")
        tk.Label(self.photo_frame, text="Image ID", font=self.FONT_CONFIG).grid(row=0, column=1, padx=5, pady=2, sticky="e")
        self._build_fixed_photo_rows()
        self._add_photo_id_field_at_row(len(self.fixed_photo_types) + 1, "Image ID (add1)")
        self.canvas.update_idletasks()
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def open_file(self):
        file_path = filedialog.askopenfilename(filetypes=[("CSV files", "*.csv"), ("All files", "*.*")])
        if not file_path:
            return
        self.current_file = file_path
        self.data_dir     = os.path.dirname(file_path)
        self.load_existing_file()
        self.load_metadata()
        self.update_treeview()

    def load_existing_file(self):
        try:
            with open(self.current_file, "r", encoding="utf-8") as fh:
                reader   = csv.DictReader(fh)
                all_data = list(reader)
            for row in all_data:
                if "Field Mapping" not in row:
                    row["Field Mapping"] = {"LEH": self.initial_leh_fields, "Photo": self.fixed_photo_types}
            if not self.records:
                self.records = all_data
                if self.records:
                    self.record_number = max(
                        (int(r["Record Number"]) for r in self.records if r.get("Record Number", "").isdigit()),
                        default=0
                    ) + 1
                else:
                    self.record_number = 1
                self.record_order = [
                    r["Record Number"] for r in self.records
                    if r.get("Record Number") not in self.record_order
                ]
            self.status_label.config(text=f"Loaded file: {os.path.basename(self.current_file)}")
        except Exception as e:
            self.status_label.config(text=f"Error loading file: {e}")

    def save_as(self):
        file_path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
        )
        if file_path:
            self.current_file = file_path
            self.data_dir     = os.path.dirname(file_path)
            self.save_to_file()
            self.save_metadata()
            self.status_label.config(text=f"Saved as {os.path.basename(self.current_file)}")

    # ── show_record — refactored into focused helpers (Fix #10) ─────────────

    def _rebuild_leh_ui(self, leh_fields):
        """Destroy existing LEH rows and recreate from leh_fields list."""
        for widget in self.leh_frame.grid_slaves():
            if int(widget.grid_info().get("row", 0)) > 0:
                widget.destroy()
        self.all_leh_fields        = leh_fields[:]
        self.leh_field_order       = leh_fields[:]
        self.additional_leh_fields = [f for f in leh_fields if f not in self.initial_leh_fields]
        self.render_leh_fields()

    def _rebuild_photo_ui(self, photo_fields):
        """Destroy all photo widgets and recreate from photo_fields list."""
        for widget in self.photo_frame.grid_slaves():
            widget.destroy()
        for key in [k for k in list(self.entries.keys()) if k.startswith("Image ID (")]:
            self._del_entry(key)
        self.photo_row_map           = {}
        self.additional_photo_fields = [
            f for f in photo_fields
            if f not in {f"Image ID ({t})" for t in self.fixed_photo_types}
        ]
        self.all_photo_fields = photo_fields[:]
        for idx, label in enumerate(photo_fields, 1):
            # Determine whether this is a fixed or additional field
            is_fixed = label in {f"Image ID ({t})" for t in self.fixed_photo_types}
            display_text = label[len("Image ID ("):-1] if is_fixed else ""
            tk.Label(self.photo_frame, text=display_text, font=self.FONT_CONFIG).grid(row=idx, column=0, padx=5, pady=2, sticky="e")
            entry = tk.Entry(self.photo_frame, width=10, font=self.FONT_CONFIG)
            entry.grid(row=idx, column=1, padx=5, pady=2)
            self._set_entry(label, entry)
            self.photo_row_map[label] = idx
            self.setup_navigation([entry])
            type_entry = tk.Entry(self.photo_frame, width=10, font=self.FONT_CONFIG)
            type_entry.grid(row=idx, column=2, padx=5, pady=2)
            self._set_entry(f"{label}_type", type_entry)
            self.setup_navigation([type_entry])

    def _populate_basic_info(self, record):
        for field in self.basic_fields:
            value = record.get("basic_info", {}).get(field)
            if value and field in self.entries:
                widget = self.entries[field]
                if isinstance(widget, ttk.Combobox):
                    widget.set(value)
                else:
                    widget.insert(0, value)

    def _populate_measurements(self, record):
        for key, vals in record.get("measurements", {}).items():
            for idx, val in enumerate(vals, 1):
                for f in self.measurement_fields:
                    if self.get_short_label(f) == key:
                        entry_key = f"{f}{idx}"
                        if entry_key in self.entries:
                            self.entries[entry_key].insert(0, val)
                        break
            for f in self.measurement_fields:
                if self.get_short_label(f) == key:
                    self.calculate_avg(f)
                    break

    def _populate_other_info(self, record):
        for field in self.other_fields:
            value = record.get("other_info", {}).get(field)
            if value and field in self.entries:
                self.entries[field].insert("1.0", value)

    def _populate_photos(self, record):
        for p in record.get("photos", []):
            pid_id    = p.get("id", "")
            pid_val   = p.get("image_id", "")
            pid_type  = p.get("type", "")
            if pid_id in self.entries:
                self.entries[pid_id].insert(0, pid_val)
            type_key = f"{pid_id}_type"
            if type_key in self.entries:
                self.entries[type_key].insert(0, pid_type)

    def _populate_leh(self, record):
        for leh in record.get("leh_list", []):
            leh_id = leh.get("id", "")
            if leh_id not in self.all_leh_fields:
                continue
            for idx, val in enumerate(leh.get("values", ["", "", ""]), 1):
                key = f"{leh_id}{idx}"
                if key in self.entries:
                    self.entries[key].insert(0, val)
            if leh_id in self.averages:
                self.averages[leh_id].config(text=leh.get("avg", "N/A"))
            for suffix, k in [
                (" LEH Count", "count"), (" LEH Type", "type"),
                (" CEJ Visible", "cej_visible"), (" Photo ID", "photo_id")
            ]:
                key = f"{leh_id}{suffix}"
                if key in self.entries:
                    self.entries[key].insert(0, leh.get(k, ""))

    def show_record(self, event=None):
        """Load and display a record from its snapshot file (Fix #10: delegates to helpers)."""
        selection = self.tree.selection()
        if not selection:
            return
        children = list(self.tree.get_children())
        if selection[0] in children:
            self.current_record_index = children.index(selection[0])
        values = self.tree.item(selection[0])["values"]
        if len(values) < 4:
            self.status_label.config(text="Snapshot filename missing")
            return

        snapshot_filename = values[3]
        snapshot_path     = os.path.join(self.data_dir or ".", "snapshots", snapshot_filename)
        logger.debug(f"Loading snapshot: {snapshot_path}  exists={os.path.exists(snapshot_path)}")

        if not os.path.exists(snapshot_path):
            self.status_label.config(text="Snapshot not found")
            return
        try:
            with open(snapshot_path, "r", encoding="utf-8") as f:
                record = json.load(f)
        except Exception as e:
            self.status_label.config(text=f"Failed to load snapshot: {e}")
            return

        self.clear_entries()

        leh_fields   = record.get("leh_fields", self.initial_leh_fields[:])
        self._rebuild_leh_ui(leh_fields)

        photo_fields = record.get("photo_fields") or [f"Image ID ({t})" for t in self.fixed_photo_types]
        self._rebuild_photo_ui(photo_fields)

        self._populate_basic_info(record)
        self._populate_measurements(record)
        self._populate_other_info(record)
        self._populate_photos(record)
        self._populate_leh(record)

        self.canvas.update_idletasks()
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        self.status_label.config(text=f"Showing record {record.get('record_id', '')}")
        logger.debug(f"Displayed record {snapshot_filename}")

    # ── Record navigation ────────────────────────────────────────────────────

    def show_previous_record(self):
        children = list(self.tree.get_children())
        if not children:
            return
        if self.current_record_index < 0:
            target_idx = len(children) - 1
        elif self.current_record_index > 0:
            target_idx = self.current_record_index - 1
        else:
            return
        self.current_record_index = target_idx
        self.tree.selection_set(children[target_idx])
        self.show_record()

    def next_record(self):
        data = self.collect_data()
        if data:
            self.save_data(data, is_update=(self.current_record_index >= 0))
            self.save_to_cache(str(self.record_number), self.entries)
            self.update_treeview()

        saved_basic  = {f: self.entries[f].get() for f in self.basic_fields}
        saved_photos = {f: self.entries[f].get()
                        for f in [f"Image ID ({t})" for t in self.fixed_photo_types] + self.additional_photo_fields
                        if f in self.entries}
        saved_ptypes = {f"{f}_type": self.entries[f"{f}_type"].get()
                        for f in self.additional_photo_fields if f"{f}_type" in self.entries}

        self.clear_entries()
        for f, v in {**saved_basic, **saved_photos, **saved_ptypes}.items():
            if v and f in self.entries:
                widget = self.entries[f]
                if isinstance(widget, ttk.Combobox):
                    widget.set(v)
                else:
                    widget.insert(0, v)

        self.reset_leh_fields()
        self.current_record_index = -1
        self.status_label.config(text="Ready for next record (same context)")

    def next_another_record(self):
        data = self.collect_data()
        if data:
            self.save_data(data, is_update=(self.current_record_index >= 0), new_record=True)
            self.save_to_cache(str(self.record_number), self.entries)
            self.update_treeview()

        saved_context = {f: self.entries[f].get() for f in self.context_fields if f in self.entries}
        self.clear_entries(preserve_fields=self.context_fields)
        self.reset_leh_fields()
        self.reset_photo_fields()
        for f, v in saved_context.items():
            if v and f in self.entries and self.entries[f].winfo_exists():
                self.entries[f].insert(0, v)

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
