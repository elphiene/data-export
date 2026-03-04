# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Ink Density Tool** — a desktop application for print industry professionals to record CMYK ink density readings from an X-Rite eXact spectrodensitometer, then export data to Adobe Illustrator-generated PDFs and Excel workbooks.

There are two implementations:
- **Python/Tkinter** (`data-export/ink-density-tool/`) — original, ships as `InkDensityTool.exe` via PyInstaller
- **Rust/egui** (`data-export/ink-density-tool-rs/`) — active rewrite on the `rust-version` branch

## Commands

### Rust version (active development)
```bash
cd data-export/ink-density-tool-rs

# Run in dev mode (Linux — GUI works, Illustrator export falls back to LibreOffice)
cargo run

# Release build
cargo build --release

# Cross-compile Windows EXE from Linux (requires mingw toolchain)
cargo build --release --target x86_64-pc-windows-gnu
```

### Python version
```bash
# Install dependencies
pip install -r data-export/ink-density-tool/requirements.txt

# Run (Linux dev mode — Illustrator export won't work)
python data-export/ink-density-tool/main.py

# Build Windows EXE
cd data-export/ink-density-tool && pyinstaller build.spec
# Output: dist/InkDensityTool.exe
```

There is no test suite. The GitHub Actions workflow (`.github/workflows/build.yml`) still targets the Python version and produces an `InkDensityTool.exe` GitHub Release on pushes to `main` that touch `data-export/ink-density-tool/**`.

## Architecture

### Shared Data Model (both implementations)
`JobConfig` → `shapes: list[ShapeData]` → `weights: list[WeightData]`
- `WeightData`: `label`, `density[4]` (C/M/Y/K max density), `steps[N][4]` (14 or 16 step rows × 4 colours)
- Step presets: `STEP_LABELS_14` (100→1) and `STEP_LABELS_16` (100→0.4)
- Session files are JSON, forward-compatible via pad/trim on load

### Rust Implementation (`ink-density-tool-rs/`)

**Stack:** `eframe`/`egui` for the GUI, `serde_json` for sessions, `umya-spreadsheet` for Excel, `lopdf` for PDF merge, `rfd` for file dialogs, `rust-embed` for asset bundling.

**Module layout:**
```
src/
├── main.rs                    # Entry point — eframe::run_native
├── settings.rs                # JSON settings (dirs crate → %APPDATA%/InkDensityTool/)
├── core/
│   ├── models.rs              # JobConfig, ShapeData, WeightData; STEP_LABELS_14/16
│   └── session.rs             # save_session / load_session
├── gui/
│   ├── app.rs                 # InkDensityApp (eframe::App); top-level layout + menus
│   ├── job_config.rs          # Left panel: metadata fields + weight label chips
│   ├── shape_tabs.rs          # Shape tab switcher + inner weight tabs
│   └── weight_grid.rs         # Data-entry grid; column-major focus order
└── export/
    ├── placeholders.rs        # <<PLACEHOLDER>> dict builder; shared by PDF paths
    ├── illustrator.rs         # JSX substitution → Illustrator.exe subprocess (Windows)
    ├── libreoffice.rs         # LibreOffice headless UNO bridge (Linux)
    ├── excel.rs               # umya-spreadsheet template fill
    └── pdf_merge.rs           # lopdf PdfWriter merge
```

**GUI data flow:**
1. `InkDensityApp.update()` — single egui frame callback; polls `Arc<Mutex<ExportStatus>>` for background thread results
2. Left panel (`job_config::show_job_config`) broadcasts weight/step label changes to `ShapeNotebookState`
3. `shape_tabs::show_shape_notebook` — outer tabs = shapes, inner tabs = weights per shape
4. `weight_grid` — column-major Tab order (all C rows → M → Y → K) to match X-Rite eXact scan sequence; 100% row is read-only
5. **DataCatcher auto-advance**: 300 ms settle timer per field using `ui.input(|i| i.time)`; if still focused and non-empty after timer, advances focus automatically

**Export flow:**
- PDF: `placeholders::build_placeholders` builds `<<W1_DC>>`, `<<W1_R01_C>>`, etc.; weights split into chunks of ≤3 (1/2/3 LPI template slots); on Windows calls `Illustrator.exe /b <temp.jsx>`, on Linux calls LibreOffice UNO; chunks merged via `pdf_merge`
- Excel: `excel.rs` picks `template_standard.xlsx` (14 steps) or `template_extended.xlsx` (16 steps); fills placeholders; adds sheet pairs for extra shapes
- Exports run on `std::thread::spawn` daemon threads; status fed back via `Arc<Mutex<ExportStatus>>`

### Python Implementation (`ink-density-tool/`)

**Stack:** Tkinter for GUI, `openpyxl` for Excel, `pypdf` for PDF merge, `pyinstaller` for packaging.

```
ink-density-tool/
├── main.py               # Entry point
├── settings.py           # JSON-backed key-value store (%APPDATA%/InkDensityTool/)
├── core/
│   ├── models.py         # Dataclasses: JobConfig, ShapeData, WeightData
│   └── session.py        # save_session / load_session; _pad_or_trim()
├── gui/
│   ├── app.py            # Main Tk window; menu, layout, export dispatch
│   ├── job_config.py     # Left panel: metadata + weight label chips
│   ├── shape_tab.py      # Two-level Notebook (shapes → weights)
│   └── weight_grid.py    # Column-major Tab order grid
├── datacatcher_sim.py    # Linux xdotool utility for DataCatcher simulation
└── export/
    ├── illustrator.py    # JSX generation + Illustrator subprocess + pypdf merge
    ├── excel.py          # openpyxl template fill; merged-cell resolution
    └── libreoffice.py    # Linux alternative — headless LibreOffice UNO bridge
```

**Key Python-specific notes:**
- `app.collect_job()` walks the Tkinter widget tree to produce a `JobConfig`
- `excel.py` resolves `MergedCell` objects by walking `merged_cells.ranges` to find parent cells before writing
- Exports run as daemon `threading.Thread`; status bar updated via `after()` callbacks

### Shared Design Constraints
- **No win32com/comtypes** — Illustrator driven via subprocess + ExtendScript (`/b` batch flag)
- **Column-major Tab order is intentional** — matches X-Rite eXact scan sequence; do not change to row-major
- **Non-destructive Illustrator workflow** — templates opened as copies, never saved
- **PDF/X-4:2008** preset used for print-ready output
- Assets (`runner.jsx`, `*.xlsx` templates) are embedded in both builds

### Settings Keys (both implementations)
- `illustrator_path` — path to `Illustrator.exe`
- `ai_template_1lpi` / `_2lpi` / `_3lpi` (+ `_extended` variants) — `.ai` master template paths
- `default_weight_labels`, `default_step_labels`, `last_session_path`
