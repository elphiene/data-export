"""LibreOffice PDF export backend — Linux/Debian substitute for Illustrator.

Uses LibreOffice's UNO API to open each .ai template, replace <<PLACEHOLDER>>
text in every draw object (including nested groups), and export to PDF.

Requirements (Debian/Ubuntu):
    sudo apt install libreoffice python3-uno

The .ai template files are the same files used on Windows — LibreOffice Draw
opens them and exposes their text frames through the UNO Draw API.
"""
from __future__ import annotations

import os
import subprocess
import tempfile
import time
from pathlib import Path

from pypdf import PdfWriter

import settings as app_settings
from core.models import JobConfig
from export.illustrator import _build_placeholders, _chunk_weights


_LO_PORT = 2002
_LO_RETRIES = 12       # × _LO_WAIT seconds max startup wait
_LO_WAIT = 1.0


# ---------------------------------------------------------------------------
# Discovery
# ---------------------------------------------------------------------------

def find_libreoffice() -> str | None:
    """Return the libreoffice/soffice executable path, or None."""
    saved = app_settings.get("libreoffice_path", "")
    if saved and Path(saved).is_file():
        return saved
    for name in ("libreoffice", "soffice"):
        r = subprocess.run(["which", name], capture_output=True, text=True)
        if r.returncode == 0:
            path = r.stdout.strip()
            if path:
                return path
    return None


def _get_lpi_templates(num_steps: int) -> dict[int, str]:
    suffix = "_extended" if num_steps > 14 else ""
    return {
        1: app_settings.get(f"ai_template_1lpi{suffix}", ""),
        2: app_settings.get(f"ai_template_2lpi{suffix}", ""),
        3: app_settings.get(f"ai_template_3lpi{suffix}", ""),
    }


# ---------------------------------------------------------------------------
# UNO session
# ---------------------------------------------------------------------------

class _LoSession:
    """Manages a headless LibreOffice process and UNO desktop connection."""

    def __init__(self, lo_exe: str) -> None:
        self._proc = subprocess.Popen(
            [
                lo_exe,
                "--headless",
                "--norestore",
                "--nofirststartwizard",
                f"--accept=socket,host=localhost,port={_LO_PORT};"
                "urp;StarOffice.ServiceManager",
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        self._desktop = self._connect()

    def _connect(self):
        import uno
        local_ctx = uno.getComponentContext()
        resolver = local_ctx.ServiceManager.createInstanceWithContext(
            "com.sun.star.bridge.UnoUrlResolver", local_ctx
        )
        url = (
            f"uno:socket,host=localhost,port={_LO_PORT};"
            "urp;StarOffice.ComponentContext"
        )
        last_exc: Exception | None = None
        for _ in range(_LO_RETRIES):
            try:
                ctx = resolver.resolve(url)
                smgr = ctx.ServiceManager
                return smgr.createInstanceWithContext("com.sun.star.frame.Desktop", ctx)
            except Exception as exc:
                last_exc = exc
                time.sleep(_LO_WAIT)
        raise RuntimeError(
            f"Could not connect to LibreOffice after {_LO_RETRIES} attempts.\n"
            f"Last error: {last_exc}\n"
            "Is another LibreOffice already running on the same port?"
        )

    def process_template(
        self,
        template_path: str,
        placeholders: dict[str, str],
        out_pdf: str,
    ) -> None:
        import uno
        template_url = uno.systemPathToFileUrl(os.path.abspath(template_path))
        props = (
            _prop("Hidden", True),
            _prop("AsTemplate", True),   # open as copy — never modifies the master
        )
        doc = self._desktop.loadComponentFromURL(template_url, "_blank", 0, props)
        try:
            _replace_all(doc, placeholders)
            _export_pdf(doc, out_pdf)
        finally:
            doc.close(False)

    def close(self) -> None:
        try:
            self._proc.terminate()
            self._proc.wait(timeout=10)
        except Exception:
            pass


# ---------------------------------------------------------------------------
# UNO helpers
# ---------------------------------------------------------------------------

def _prop(name: str, value):
    from com.sun.star.beans import PropertyValue
    p = PropertyValue()
    p.Name = name
    p.Value = value
    return p


def _replace_all(doc, placeholders: dict[str, str]) -> None:
    """Replace every placeholder across all text frames, including nested groups.

    Uses LibreOffice's built-in Find & Replace (preserves character formatting).
    Falls back to recursive shape traversal for any that weren't reached.
    """
    search = doc.createSearchDescriptor()
    search.SearchRegularExpression = False
    for key, value in placeholders.items():
        if not key:
            continue
        search.SearchString = key
        search.ReplaceString = value
        doc.replaceAll(search)

    # Belt-and-braces: also walk every draw shape recursively so text inside
    # groups on locked or hidden layers is caught.
    pages = doc.DrawPages
    for pi in range(pages.Count):
        _replace_in_container(pages.getByIndex(pi), placeholders)


def _replace_in_container(container, placeholders: dict[str, str]) -> None:
    """Recursively walk draw shapes and replace placeholder text."""
    for i in range(container.Count):
        shape = container.getByIndex(i)
        # Recurse into groups
        if hasattr(shape, "Count"):
            _replace_in_container(shape, placeholders)
        # Text-bearing shapes
        if shape.supportsService("com.sun.star.drawing.Text"):
            text_obj = shape.getText()
            content = text_obj.getString()
            new_content = content
            for key, value in placeholders.items():
                if key:
                    new_content = new_content.replace(key, value)
            if new_content != content:
                text_obj.setString(new_content)


def _export_pdf(doc, out_pdf: str) -> None:
    import uno
    out_url = uno.systemPathToFileUrl(os.path.abspath(out_pdf))
    doc.storeToURL(out_url, (_prop("FilterName", "draw_pdf_Export"),))


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def export_pdf(job: JobConfig, output_path: str) -> None:
    """Export all shapes as PDFs via LibreOffice and merge into output_path."""
    lo_exe = find_libreoffice()
    if lo_exe is None:
        raise RuntimeError(
            "LibreOffice not found.\n"
            "Install with:  sudo apt install libreoffice python3-uno"
        )

    try:
        import uno  # noqa: F401
    except ImportError:
        raise RuntimeError(
            "python3-uno not installed.\n"
            "Install with:  sudo apt install python3-uno\n"
            "Then restart the app with the system Python (not a virtualenv)."
        )

    num_steps = len(job.step_labels)
    lpi_templates = _get_lpi_templates(num_steps)
    missing = [n for n in (1, 2, 3) if not lpi_templates[n] or not Path(lpi_templates[n]).is_file()]
    if missing:
        raise RuntimeError(
            f"Missing template(s) for {', '.join(str(n) for n in missing)} LPI. "
            "Please set all three template paths in Settings."
        )

    if not job.shapes:
        raise RuntimeError("No shapes to export.")
    for shape in job.shapes:
        if not shape.weights:
            raise RuntimeError(f"Shape '{shape.name}' has no LPIs. Add at least one before exporting.")

    session = _LoSession(lo_exe)
    try:
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
                    session.process_template(template_path, placeholders, out_pdf)

                    if not Path(out_pdf).is_file():
                        raise RuntimeError(
                            f"LibreOffice did not produce a PDF for shape "
                            f"'{shape.name}' chunk {chunk_idx + 1}"
                        )
                    all_pdfs.append(out_pdf)

            writer = PdfWriter()
            for pdf_path in all_pdfs:
                writer.append(pdf_path)

            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, "wb") as f:
                writer.write(f)
    finally:
        session.close()
