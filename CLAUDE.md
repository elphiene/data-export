# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Workflow constraints
- **GitHub is blocked at the user's workplace.** Never suggest GitHub releases, raw GitHub URLs, or any github.com link as a file delivery method.

## Project Overview

**Ink Density Tool** — a desktop application for print industry professionals to record CMYK ink density readings from an X-Rite eXact spectrodensitometer, then export data to Adobe Illustrator-generated PDFs and Excel workbooks.

Implemented in Rust/egui (`data-export/ink-density-tool-rs/`).

## Commands

```bash
cd data-export/ink-density-tool-rs

# Linux build deps (Debian/Ubuntu — needed for egui/eframe)
# sudo apt-get install libgtk-3-dev libxcb-render0-dev libxcb-shape0-dev \
#   libxcb-xfixes0-dev libxkbcommon-dev libssl-dev

# Run in dev mode (Linux — GUI works, Illustrator export falls back to LibreOffice)
cargo run

# Release build
cargo build --release

# Cross-compile Windows EXE from Linux (requires mingw toolchain)
cargo build --release --target x86_64-pc-windows-gnu

# Run tests (currently only session round-trip tests exist)
cargo test
```

### Release
```bash
# From repo root — full release cycle: commit+push, cross-compile, deploy, email
./release.sh "optional commit message"
```
`release.sh` requires a `.env` file (see `.env.example`) with SMTP credentials. It:
1. Commits + pushes to `rust-version`
2. Cross-compiles the Windows EXE
3. Copies `ink-density-tool.exe` to `brandpack-tools/server/downloads/` (served at `https://eldev.cherrysofa.com/downloads/ink-density-tool.exe`)
4. Emails the download link to the recipient — this is the delivery mechanism since GitHub is blocked at the workplace

### CI Workflows
- `.github/workflows/build-rust.yml` — builds + tests Rust version on Windows and Linux; triggers on pushes to `rust-version` that touch `data-export/ink-density-tool-rs/**`; uploads Windows EXE as artifact

## Architecture

### Data Model
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
    ├── placeholders.rs        # <<PLACEHOLDER>> dict builder; shared by PDF paths (private mod)
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
- PDF: `placeholders::build_placeholders` builds `<<W1_DC>>`, `<<W1_R01_C>>`, etc.; weights split into chunks of ≤3 (W1/W2/W3 slots in a single template); on Windows calls `Illustrator.exe /b <temp.jsx>`, on Linux calls LibreOffice UNO (via embedded `lo_uno_helper.py` + JSON placeholder dict); chunks merged via `pdf_merge`
- Excel: `excel.rs` picks `template_standard.xlsx` (14 steps) or `template_extended.xlsx` (16 steps); fills placeholders; adds sheet pairs for extra shapes
- Exports run on `std::thread::spawn` daemon threads; status fed back via `Arc<Mutex<ExportStatus>>`

### Design Constraints
- **No win32com/comtypes** — Illustrator driven via subprocess + ExtendScript (`/b` batch flag)
- **Column-major Tab order is intentional** — matches X-Rite eXact scan sequence; do not change to row-major
- **Non-destructive Illustrator workflow** — templates opened as copies, never saved
- **PDF/X-4:2008** preset used for print-ready output
- Assets (`runner.jsx`, `lo_uno_helper.py`, `*.xlsx` templates) are embedded via `rust-embed`
- `data-export/ink-density-tool-rs/TEMPLATE_GUIDE.md` documents all `<<PLACEHOLDER>>` names used in Illustrator `.ai` templates

### Settings Keys
- `illustrator_path` — path to `Illustrator.exe`
- `ai_template` / `ai_template_extended` — `.ai` master template paths (standard 14-step / extended 16-step); each template contains W1/W2/W3 slots for up to 3 weights per page
- `default_weight_labels`, `default_step_labels`, `last_session_path`
