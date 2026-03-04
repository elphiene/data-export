# DataCatcher Integration & Tab Order Brief

## Context

This is a Windows desktop app (tkinter, Python) for recording CMYK ink density readings from an X-Rite eXact Gen 1 spectrodensitometer. The tool is documented in `PLAN.md`.

---

## What is DataCatcher

DataCatcher is a free official X-Rite utility that connects to the eXact via USB. When a scan is taken on the device, DataCatcher intercepts the reading and injects it into whatever field is currently focused on the PC — exactly like a keyboard typing the value. It requires no API, no serial port code, and no changes to the receiving application. From tkinter's perspective, DataCatcher is indistinguishable from a user typing a number and pressing Tab.

**Download source:** `xrite.com/service-support/product-support/portable-spectrophotometers/exact`

Required downloads — install in this order:

1. eXact Driver DLL v3.5.10
2. DataCatcher for PC v1.3.3816

DataCatcher is configured to send a Tab keystroke after each value, which advances focus to the next field automatically.

---

## How DataCatcher Links to This Project

No integration code is needed. The workflow is:

1. User opens the app and navigates to the correct weight tab
2. User clicks the first Entry field (top of C column)
3. User scans on the eXact → DataCatcher types the value into the focused field and sends Tab
4. Focus moves to the next field automatically
5. User scans again → repeat until all fields are filled

The only requirement is that the Tab order in `weight_grid.py` matches the physical scan order from the device.

---

## Required Tab Order Change

### Current (default tkinter behaviour)

Tab moves **left to right** across a row: C → M → Y → K, then down to the next row.

### Required (to match scan order)

Tab moves **down each column**: all of C top-to-bottom, then all of M top-to-bottom, then Y, then K.

**Example for a single weight tab (15 rows × 4 columns):**

```
Tab sequence: C-density → C-100 → C-95 → ... → C-1 → M-density → M-100 → ... → K-1
Shift+Tab reverses this exactly.
Last cell (K row 14) wraps back to first cell (C density) of same weight tab.
```

### Implementation

Do not rely on default tkinter Tab order (which follows widget creation order). After creating all Entry widgets for a weight tab, store them in a 2D list `entries[row][col]` and apply a custom Tab binding:

```python
def make_tab_handler(target):
    def handler(event):
        target.focus_set()
        return 'break'  # Prevents tkinter default Tab handling
    return handler

def set_column_major_tab_order(entries):
    rows = len(entries)
    cols = len(entries[0])

    # Flatten into column-major order
    ordered = [entries[row][col] for col in range(cols) for row in range(rows)]

    for i, widget in enumerate(ordered):
        next_widget = ordered[(i + 1) % len(ordered)]
        prev_widget = ordered[i - 1]
        widget.bind('<Tab>', make_tab_handler(next_widget))
        widget.bind('<Shift-Tab>', make_tab_handler(prev_widget))
```

Call `set_column_major_tab_order(entries)` once per weight tab, after all Entry widgets are created.

---

## Validation Compatibility Warning

`weight_grid.py` uses numeric-only input validation. Ensure the `validatecommand` does not block programmatic input — DataCatcher injects values the same way paste does. Use `validate='key'` with `%P` (proposed value) rather than character-by-character rejection. Test by pasting `2.11` into a field; if it accepts it, DataCatcher will work.

---

## Recommended Implementation Approach

Follow the order in `PLAN.md` unchanged. The only additions are:

- In **step 3** (`gui/weight_grid.py`): implement the column-major Tab order using the approach above from the start. Do not build row-major first and refactor later.
- In **step 3** also: validate that pasting a decimal value into any Entry field works correctly before moving on.

No new dependencies, no new files, no architecture changes. DataCatcher operates entirely outside the application.

---

## Summary of Changes to PLAN.md

| Area | Change |
|---|---|
| New dependency | None |
| New files | None |
| Architecture | None |
| `weight_grid.py` | Implement column-major Tab order from the start |
| `weight_grid.py` | Confirm paste/programmatic input works with numeric validator |
| Hardware setup | Install eXact driver + DataCatcher before testing |
