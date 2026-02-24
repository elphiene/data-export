"""Illustrator PDF export.

Flow per dot shape:
1. Chunk the shape's LPIs (weights) into groups of up to 3.
2. For each chunk, pick the matching template (1LPI / 2LPI / 3LPI).
3. Build a placeholder → value dict for the chunk.
4. Render runner.jsx with all values substituted.
5. Write a temp .jsx and call Illustrator.exe in batch mode.
6. After all shapes/chunks, pypdf merges all PDFs into one final file.

Chunking examples:
  1 LPI  → [1LPI template]
  2 LPIs → [2LPI template]
  3 LPIs → [3LPI template]
  5 LPIs → [3LPI, 2LPI]
  7 LPIs → [3LPI, 3LPI, 1LPI]
"""
from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from pathlib import Path

from pypdf import PdfWriter

import settings as app_settings
from core.models import JobConfig, ShapeData, WeightData


# Common Illustrator install paths to probe (Windows)
_ILLUSTRATOR_SEARCH_PATHS = [
    r"C:\Program Files\Adobe\Adobe Illustrator 2025\Support Files\Contents\Windows\Illustrator.exe",
    r"C:\Program Files\Adobe\Adobe Illustrator 2024\Support Files\Contents\Windows\Illustrator.exe",
    r"C:\Program Files\Adobe\Adobe Illustrator 2023\Support Files\Contents\Windows\Illustrator.exe",
    r"C:\Program Files\Adobe\Adobe Illustrator 2022\Support Files\Contents\Windows\Illustrator.exe",
    r"C:\Program Files\Adobe\Adobe Illustrator 2021\Support Files\Contents\Windows\Illustrator.exe",
    r"C:\Program Files\Adobe\Adobe Illustrator CC 2020\Support Files\Contents\Windows\Illustrator.exe",
]


def find_illustrator() -> str | None:
    """Return the path to Illustrator.exe, or None if not found."""
    saved = app_settings.get("illustrator_path")
    if saved and Path(saved).is_file():
        return saved
    for candidate in _ILLUSTRATOR_SEARCH_PATHS:
        if Path(candidate).is_file():
            return candidate
    return None


def _get_lpi_templates(num_steps: int) -> dict[int, str]:
    """Return {1: path, 2: path, 3: path} from settings, choosing standard/extended by step count."""
    suffix = "_extended" if num_steps > 14 else ""
    return {
        1: app_settings.get(f"ai_template_1lpi{suffix}", ""),
        2: app_settings.get(f"ai_template_2lpi{suffix}", ""),
        3: app_settings.get(f"ai_template_3lpi{suffix}", ""),
    }


def _chunk_weights(weights: list[WeightData], size: int = 3) -> list[list[WeightData]]:
    """Split weights into groups of up to `size`."""
    return [weights[i:i + size] for i in range(0, len(weights), size)]


def _build_placeholders(job: JobConfig, shape: ShapeData, chunk: list[WeightData]) -> dict[str, str]:
    """Build the <<PLACEHOLDER>> → value mapping for one chunk of LPIs."""
    heading = " ".join(filter(None, [job.customer, job.print_type, job.stock_desc, job.finish]))
    dot_shape = " ".join(filter(None, [job.dot_shape_type, job.dot_shape_number]))

    ph: dict[str, str] = {
        "<<CUSTOMER>>": heading,
        "<<STOCK>>": "",
        "<<CRS>>": dot_shape,
        "<<DATE>>": job.date,
        "<<SHAPE>>": shape.name,
    }

    colour_suffixes = ["C", "M", "Y", "K"]

    for wi, weight in enumerate(chunk, start=1):
        ph[f"<<W{wi}_LABEL>>"] = weight.label

        # Density row
        for ci, suffix in enumerate(colour_suffixes):
            val = weight.density[ci] if ci < len(weight.density) else 0.0
            ph[f"<<W{wi}_D{suffix}>>"] = _fmt(val)

        # Step rows (R01 … R16)
        for ri, row in enumerate(weight.steps, start=1):
            for ci, suffix in enumerate(colour_suffixes):
                val = row[ci] if ci < len(row) else 0.0
                ph[f"<<W{wi}_R{ri:02d}_{suffix}>>"] = _fmt(val)

    return ph


