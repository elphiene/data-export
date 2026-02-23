# Ink Density Tool — Implementation Plan

## What It Does

A Windows desktop app that:
1. Lets you type in CMYK ink density readings per job
2. Saves/loads your session so you can come back to it
3. Exports a populated PDF via Illustrator (by scripting Illustrator directly)
4. Exports a populated Excel file

---

## What We Know From the Template Images

Each job produces one multi-page PDF. Each **page = one dot shape** (e.g. HD 16, CRY 01, CRY 02).

Each page has up to 3 **weight tables** side by side (e.g. 120#, 150#, 200#). Each table has:
- 1 **density row**: 4 max-density readings (C, M, Y, K) — decimal values like `2.11`
- **14 step rows**: percentage readings per colour (C, M, Y, K) per step (100, 95, 90 … 1)
- A **reference density column** (the teal numbers) — this is a fixed fixture in the template, never changes

Variable metadata per page: customer name, stock code, CRS, date, dot shape name, weight labels.

Per job totals (example — 3 shapes × 3 weights × 60 values): **540 values** entered once, never by hand again.

---

## Tech Stack

| Purpose | Library | Why |
|---|---|---|
| GUI | **tkinter** (built-in) | No extra install, bundles cleanly with PyInstaller |
| Excel export | **openpyxl** | Reads/writes .xlsx, preserves existing formatting |
| PDF merging | **pypdf** | Merge one PDF per shape into a single final PDF |
| Build | **PyInstaller** | Creates a single standalone `.exe` — no Python install needed |
| Illustrator | **subprocess + ExtendScript (.jsx)** | Avoids win32com/comtypes PyInstaller nightmare; simple and reliable |

No win32com, no web server, no database.

---

## Architecture

```
ink-density-tool/
├── main.py                  # Entry point; PyInstaller target
├── gui/
│   ├── app.py               # Main window, menu bar, layout
│   ├── job_config.py        # Left panel: customer, stock, CRS, date, weight/step config
│   ├── shape_tab.py         # One tab per dot shape; sub-tabs per weight
│   └── weight_grid.py       # Data entry grid: density row + 14 step rows × 4 colours
├── core/
│   ├── models.py            # Dataclasses: JobConfig, ShapeData, WeightData
│   └── session.py           # JSON save/load
├── export/
│   ├── illustrator.py       # Generate JSX → call Illustrator → merge PDFs
│   └── excel.py             # openpyxl: open template, fill cells, save
├── assets/
│   ├── runner.jsx           # JSX script template (with <<PLACEHOLDERS>>)
│   └── template.xlsx        # Excel template (provided separately)
├── settings.py              # App settings (Illustrator path, defaults)
├── requirements.txt
└── build.spec               # PyInstaller spec
```

---

## Data Model

```python
@dataclass
class WeightData:
    label: str               # "120#"
    density: list[float]     # [C, M, Y, K] — 4 values, top density row
    steps: list[list[float]] # [14 rows][4 colours] — the percentage readings

@dataclass
class ShapeData:
    name: str                # "HD 16"
    weights: list[WeightData]

@dataclass
class JobConfig:
    customer: str
    stock: str
    crs: str
    date: str
    weight_labels: list[str]   # e.g. ["120#", "150#", "200#"] — configurable per job
    step_labels: list[str]     # ["100", "95", "90", "80", "70", "60", "50", "40", "30", "20", "10", "5", "3", "1"]
    colour_names: list[str]    # ["C", "M", "Y", "K"]
    shapes: list[ShapeData]
    template_ai_path: str      # path to the Illustrator master template
    template_xlsx_path: str    # path to the Excel template
```

The whole job saves to a `.json` session file. Reopening it restores all values.

---

## GUI Layout

```
┌──────────────────────────────────────────────────────────────────┐
│  File   Settings   Export                                        │
├────────────────┬─────────────────────────────────────────────────┤
│                │  [ HD 16 ] [ CRY 01 ] [ CRY 02 ] [ + Add ]     │
│  Job Config    ├─────────────────────────────────────────────────┤
│                │  [ 120# ] [ 150# ] [ 200# ]                     │
│  Customer:     │  ┌───────────────────────────────────────────┐  │
│  [__________]  │  │         C        M        Y        K      │  │
│                │  │ D    [2.11]   [1.80]   [1.66]   [1.79]   │  │
│  Stock:        │  │ 100  [    ]   [    ]   [    ]   [    ]   │  │
│  [__________]  │  │  95  [    ]   [    ]   [    ]   [    ]   │  │
│                │  │  90  [    ]   [    ]   [    ]   [    ]   │  │
│  CRS:          │  │  80  ...                                  │  │
│  [__________]  │  │   1  [    ]   [    ]   [    ]   [    ]   │  │
│                │  └───────────────────────────────────────────┘  │
│  Date:         │                                                  │
│  [__________]  │  [ Export → Illustrator PDF ]  [ Export → Excel]│
│                │                                                  │
│  Weights:      │  Status: Ready                                   │
│  [120#][150#]  │                                                  │
│  [200#] [+]    │                                                  │
│                │                                                  │
│  Steps: 14 ✓   │                                                  │
└────────────────┴─────────────────────────────────────────────────┘
```

- **Left panel**: always-visible job config. Weight labels are editable inline (click to rename, + to add, × to remove).
- **Right panel**: ttk.Notebook — one tab per dot shape, + button to add/remove shapes.
- Each shape tab: sub-notebook with one tab per weight.
- Each weight tab: the data entry grid. Tab key moves between fields left-to-right, top-to-bottom.
- Fields accept only numeric input (validated on entry).
- Bottom status bar shows export progress / errors.

---

## Illustrator Export Flow

### One-time template setup (user does this once)
The master Illustrator template needs placeholder text in each data cell. We provide a reference guide. Example placeholder names:

| Location | Placeholder |
|---|---|
| Customer name | `<<CUSTOMER>>` |
| Stock code | `<<STOCK>>` |
| CRS | `<<CRS>>` |
| Date | `<<DATE>>` |
| Dot shape name | `<<SHAPE>>` |
| Weight 1 label | `<<W1_LABEL>>` |
| Weight 1, C max density | `<<W1_DC>>` |
| Weight 1, M max density | `<<W1_DM>>` |
| Weight 1, step row 1, C | `<<W1_R01_C>>` |
| Weight 1, step row 14, K | `<<W1_R14_K>>` |
| Weight 2, step row 7, M | `<<W2_R07_M>>` |
| *(and so on)* | |

Total placeholders per page: ~185 (5 metadata + 3 weight labels + 12 density + 168 step values).

The template is saved as a "blank master" `.ai` file. The tool never modifies this file — it always works from a copy.

### Export process (per job)
1. For each dot shape, Python builds a dictionary of `{ "<<PLACEHOLDER>>": "value" }`.
2. A temp `.jsx` script is generated from `runner.jsx` with all replacements embedded.
3. `subprocess.run(["Illustrator.exe", "/b", "temp_script.jsx"])` runs the script.
4. The JSX opens the master template (as a new document), replaces every placeholder, exports the page as a PDF, closes without saving.
5. After all shapes are done, `pypdf` merges the individual PDFs into one final file.
6. Temp files are cleaned up.

### Finding the Illustrator executable
The tool checks common installation paths in order:
```
C:\Program Files\Adobe\Adobe Illustrator 20XX\Support Files\Contents\Windows\Illustrator.exe
```
If not found, Settings lets the user browse to it. The path is saved in `settings.json`.

---

## Excel Export

Using `openpyxl`:
1. Load the Excel template with `load_workbook(template_path)`.
2. Fill cells by coordinate (cell addresses are defined in a mapping in `excel.py`).
3. Save to a new output file — template is never modified.

The Excel cell mapping will be defined once we see the Excel template.

---

## Session Management

- On launch: loads the last session automatically if one exists.
- File > Save / Save As: saves `.json` session file.
- File > Open: loads a saved session.
- The JSON file is human-readable and shareable.

---

## Settings

A `settings.json` file (in the app's data directory) stores:
- Illustrator executable path
- Default template paths (AI + xlsx)
- Default weight labels
- Default step labels

Settings are accessible from the Settings menu.

---

## Build

PyInstaller spec (`build.spec`):
- `--onefile` — single `.exe`, no installer needed
- Bundles `assets/` directory (JSX template + xlsx template)
- Windows target only
- The `.exe` can be copied to a USB drive or shared folder and run directly

Note: Windows SmartScreen may show a warning the first time (unsigned binary). This is normal for in-house tools — click "Run anyway".

---

## Implementation Order

1. **`core/models.py`** — data model (dataclasses)
2. **`core/session.py`** — JSON save/load
3. **`gui/weight_grid.py`** — the data entry grid widget (most complex UI piece)
4. **`gui/job_config.py`** — left panel form
5. **`gui/shape_tab.py`** — shape tab with weight sub-tabs
6. **`gui/app.py`** — main window, wires everything together
7. **`export/illustrator.py`** — JSX generation + subprocess call
8. **`export/excel.py`** — openpyxl export (once Excel template is received)
9. **`assets/runner.jsx`** — JSX script template
10. **`settings.py`** — settings management
11. **`main.py`** — entry point
12. **`build.spec`** — PyInstaller spec + test build

---

## What's Needed Before Implementation

- [ ] The actual Illustrator `.ai` template file — to verify the text frame structure and confirm the JSX approach will work as-is, or if we need to adapt it
- [ ] The Excel template — for the cell mapping in `excel.py`

The Illustrator template file is the most critical: once we can see the layer/text frame structure, we can write a "discovery JSX" that dumps all text frame contents, which lets us build the exact placeholder mapping without guesswork.
