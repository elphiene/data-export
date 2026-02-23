"""ShapeNotebook — outer tab notebook with one tab per dot shape.

Each shape tab contains an inner weight sub-notebook with one WeightGrid per weight.
"""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk, simpledialog, messagebox
from typing import Callable

from core.models import ShapeData, WeightData, STEP_LABELS_14
from gui.weight_grid import WeightGrid


class _ShapeTab(ttk.Frame):
    """Content of a single shape tab: inner notebook with one WeightGrid per weight."""

    def __init__(
        self,
        parent: tk.Widget,
        shape_data: ShapeData,
        weight_labels: list[str],
        step_labels: list[str] | None = None,
        on_change: Callable[[], None] | None = None,
        **kwargs,
    ) -> None:
        super().__init__(parent, **kwargs)
        self._on_change = on_change
        self._weight_labels = weight_labels
        self._step_labels = step_labels if step_labels is not None else list(STEP_LABELS_14)
        self._grids: list[WeightGrid] = []

        self._notebook = ttk.Notebook(self)
        self._notebook.pack(fill="both", expand=True, padx=4, pady=4)

        self._build_weight_tabs(shape_data, weight_labels, self._step_labels)

    def _build_weight_tabs(
        self,
        shape_data: ShapeData,
        weight_labels: list[str],
        step_labels: list[str],
    ) -> None:
        """Create one sub-tab per weight label, populating from shape_data if available."""
        for child in self._notebook.winfo_children():
            child.destroy()
        self._grids = []

        for i, label in enumerate(weight_labels):
            # Find matching WeightData by position (labels may differ)
            weight_data = shape_data.weights[i] if i < len(shape_data.weights) else None
            if weight_data is None:
                weight_data = WeightData(
                    label=label,
                    density=[0.0, 0.0, 0.0, 0.0],
                    steps=[[0.0, 0.0, 0.0, 0.0] for _ in step_labels],
                )

            container = ttk.Frame(self._notebook)
            container.pack(fill="both", expand=True)

            # Scrollable canvas so tall grids still work at small window sizes
            canvas = tk.Canvas(container, highlightthickness=0)
            scrollbar = ttk.Scrollbar(container, orient="vertical", command=canvas.yview)
            canvas.configure(yscrollcommand=scrollbar.set)
            scrollbar.pack(side="right", fill="y")
            canvas.pack(side="left", fill="both", expand=True)

            inner = ttk.Frame(canvas)
            canvas_window = canvas.create_window((0, 0), window=inner, anchor="nw")

            grid = WeightGrid(
                inner,
                weight_data=weight_data,
                on_change=self._on_change,
                step_labels=step_labels,
                on_complete=lambda i=i: self._advance_weight(i),
            )
            grid.pack(padx=8, pady=8)
            self._grids.append(grid)
            grid._label = label

            def _on_configure(event, c=canvas, cw=canvas_window):
                c.configure(scrollregion=c.bbox("all"))
                c.itemconfig(cw, width=c.winfo_width())

            inner.bind("<Configure>", _on_configure)
            canvas.bind("<Configure>", lambda e, c=canvas, cw=canvas_window:
                        c.itemconfig(cw, width=e.width))

            # Mouse wheel scrolling
            def _on_mousewheel(event, c=canvas):
                c.yview_scroll(int(-1 * (event.delta / 120)), "units")

            canvas.bind("<MouseWheel>", _on_mousewheel)
            inner.bind("<MouseWheel>", _on_mousewheel)

            self._notebook.add(container, text=label)

    def _advance_weight(self, index: int) -> None:
        if index < len(self._grids) - 1:
            self._notebook.select(index + 1)
            self._grids[index + 1].focus_first()
        else:
            # Last weight tab — wrap to C-density of the same grid
            self._grids[index].focus_first()

    def update_weight_labels(
        self,
        shape_data: ShapeData,
        weight_labels: list[str],
        step_labels: list[str] | None = None,
    ) -> None:
        """Rebuild weight sub-tabs when labels change (preserves existing data)."""
        if step_labels is not None:
            self._step_labels = step_labels
        # Gather current data first
        current_weights = self.get_shape_data().weights
        # Patch shape_data with current grid values
        merged_shape = ShapeData(name=shape_data.name, weights=current_weights)
        # Pad with empty weights if new labels added
        while len(merged_shape.weights) < len(weight_labels):
            merged_shape.weights.append(
                WeightData(
                    label=weight_labels[len(merged_shape.weights)],
                    density=[0.0, 0.0, 0.0, 0.0],
                    steps=[[0.0, 0.0, 0.0, 0.0] for _ in self._step_labels],
                )
            )
        self._build_weight_tabs(merged_shape, weight_labels, self._step_labels)

    def get_shape_data(self) -> ShapeData:
        """Collect current values from all weight grids."""
        weights = []
        for i, grid in enumerate(self._grids):
            wd = grid.get_data()
            wd.label = self._weight_labels[i] if i < len(self._weight_labels) else wd.label
            weights.append(wd)
        return ShapeData(name="", weights=weights)  # name set by ShapeNotebook


