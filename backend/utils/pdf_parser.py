from __future__ import annotations

from pathlib import Path

from pypdf import PdfReader


def extract_pdf_text(path: str | Path) -> str:
    p = Path(path)
    reader = PdfReader(str(p))
    parts: list[str] = []
    for idx, page in enumerate(reader.pages, start=1):
        txt = page.extract_text() or ""
        txt = txt.replace("\x00", " ").strip()
        if txt:
            parts.append(f"[PAGE {idx}]\n{txt}")
    return "\n\n".join(parts).strip()
