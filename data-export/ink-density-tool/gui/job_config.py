"""JobConfigPanel — left panel with job metadata and weight label management."""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Callable

from core.models import JobConfig, STEP_LABELS_14, STEP_LABELS_16

_PRINT_TYPES = ["CRS", "QUA"]
_FINISHES = ["RP", "SP", "CBW SP"]
_DOT_SHAPE_TYPES = ["CRS", "CRY", "HD", "ESXR"]


class JobConfigPanel(ttk.Frame):
    """Left panel: job metadata + editable weight label chips."""

    def __init__(
        self,
        parent: tk.Widget,
        on_weights_changed: Callable[[list[str]], None] | None = None,
        on_steps_changed: Callable[[list[str]], None] | None = None,
        **kwargs,
    ) -> None:
        super().__init__(parent, **kwargs)
        self._on_weights_changed = on_weights_changed
        self._on_steps_changed = on_steps_changed
        self._weight_vars: list[tk.StringVar] = []
        self._steps_var = tk.StringVar(value="14")

        self._build()

    # ------------------------------------------------------------------
    # Build
    # ------------------------------------------------------------------

    def _build(self) -> None:
        pad = {"padx": 8, "pady": 3}

        ttk.Label(self, text="Job Configuration", font=("", 10, "bold")).pack(
            anchor="w", padx=8, pady=(10, 6)
        )

        # Customer
        self._customer_var = tk.StringVar()
        ttk.Label(self, text="Customer:", anchor="w").pack(fill="x", **pad)
        ttk.Entry(self, textvariable=self._customer_var).pack(fill="x", **pad)

        # Heading: print type (CRS/QUA) + stock description + finish (RP/SP/CBW SP)
        ttk.Label(self, text="Heading:", anchor="w").pack(fill="x", **pad)
        heading_frame = ttk.Frame(self)
        heading_frame.pack(fill="x", padx=8, pady=3)

        self._print_type_var = tk.StringVar(value="CRS")
        ttk.Combobox(
            heading_frame,
            textvariable=self._print_type_var,
            values=_PRINT_TYPES,
            state="readonly",
            width=5,
        ).pack(side="left", padx=(0, 4))

        self._stock_desc_var = tk.StringVar()
        ttk.Entry(heading_frame, textvariable=self._stock_desc_var, width=8).pack(
            side="left", padx=(0, 4)
        )

        self._finish_var = tk.StringVar(value="RP")
        ttk.Combobox(
            heading_frame,
            textvariable=self._finish_var,
            values=_FINISHES,
            state="readonly",
            width=7,
        ).pack(side="left")

        # Dot shape: type (CRS/CRY/HD/ESXR) + number
        ttk.Label(self, text="Dot Shape:", anchor="w").pack(fill="x", **pad)
        dot_frame = ttk.Frame(self)
        dot_frame.pack(fill="x", padx=8, pady=3)

        self._dot_shape_type_var = tk.StringVar(value="CRS")
        ttk.Combobox(
            dot_frame,
            textvariable=self._dot_shape_type_var,
            values=_DOT_SHAPE_TYPES,
            state="readonly",
            width=6,
        ).pack(side="left", padx=(0, 4))

        self._dot_shape_number_var = tk.StringVar()
        ttk.Entry(dot_frame, textvariable=self._dot_shape_number_var, width=6).pack(side="left")

        # Date
        self._date_var = tk.StringVar()
        ttk.Label(self, text="Date:", anchor="w").pack(fill="x", **pad)
        ttk.Entry(self, textvariable=self._date_var).pack(fill="x", **pad)

        # Set Number / Job Number
        sj_frame = ttk.Frame(self)
        sj_frame.pack(fill="x", padx=8, pady=3)

        set_col = ttk.Frame(sj_frame)
        set_col.pack(side="left", fill="x", expand=True, padx=(0, 4))
        ttk.Label(set_col, text="Set #:", anchor="w").pack(fill="x")
        self._set_number_var = tk.StringVar()
        ttk.Entry(set_col, textvariable=self._set_number_var).pack(fill="x")

        job_col = ttk.Frame(sj_frame)
        job_col.pack(side="left", fill="x", expand=True)
        ttk.Label(job_col, text="Job #:", anchor="w").pack(fill="x")
        self._job_number_var = tk.StringVar()
        ttk.Entry(job_col, textvariable=self._job_number_var).pack(fill="x")

        ttk.Separator(self, orient="horizontal").pack(fill="x", padx=8, pady=8)

        # Weights
        ttk.Label(self, text="LPIs:", anchor="w").pack(fill="x", padx=8)
        self._weight_frame = ttk.Frame(self)
        self._weight_frame.pack(fill="x", padx=8, pady=4)
        self._rebuild_weight_chips([])

        ttk.Separator(self, orient="horizontal").pack(fill="x", padx=8, pady=8)

        # Step preset radio buttons
        ttk.Label(self, text="Steps:", anchor="w").pack(fill="x", padx=8)
        steps_frame = ttk.Frame(self)
        steps_frame.pack(fill="x", padx=8, pady=4)

        ttk.Radiobutton(
            steps_frame,
            text="Standard (100\u21921)",
            variable=self._steps_var,
            value="14",
            command=self._notify_steps_changed,
        ).pack(anchor="w")
        ttk.Radiobutton(
            steps_frame,
            text="Extended (100\u21920.4)",
            variable=self._steps_var,
            value="16",
            command=self._notify_steps_changed,
        ).pack(anchor="w")

    def _rebuild_weight_chips(self, labels: list[str]) -> None:
        for child in self._weight_frame.winfo_children():
            child.destroy()
        self._weight_vars = []

        for i, label in enumerate(labels):
            self._add_chip_row(i, label)

        ttk.Button(
            self._weight_frame,
            text="+ Add LPI",
            command=self._add_weight,
            width=14,
        ).pack(anchor="w", pady=(4, 0))

    def _add_chip_row(self, index: int, label: str) -> None:
        var = tk.StringVar(value=label)
        self._weight_vars.append(var)

        row = ttk.Frame(self._weight_frame)
        row.pack(fill="x", pady=2)

        entry = ttk.Entry(row, textvariable=var, width=8)
        entry.pack(side="left")
        entry.bind("<FocusOut>", lambda e: self._notify_weights_changed())

        def remove(idx=index):
            self._remove_weight(idx)

        ttk.Button(row, text="×", width=2, command=remove).pack(side="left", padx=(4, 0))

    # ------------------------------------------------------------------
    # Weight management
    # ------------------------------------------------------------------

    def _add_weight(self) -> None:
        current = self.get_weight_labels()
        current.append(f"LPI{len(current) + 1}")
        self._rebuild_weight_chips(current)
        self._notify_weights_changed()

    def _remove_weight(self, index: int) -> None:
        current = self.get_weight_labels()
        if len(current) <= 1:
            return
        current.pop(index)
        self._rebuild_weight_chips(current)
        self._notify_weights_changed()

    def _notify_weights_changed(self) -> None:
        if self._on_weights_changed:
            self._on_weights_changed(self.get_weight_labels())

    def _notify_steps_changed(self) -> None:
        if self._on_steps_changed:
            self._on_steps_changed(self.get_step_labels())

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def get_weight_labels(self) -> list[str]:
        return [v.get().strip() or f"LPI{i+1}" for i, v in enumerate(self._weight_vars)]

    def get_step_labels(self) -> list[str]:
        return list(STEP_LABELS_16) if self._steps_var.get() == "16" else list(STEP_LABELS_14)

    def get_metadata(self) -> dict[str, str]:
        return {
            "customer": self._customer_var.get(),
            "print_type": self._print_type_var.get(),
            "stock_desc": self._stock_desc_var.get(),
            "finish": self._finish_var.get(),
            "dot_shape_type": self._dot_shape_type_var.get(),
            "dot_shape_number": self._dot_shape_number_var.get(),
            "date": self._date_var.get(),
            "set_number": self._set_number_var.get(),
            "job_number": self._job_number_var.get(),
        }

    def populate(self, job: JobConfig) -> None:
        self._customer_var.set(job.customer)
        self._print_type_var.set(job.print_type)
        self._stock_desc_var.set(job.stock_desc)
        self._finish_var.set(job.finish)
        self._dot_shape_type_var.set(job.dot_shape_type)
        self._dot_shape_number_var.set(job.dot_shape_number)
        self._date_var.set(job.date)
        self._set_number_var.set(job.set_number)
        self._job_number_var.set(job.job_number)
        self._rebuild_weight_chips(job.weight_labels)
        self._steps_var.set("16" if len(job.step_labels) == 16 else "14")