class ShapeNotebook(ttk.Frame):
    """Outer notebook: one tab per dot shape, with a + button to add more."""

    def __init__(
        self,
        parent: tk.Widget,
        on_change: Callable[[], None] | None = None,
        **kwargs,
    ) -> None:
        super().__init__(parent, **kwargs)
        self._on_change = on_change
        self._weight_labels: list[str] = []
        self._step_labels: list[str] = list(STEP_LABELS_14)
        self._shape_tabs: list[_ShapeTab] = []
        self._shape_names: list[str] = []

        self._notebook = ttk.Notebook(self)
        self._notebook.pack(fill="both", expand=True)

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def add_shape(self, shape_data: ShapeData) -> None:
        """Append a new shape tab populated from shape_data."""
        tab = _ShapeTab(
            self._notebook,
            shape_data=shape_data,
            weight_labels=self._weight_labels,
            step_labels=self._step_labels,
            on_change=self._on_change,
        )
        self._shape_tabs.append(tab)
        self._shape_names.append(shape_data.name)
        self._notebook.add(tab, text=shape_data.name)
        self._notebook.select(tab)

        # Right-click context menu for renaming / removing
        idx = len(self._shape_tabs) - 1
        tab.bind("<Button-3>", lambda e, i=idx: self._shape_context_menu(e, i))

    def add_new_shape(self) -> None:
        """Prompt for a name then add a blank shape tab."""
        name = simpledialog.askstring(
            "New Dot Shape", "Enter dot shape name (e.g. HD 16):", parent=self
        )
        if not name:
            return
        name = name.strip()
        empty = ShapeData(
            name=name,
            weights=[
                WeightData(
                    label=lbl,
                    density=[0.0, 0.0, 0.0, 0.0],
                    steps=[[0.0, 0.0, 0.0, 0.0] for _ in self._step_labels],
                )
                for lbl in self._weight_labels
            ],
        )
        self.add_shape(empty)
        if self._on_change:
            self._on_change()

    def remove_shape(self, index: int) -> None:
        if len(self._shape_tabs) <= 1:
            messagebox.showwarning("Cannot Remove", "A job must have at least one dot shape.")
            return
        tab = self._shape_tabs.pop(index)
        self._shape_names.pop(index)
        self._notebook.forget(tab)
        tab.destroy()
        if self._on_change:
            self._on_change()

    def rename_shape(self, index: int) -> None:
        old_name = self._shape_names[index]
        new_name = simpledialog.askstring(
            "Rename Shape", "New name:", initialvalue=old_name, parent=self
        )
        if not new_name or new_name.strip() == old_name:
            return
        new_name = new_name.strip()
        self._shape_names[index] = new_name
        tab = self._shape_tabs[index]
        self._notebook.tab(tab, text=new_name)
        if self._on_change:
            self._on_change()

    def update_weight_labels(self, weight_labels: list[str]) -> None:
        """Propagate new weight labels to all shape tabs."""
        self._weight_labels = weight_labels
        for tab, name in zip(self._shape_tabs, self._shape_names):
            shape_data = tab.get_shape_data()
            shape_data.name = name
            tab.update_weight_labels(shape_data, weight_labels)

    def update_step_labels(self, step_labels: list[str]) -> None:
        """Propagate new step labels to all shape tabs (rebuilds grids)."""
        self._step_labels = step_labels
        for tab, name in zip(self._shape_tabs, self._shape_names):
            shape_data = tab.get_shape_data()
            shape_data.name = name
            tab.update_weight_labels(shape_data, self._weight_labels, step_labels)

    def get_all_shapes(self) -> list[ShapeData]:
        result = []
        for tab, name in zip(self._shape_tabs, self._shape_names):
            sd = tab.get_shape_data()
            sd.name = name
            result.append(sd)
        return result

    def populate(
        self,
        job_shapes: list[ShapeData],
        weight_labels: list[str],
        step_labels: list[str] | None = None,
    ) -> None:
        """Clear and rebuild all shape tabs from data."""
        # Remove existing tabs
        for tab in list(self._shape_tabs):
            self._notebook.forget(tab)
            tab.destroy()
        self._shape_tabs = []
        self._shape_names = []
        self._weight_labels = weight_labels
        if step_labels is not None:
            self._step_labels = step_labels

        for shape in job_shapes:
            self.add_shape(shape)

    # ------------------------------------------------------------------
    # Context menu
    # ------------------------------------------------------------------

    def _shape_context_menu(self, event: tk.Event, index: int) -> None:
        menu = tk.Menu(self, tearoff=False)
        menu.add_command(label="Rename…", command=lambda: self.rename_shape(index))
        menu.add_command(label="Remove", command=lambda: self.remove_shape(index))
        menu.tk_popup(event.x_root, event.y_root)
