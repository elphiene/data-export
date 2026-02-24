"""Main application window."""
from __future__ import annotations

import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

from core.models import JobConfig, ShapeData, WeightData
from core.session import save_session, load_session
from gui.job_config import JobConfigPanel
from gui.shape_tab import ShapeNotebook
import settings as app_settings


class App(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Ink Density Tool")
        self.minsize(900, 600)
        self._current_path: str | None = None
        self._dirty = False
        self._export_threads: list[threading.Thread] = []

        self._build_menu()
        self._build_layout()
        self._build_status_bar()

        self._load_initial_session()

    # ------------------------------------------------------------------
    # Menu
    # ------------------------------------------------------------------

    def _build_menu(self) -> None:
        menubar = tk.Menu(self)
        self.config(menu=menubar)

        # File
        file_menu = tk.Menu(menubar, tearoff=False)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="New", accelerator="Ctrl+N", command=self._new_job)
        file_menu.add_command(label="Open…", accelerator="Ctrl+O", command=self._open_session)
        file_menu.add_separator()
        file_menu.add_command(label="Save", accelerator="Ctrl+S", command=self._save_session)
        file_menu.add_command(label="Save As…", accelerator="Ctrl+Shift+S", command=self._save_as)
        file_menu.add_separator()
        file_menu.add_command(label="Fill Example Data", command=self._fill_example_data)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self._on_close)

        self.bind_all("<Control-n>", lambda e: self._new_job())
        self.bind_all("<Control-o>", lambda e: self._open_session())
        self.bind_all("<Control-s>", lambda e: self._save_session())
        self.bind_all("<Control-S>", lambda e: self._save_as())

        # Settings
        settings_menu = tk.Menu(menubar, tearoff=False)
        menubar.add_cascade(label="Settings", menu=settings_menu)
        settings_menu.add_command(label="Illustrator Path…", command=self._set_illustrator_path)
        settings_menu.add_command(label="Default Templates…", command=self._set_templates)

        # Export
        export_menu = tk.Menu(menubar, tearoff=False)
        menubar.add_cascade(label="Export", menu=export_menu)
        export_menu.add_command(label="Export → Illustrator PDF", command=self._export_pdf)
        export_menu.add_command(label="Export → Excel", command=self._export_excel)

        self.protocol("WM_DELETE_WINDOW", self._on_close)

    # ------------------------------------------------------------------
    # Layout
    # ------------------------------------------------------------------

    def _build_layout(self) -> None:
        pane = ttk.PanedWindow(self, orient="horizontal")
        pane.pack(fill="both", expand=True)

        # Left panel
        left_frame = ttk.Frame(pane, width=200)
        left_frame.pack_propagate(False)
        pane.add(left_frame, weight=0)

        self._config_panel = JobConfigPanel(
            left_frame,
            on_weights_changed=self._on_weights_changed,
            on_steps_changed=self._on_steps_changed,
        )
        self._config_panel.pack(fill="both", expand=True)

        # Right panel
        right_frame = ttk.Frame(pane)
        pane.add(right_frame, weight=1)

        # Shape notebook + toolbar
        toolbar = ttk.Frame(right_frame)
        toolbar.pack(fill="x", padx=4, pady=(4, 0))

        self._shape_notebook = ShapeNotebook(right_frame, on_change=self._mark_dirty)
        self._shape_notebook.pack(fill="both", expand=True, padx=4, pady=4)

        ttk.Button(toolbar, text="+ Add Shape", command=self._add_shape).pack(side="left")
        ttk.Button(toolbar, text="Rename", command=self._rename_shape).pack(side="left", padx=(4, 0))
        ttk.Button(toolbar, text="✕ Remove", command=self._remove_shape).pack(side="left", padx=(4, 0))

        # Export buttons
        btn_frame = ttk.Frame(right_frame)
        btn_frame.pack(fill="x", padx=4, pady=(0, 4))
        ttk.Button(btn_frame, text="Export → Illustrator PDF", command=self._export_pdf).pack(
            side="left", padx=(0, 8)
        )
        ttk.Button(btn_frame, text="Export → Excel", command=self._export_excel).pack(side="left")

    def _build_status_bar(self) -> None:
        self._status_var = tk.StringVar(value="Ready")
        bar = ttk.Label(self, textvariable=self._status_var, anchor="w", relief="sunken")
        bar.pack(side="bottom", fill="x", padx=2, pady=2)

    # ------------------------------------------------------------------
    # Session management
    # ------------------------------------------------------------------

    def _load_initial_session(self) -> None:
        last = app_settings.get("last_session_path")
        if last:
            try:
                job = load_session(last)
                self._populate_from_job(job)
                self._current_path = last
                self._status("Loaded: " + last)
                return
            except Exception:
                pass
        # Start with a blank job
        self._new_job()

    def _new_job(self) -> None:
        if self._dirty and not self._confirm_discard():
            return
        step_labels = self._config_panel.get_step_labels()
        job = JobConfig(
            weight_labels=app_settings.get("default_weight_labels", ["120#", "150#", "200#"]),
            step_labels=step_labels,
        )
        # Add one blank shape to start
        job.shapes = [
            ShapeData(
                name="Shape 1",
                weights=[
                    WeightData(
                        label=lbl,
                        density=[0.0] * 4,
                        steps=[[0.0] * 4 for _ in step_labels],
                    )
                    for lbl in job.weight_labels
                ],
            )
        ]
        self._populate_from_job(job)
        self._current_path = None
        self._dirty = False
        self.title("Ink Density Tool")
        self._status("New job")

    def _populate_from_job(self, job: JobConfig) -> None:
        self._config_panel.populate(job)
        self._shape_notebook.populate(job.shapes, job.weight_labels, job.step_labels)

    def _collect_job(self) -> JobConfig:
        meta = self._config_panel.get_metadata()
        weight_labels = self._config_panel.get_weight_labels()
        step_labels = self._config_panel.get_step_labels()
        shapes = self._shape_notebook.get_all_shapes()

        return JobConfig(
            customer=meta["customer"],
            print_type=meta["print_type"],
            stock_desc=meta["stock_desc"],
            finish=meta["finish"],
            dot_shape_type=meta["dot_shape_type"],
            dot_shape_number=meta["dot_shape_number"],
            date=meta["date"],
            set_number=meta["set_number"],
            job_number=meta["job_number"],
            weight_labels=weight_labels,
            step_labels=step_labels,
            shapes=shapes,
        )

    def _save_session(self) -> None:
        if self._current_path is None:
            self._save_as()
            return
        try:
            save_session(self._collect_job(), self._current_path)
            self._dirty = False
            self._status(f"Saved: {self._current_path}")
        except Exception as exc:
            messagebox.showerror("Save Error", str(exc))

    def _save_as(self) -> None:
        path = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("Ink Density Session", "*.json"), ("All Files", "*.*")],
        )
        if not path:
            return
        self._current_path = path
        app_settings.set("last_session_path", path)
        self._save_session()
        self.title(f"Ink Density Tool — {path}")

    def _open_session(self) -> None:
        if self._dirty and not self._confirm_discard():
            return
        path = filedialog.askopenfilename(
            filetypes=[("Ink Density Session", "*.json"), ("All Files", "*.*")]
        )
        if not path:
            return
        try:
            job = load_session(path)
            self._populate_from_job(job)
            self._current_path = path
            self._dirty = False
            app_settings.set("last_session_path", path)
            self.title(f"Ink Density Tool — {path}")
            self._status(f"Opened: {path}")
        except Exception as exc:
            messagebox.showerror("Open Error", str(exc))

    # ------------------------------------------------------------------
    # Export
    # ------------------------------------------------------------------

    def _export_pdf(self) -> None:
        job = self._collect_job()
        missing = [
            f"{n} LPI" for n in (1, 2, 3)
            if not app_settings.get(f"ai_template_{n}lpi")
        ]
        if missing:
            messagebox.showwarning(
                "No Template",
                f"Set the Illustrator template path(s) for {', '.join(missing)} in Settings.",
            )
            return
        out_path = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            filetypes=[("PDF", "*.pdf"), ("All Files", "*.*")],
            title="Save exported PDF",
        )
        if not out_path:
            return
        self._status("Exporting PDF…")
        self._run_in_thread(self._do_export_pdf, job, out_path)

    def _do_export_pdf(self, job: JobConfig, out_path: str) -> None:
        try:
            import sys
            if sys.platform == "win32":
                from export.illustrator import export_pdf
            else:
                from export.libreoffice import export_pdf
            export_pdf(job, out_path)
            self.after(0, self._status, f"PDF exported: {out_path}")
        except Exception as exc:
            self.after(0, messagebox.showerror, "Export Error", str(exc))
            self.after(0, self._status, "Export failed.")

    def _export_excel(self) -> None:
        job = self._collect_job()
        out_path = filedialog.asksaveasfilename(
            defaultextension=".xlsx",
            filetypes=[("Excel Workbook", "*.xlsx"), ("All Files", "*.*")],
            title="Save exported Excel",
        )
        if not out_path:
            return
        self._status("Exporting Excel…")
        self._run_in_thread(self._do_export_excel, job, out_path)

    def _do_export_excel(self, job: JobConfig, out_path: str) -> None:
        try:
            from export.excel import export_excel
            export_excel(job, out_path)
            self.after(0, self._status, f"Excel exported: {out_path}")
        except Exception as exc:
            self.after(0, messagebox.showerror, "Export Error", str(exc))
            self.after(0, self._status, "Export failed.")

    # ------------------------------------------------------------------
    # Settings dialogs
    # ------------------------------------------------------------------

    def _set_illustrator_path(self) -> None:
        current = app_settings.get("illustrator_path", "")
        path = filedialog.askopenfilename(
            title="Select Illustrator.exe",
            initialfile=current or "Illustrator.exe",
            filetypes=[("Executable", "*.exe"), ("All Files", "*.*")],
        )
        if path:
            app_settings.set("illustrator_path", path)
            self._status(f"Illustrator path set: {path}")

    def _set_templates(self) -> None:
        dialog = _TemplatesDialog(self)
        self.wait_window(dialog)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _fill_example_data(self) -> None:
        """Populate all fields with realistic dummy data for testing."""
        # fmt: off
        step_labels = self._config_panel.get_step_labels()
        weight_labels = ["120#", "150#", "200#"]

        # Realistic CMYK step readings that taper from 100 down to near 0
        _steps_c = [100.0, 93.2, 86.5, 74.1, 62.8, 52.3, 42.0, 32.7, 23.9, 15.4,  7.8, 3.9, 2.3, 1.1]
        _steps_m = [100.0, 94.1, 87.3, 75.6, 64.2, 53.8, 43.5, 34.1, 25.2, 16.8,  8.5, 4.2, 2.5, 1.3]
        _steps_y = [100.0, 92.7, 85.9, 73.4, 61.5, 51.0, 40.8, 31.6, 22.7, 14.2,  6.9, 3.4, 2.0, 0.9]
        _steps_k = [100.0, 93.8, 86.9, 74.8, 63.1, 52.7, 42.3, 33.0, 24.3, 15.9,  8.1, 4.0, 2.4, 1.2]

        def make_steps(c_off: float, m_off: float) -> list[list[float]]:
            rows = []
            for i, _ in enumerate(step_labels):
                if i < len(_steps_c):
                    rows.append([
                        round(_steps_c[i] + c_off, 1),
                        round(_steps_m[i] + m_off, 1),
                        round(_steps_y[i] - c_off * 0.5, 1),
                        round(_steps_k[i] + m_off * 0.5, 1),
                    ])
                else:
                    rows.append([0.0, 0.0, 0.0, 0.0])
            return rows

        shapes = [
            ShapeData(name="HD 16", weights=[
                WeightData(label="120#", density=[2.11, 1.80, 1.66, 1.79], steps=make_steps(0.0,  0.0)),
                WeightData(label="150#", density=[2.08, 1.77, 1.63, 1.75], steps=make_steps(0.3, -0.2)),
                WeightData(label="200#", density=[2.05, 1.74, 1.60, 1.72], steps=make_steps(0.6, -0.4)),
            ]),
        ]

        job = JobConfig(
            customer="Test Customer",
            print_type="CRS",
            stock_desc="XPS",
            finish="CBW SP",
            dot_shape_type="CRS",
            dot_shape_number="01",
            date="24-02-2026",
            set_number="01",
            job_number="J001",
            weight_labels=weight_labels,
            step_labels=step_labels,
            shapes=shapes,
        )
        # fmt: on
        self._populate_from_job(job)
        self._dirty = True
        self._status("Example data loaded")

    def _add_shape(self) -> None:
        self._shape_notebook.add_new_shape()

    def _rename_shape(self) -> None:
        self._shape_notebook.rename_shape(self._shape_notebook.get_selected_index())

    def _remove_shape(self) -> None:
        self._shape_notebook.remove_shape(self._shape_notebook.get_selected_index())

    def _on_weights_changed(self, labels: list[str]) -> None:
        self._shape_notebook.update_weight_labels(labels)
        self._mark_dirty()

    def _on_steps_changed(self, step_labels: list[str]) -> None:
        self._shape_notebook.update_step_labels(step_labels)
        self._mark_dirty()

    def _mark_dirty(self) -> None:
        self._dirty = True

    def _status(self, msg: str) -> None:
        self._status_var.set(f"Status: {msg}")

    def _confirm_discard(self) -> bool:
        return messagebox.askyesno(
            "Unsaved Changes", "Discard unsaved changes?"
        )

    def _on_close(self) -> None:
        # Warn if an export is still running
        self._export_threads = [t for t in self._export_threads if t.is_alive()]
        if self._export_threads:
            if not messagebox.askyesno(
                "Export In Progress",
                "An export is still running. Closing now may produce incomplete files.\n\n"
                "Close anyway?",
            ):
                return
        if self._dirty and not self._confirm_discard():
            return
        self.destroy()

    def _run_in_thread(self, fn, *args) -> None:
        t = threading.Thread(target=fn, args=args, daemon=True)
        self._export_threads.append(t)
        t.start()