def _fmt(v: float) -> str:
    """Format a float for insertion into the template (strip trailing zeros)."""
    if v == 0.0:
        return ""
    return f"{v:.4g}"


def _render_jsx(placeholders: dict[str, str], template_ai_path: str, out_pdf_path: str) -> str:
    """Read runner.jsx template and substitute all placeholders + paths."""
    base = Path(sys._MEIPASS) if getattr(sys, "frozen", False) else Path(__file__).parent.parent
    jsx_template_path = base / "assets" / "runner.jsx"
    jsx_source = jsx_template_path.read_text(encoding="utf-8")

    # Substitute data placeholders (<<...>>)
    for key, value in placeholders.items():
        jsx_source = jsx_source.replace(key, value)

    # Substitute path tokens — ExtendScript File() requires forward slashes on Windows
    # Escape backslashes first (for any remaining), then double-quotes for JSX string safety
    def _jsx_escape(p: str) -> str:
        return p.replace("\\", "/").replace('"', '\\"')

    jsx_source = jsx_source.replace("<<TEMPLATE_PATH>>", _jsx_escape(template_ai_path))
    jsx_source = jsx_source.replace("<<OUTPUT_PDF>>", _jsx_escape(out_pdf_path))

    return jsx_source


def export_pdf(job: JobConfig, output_path: str) -> None:
    """Export all shapes as PDFs (chunked by LPI count) and merge into output_path."""
    illustrator_exe = find_illustrator()
    if illustrator_exe is None:
        raise RuntimeError(
            "Illustrator.exe not found. Please set the path in Settings."
        )

    num_steps = len(job.step_labels)
    lpi_templates = _get_lpi_templates(num_steps)
    missing = [n for n in (1, 2, 3) if not lpi_templates[n] or not Path(lpi_templates[n]).is_file()]
    if missing:
        raise RuntimeError(
            f"Missing Illustrator template(s) for {', '.join(str(n) for n in missing)} LPI. "
            "Please set all three template paths in Settings."
        )

    all_pdfs: list[str] = []

    with tempfile.TemporaryDirectory() as tmp_dir:
        for shape in job.shapes:
            chunks = _chunk_weights(shape.weights)

            for chunk_idx, chunk in enumerate(chunks):
                template_path = lpi_templates[len(chunk)]
                safe_name = "".join(
                    c if c.isalnum() or c in "-_ " else "_" for c in shape.name
                )
                out_pdf = os.path.join(tmp_dir, f"{safe_name}_chunk{chunk_idx}.pdf")

                placeholders = _build_placeholders(job, shape, chunk)
                jsx_source = _render_jsx(placeholders, template_path, out_pdf)

                jsx_path = os.path.join(tmp_dir, f"{safe_name}_chunk{chunk_idx}.jsx")
                with open(jsx_path, "w", encoding="utf-8") as f:
                    f.write(jsx_source)

                try:
                    result = subprocess.run(
                        [illustrator_exe, "/b", jsx_path],
                        timeout=120,
                        capture_output=True,
                        text=True,
                    )
                except subprocess.TimeoutExpired:
                    raise RuntimeError(
                        f"Illustrator timed out after 120 seconds "
                        f"for shape '{shape.name}' chunk {chunk_idx + 1}. "
                        "The script may be waiting for user input — check Illustrator."
                    )
                if result.returncode != 0:
                    detail = result.stderr.strip() if result.stderr else ""
                    msg = (
                        f"Illustrator returned exit code {result.returncode} "
                        f"for shape '{shape.name}' chunk {chunk_idx + 1}"
                    )
                    if detail:
                        msg += f"\n{detail}"
                    raise RuntimeError(msg)

                if not Path(out_pdf).is_file():
                    raise RuntimeError(
                        f"Illustrator did not produce a PDF for shape '{shape.name}' "
                        f"chunk {chunk_idx + 1}"
                    )

                all_pdfs.append(out_pdf)

        # Merge all PDFs
        writer = PdfWriter()
        for pdf_path in all_pdfs:
            writer.append(pdf_path)

        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "wb") as f:
            writer.write(f)
