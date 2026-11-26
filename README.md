# LEH Record Program

A desktop GUI application built with **Python** and **Tkinter (`tkinter` / `ttk`)** for recording dental measurements, Linear Enamel Hypoplasia (LEH) observations, and photo metadata, with real-time age-group estimation and local JSON / CSV export.

以 **Python (Tkinter / ttk)** 開發的本機桌面資料紀錄程式，用於牙齒形態量測、線性釉質發育不全（LEH）紀錄與照片編號管理，支援同個體多顆牙齒的即時年齡分期交集推算與 JSON / CSV 匯出。

---

## Features / 主要功能

- **Basic Information & Dynamic Age Group Estimation**：
  - `Tooth Type` 下拉選單與 `Jaw Type`（`U` / `L` / `un`）唯讀選單。
  - 依據 `Tooth Type`、`Jaw Type` 與 `Wear Level`（數值分級）自動反查 `WEAR_CLASS_TABLE` 對應的年齡分期（`A`–`G`）。
  - 自動將相同 `Sample ID` 的多顆牙齒進行**年齡分期交集**，並在儲存時同步回寫先前同 `Sample ID` 的紀錄與 snapshot；若發生年齡衝突則保留當下牙齒區間並於狀態列提示。
  - 提供 **Pause Auto** 勾選格，可隨時暫停自動推算並手動輸入 `Age Group`。
- **Measurements & LEH Records**：
  - 每個量測項目支援 3 次重複測量並即時計算平均值。
  - 支援動態新增多筆 LEH 欄位（`+`）與多組照片 ID 欄位。
- **Record Management & Export**：
  - **Save**：儲存或覆寫目前編輯的紀錄（支援從左側 `Previous Records` 雙擊載入修改）。
  - **Previous Record**：載入上一筆已存紀錄。
  - **NEXT(same)**：儲存目前紀錄並保留基本個體資訊與照片，接續紀錄同一個體的下一顆牙齒。
  - **NEXT(another)**：儲存目前紀錄並僅保留 `Context` 欄位，開始下一個體的紀錄。
  - **Export CSV**：匯出完整紀錄至 CSV 檔並保存 `metadata/metadata.pkl`。
  - 每筆紀錄自動保存結構化 JSON snapshot（`snapshots/`）與索引（`snapshots/index.json`）。

---

## Quick Start / 使用方式

### Option A: Download Executable (Windows Releases)
1. Go to the repository's **Releases** page on GitHub.
2. Download `leh_record.exe` from the latest release.
3. Double-click `leh_record.exe` to launch (no Python installation required).

### Option B: Run from Source (Python)
Requires **Python 3.8+** (uses only Python standard library — no external `pip` packages needed).

```bash
python leh_record.py
```

---

## Build Standalone Executable / 打包成 `.exe`（供上傳 Releases）

If you want to package `leh_record.py` into a single Windows executable for GitHub Releases:

```bash
pip install pyinstaller
pyinstaller --onefile --windowed leh_record.py
```

The generated executable will be at `dist/leh_record.exe`.

---

## Output Structure / 資料輸出結構

When you select or create a working folder, the program stores data locally in:

```text
<selected_folder>/
├── LEHrec_YYYYMMDD.csv       # Exported CSV (via Export CSV)
├── snapshots/
│   ├── index.json            # Record index for the sidebar list
│   └── R1_S1_<SampleID>.json # Per-record JSON snapshot
└── metadata/
    └── metadata.pkl          # Session metadata for reloading
```