# ------------------------------------------------------------------
# Settings dialog
# ------------------------------------------------------------------

class _TemplatesDialog(tk.Toplevel):
    def __init__(self, parent: tk.Widget) -> None:
        super().__init__(parent)
        self.title("Template Paths")
        self.resizable(False, False)
        self.grab_set()

        s = app_settings.load()

        # Standard AI template vars
        self._ai1_std  = tk.StringVar(value=s.get("ai_template_1lpi", ""))
        self._ai2_std  = tk.StringVar(value=s.get("ai_template_2lpi", ""))
        self._ai3_std  = tk.StringVar(value=s.get("ai_template_3lpi", ""))
        # Extended AI template vars
        self._ai1_ext  = tk.StringVar(value=s.get("ai_template_1lpi_extended", ""))
        self._ai2_ext  = tk.StringVar(value=s.get("ai_template_2lpi_extended", ""))
        self._ai3_ext  = tk.StringVar(value=s.get("ai_template_3lpi_extended", ""))

        row = 0

        ttk.Label(self, text="Illustrator — Standard (100→1)", font=("", 9, "bold")).grid(
            row=row, column=0, padx=8, pady=(12, 4), sticky="w"
        )
        row += 1
        for label_text, var in [
            ("1 LPI (.ai):", self._ai1_std),
            ("2 LPI (.ai):", self._ai2_std),
            ("3 LPI (.ai):", self._ai3_std),
        ]:
            ttk.Label(self, text=label_text).grid(row=row, column=0, padx=16, pady=(4, 2), sticky="w")
            row += 1
            ttk.Entry(self, textvariable=var, width=48).grid(row=row, column=0, padx=16, pady=2)
            ttk.Button(self, text="Browse…", command=lambda v=var: self._browse_ai(v)).grid(
                row=row, column=1, padx=4
            )
            row += 1

        ttk.Label(self, text="Illustrator — Extended (100→0.4)", font=("", 9, "bold")).grid(
            row=row, column=0, padx=8, pady=(12, 4), sticky="w"
        )
        row += 1
        for label_text, var in [
            ("1 LPI (.ai):", self._ai1_ext),
            ("2 LPI (.ai):", self._ai2_ext),
            ("3 LPI (.ai):", self._ai3_ext),
        ]:
            ttk.Label(self, text=label_text).grid(row=row, column=0, padx=16, pady=(4, 2), sticky="w")
            row += 1
            ttk.Entry(self, textvariable=var, width=48).grid(row=row, column=0, padx=16, pady=2)
            ttk.Button(self, text="Browse…", command=lambda v=var: self._browse_ai(v)).grid(
                row=row, column=1, padx=4
            )
            row += 1

        ttk.Label(
            self,
            text="Excel templates are selected automatically from assets/\n(template_standard.xlsx or template_extended.xlsx).",
            foreground="grey",
        ).grid(row=row, column=0, columnspan=2, padx=8, pady=(12, 4), sticky="w")
        row += 1

        btn_frame = ttk.Frame(self)
        btn_frame.grid(row=row, column=0, columnspan=2, pady=12)
        ttk.Button(btn_frame, text="Save", command=self._save).pack(side="left", padx=4)
        ttk.Button(btn_frame, text="Cancel", command=self.destroy).pack(side="left", padx=4)

    def _browse_ai(self, var: tk.StringVar) -> None:
        path = filedialog.askopenfilename(
            filetypes=[("Illustrator", "*.ai"), ("All Files", "*.*")]
        )
        if path:
            var.set(path)

    def _save(self) -> None:
        app_settings.set("ai_template_1lpi", self._ai1_std.get())
        app_settings.set("ai_template_2lpi", self._ai2_std.get())
        app_settings.set("ai_template_3lpi", self._ai3_std.get())
        app_settings.set("ai_template_1lpi_extended", self._ai1_ext.get())
        app_settings.set("ai_template_2lpi_extended", self._ai2_ext.get())
        app_settings.set("ai_template_3lpi_extended", self._ai3_ext.get())
        self.destroy()
