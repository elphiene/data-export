"""WeightGrid — data entry grid for one weight table.

Layout:
       C       M       Y       K
D   [2.11]  [1.80]  [1.66]  [1.79]
100 [    ]  [    ]  [    ]  [    ]
 95 [    ]  [    ]  [    ]  [    ]
 ...
  1 [    ]  [    ]  [    ]  [    ]
"""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Callable

from core.models import WeightData, STEP_LABELS_14, COLOUR_NAMES


class WeightGrid(ttk.Frame):
    """A grid widget for entering density + step readings for one weight."""

    def __init__(
        self,
        parent: tk.Widget,
        weight_data: WeightData | None = None,
        on_change: Callable[[], None] | None = None,
        step_labels: list[str] | None = None,
        on_complete: Callable[[], None] | None = None,
        **kwargs,
    ) -> None:
        super().__init__(parent, **kwargs)
        self._on_change = on_change
        self._on_complete = on_complete
        self._step_labels = step_labels if step_labels is not None else list(STEP_LABELS_14)
        self._entries: list[list[tk.Entry]] = []  # [row][col], row 0 = density row
        self._vars: list[list[tk.StringVar]] = []

        self._build()
        if weight_data is not None:
            self.set_data(weight_data)

    # ------------------------------------------------------------------
    # Build
    # ------------------------------------------------------------------

    def _build(self) -> None:
        # Column header row
        ttk.Label(self, text="", width=5).grid(row=0, column=0, padx=(0, 4))
        for col, name in enumerate(COLOUR_NAMES):
            ttk.Label(self, text=name, anchor="center", width=8).grid(
                row=0, column=col + 1, padx=2
            )

        # Density row (row index 1 in grid, row 0 in data)
        ttk.Label(self, text="D", anchor="e", width=5).grid(
            row=1, column=0, padx=(0, 4), pady=(2, 4)
        )
        density_row_entries = []
        density_row_vars = []
        for col in range(4):
            var = tk.StringVar()
            var.trace_add("write", self._make_trace(0, col, var))
            entry = self._make_entry(var, row=1, col=col + 1, pady=(2, 4))
            density_row_entries.append(entry)
            density_row_vars.append(var)
        self._entries.append(density_row_entries)
        self._vars.append(density_row_vars)

        # Step rows
        for step_idx, label in enumerate(self._step_labels):
            grid_row = step_idx + 2
            ttk.Label(self, text=label, anchor="e", width=5).grid(
                row=grid_row, column=0, padx=(0, 4), pady=1
            )
            row_entries = []
            row_vars = []
            for col in range(4):
                var = tk.StringVar()
                var.trace_add("write", self._make_trace(step_idx + 1, col, var))
                entry = self._make_entry(var, row=grid_row, col=col + 1, pady=1)
                row_entries.append(entry)
                row_vars.append(var)
            self._entries.append(row_entries)
            self._vars.append(row_vars)

        self._setup_tab_order()
        self._lock_100_row()

    def _make_entry(
        self, var: tk.StringVar, row: int, col: int, pady: int | tuple = 1
    ) -> tk.Entry:
        vcmd = (self.register(self._validate_numeric), "%P")
        entry = tk.Entry(
            self,
            textvariable=var,
            width=7,
            justify="center",
            validate="key",
            validatecommand=vcmd,
        )
        entry.grid(row=row, column=col, padx=2, pady=pady, sticky="ew")
        default_bg = entry.cget("background")
        entry.bind("<FocusIn>",  lambda e, w=entry: w.config(background="#fffacd"))
        entry.bind("<FocusOut>", lambda e, w=entry, bg=default_bg: w.config(background=bg))
        return entry

    def _lock_100_row(self) -> None:
        """Lock the 100% step row: always shows 100, disabled, skipped by Tab."""
        for col in range(4):
            self._vars[1][col].set("100")
            self._entries[1][col].config(state="disabled")

    def _setup_tab_order(self) -> None:
        """Bind Tab/Shift-Tab column-major: all rows for C, then M, then Y, then K.

        Row 1 (the 100% step) is locked and excluded — Tab goes density → 95 → …
        Return is bound identically to Tab for DataCatcher compatibility.
        """
        def _make_tab_handler(target):
            def handler(event):
                target.focus_set()
                return "break"
            return handler

        num_rows = len(self._entries)
        num_cols = 4
        # Row 1 is the 100% step — locked, excluded from Tab order
        flat = [
            self._entries[row][col]
            for col in range(num_cols)
            for row in range(num_rows)
            if row != 1
        ]
        self._flat_order = flat
        self._flat_index = {id(e): i for i, e in enumerate(flat)}

        for i, entry in enumerate(flat):
            prev_entry = flat[i - 1] if i > 0 else flat[-1]

            if i == len(flat) - 1 and self._on_complete:
                entry.bind("<Tab>", lambda e: self._on_complete() or "break")
                entry.bind("<Return>", lambda e: self._on_complete() or "break")
            else:
                next_entry = flat[(i + 1) % len(flat)]
                entry.bind("<Tab>", _make_tab_handler(next_entry))
                entry.bind("<Return>", _make_tab_handler(next_entry))

            entry.bind("<Shift-Tab>", _make_tab_handler(prev_entry))

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    @staticmethod
    def _validate_numeric(value: str) -> bool:
        """Allow empty string, digits, one dot, optional leading minus."""
        if value == "" or value == "-":
            return True
        try:
            float(value)
            return True
        except ValueError:
            # Allow partial float like "2." during typing
            if value.count(".") == 1 and value.replace(".", "").replace("-", "").isdigit():
                return True
            return False

    def _make_trace(self, row: int, col: int, var: tk.StringVar):
        def _trace(*_):
            if self._on_change:
                self._on_change()
            # Auto-advance when value settles — handles DataCatcher injection
            # regardless of whether it sends Tab, Return, or neither.
            # Only fires when this entry actually has focus (not during load/clear).
            entry = self._entries[row][col]
            try:
                if entry.focus_get() is entry:
                    self._schedule_settle_advance(row, col)
            except Exception:
                pass
        return _trace

    def _schedule_settle_advance(self, row: int, col: int) -> None:
        """(Re)schedule a 300 ms settle timer; fires _settle_advance if still focused."""
        entry = self._entries[row][col]
        # Don't schedule for the locked 100% row
        if str(entry.cget("state")) == "disabled":
            return
        after_id = getattr(entry, "_settle_id", None)
        if after_id is not None:
            try:
                entry.after_cancel(after_id)
            except Exception:
                pass
        entry._settle_id = entry.after(300, lambda: self._settle_advance(row, col))

    def _settle_advance(self, row: int, col: int) -> None:
        """Advance focus to the next entry if this one is still focused and non-empty."""
        entry = self._entries[row][col]
        entry._settle_id = None
        try:
            if entry.focus_get() is not entry:
                return
        except Exception:
            return
        if not self._vars[row][col].get():
            return
        idx = getattr(self, "_flat_index", {}).get(id(entry))
        if idx is None:
            return
        flat = self._flat_order
        if idx == len(flat) - 1 and self._on_complete:
            self._on_complete()
        elif idx < len(flat) - 1:
            flat[idx + 1].focus_set()

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def get_data(self) -> WeightData:
        """Read current entry values into a WeightData."""
        label = getattr(self, "_label", "")
        num_steps = len(self._step_labels)

        def parse(v: str) -> float:
            try:
                return float(v)
            except ValueError:
                return 0.0

        density = [parse(self._vars[0][col].get()) for col in range(4)]
        steps = [
            [parse(self._vars[row + 1][col].get()) for col in range(4)]
            for row in range(num_steps)
        ]
        return WeightData(label=label, density=density, steps=steps)

    def set_data(self, weight_data: WeightData) -> None:
        """Populate grid from a WeightData object."""
        self._label = weight_data.label
        num_steps = len(self._step_labels)

        def fmt(v: float) -> str:
            return "" if v == 0.0 else str(v)

        for col in range(4):
            self._vars[0][col].set(fmt(weight_data.density[col]))

        for row in range(num_steps):
            for col in range(4):
                v = weight_data.steps[row][col] if row < len(weight_data.steps) else 0.0
                self._vars[row + 1][col].set(fmt(v))
        self._lock_100_row()

    def clear(self) -> None:
        """Clear all entries."""
        for row_vars in self._vars:
            for var in row_vars:
                var.set("")
        self._lock_100_row()

    def focus_first(self) -> None:
        """Focus the first entry (top-left)."""
        self._entries[0][0].focus_set()
