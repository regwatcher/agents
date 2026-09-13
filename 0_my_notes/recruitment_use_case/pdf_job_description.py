"""Convert uploaded PDF job descriptions to Markdown (text extraction)."""

from __future__ import annotations

from pathlib import Path

from pypdf import PdfReader


def pdf_to_markdown(pdf_path: str | Path, *, page_separator: str = "\n\n---\n\n") -> str:
    """
    Extract text from each page and wrap as Markdown.

    Many PDFs only yield plain text (no real structure); headings are added per page
    for readability. Image-only PDFs may produce little or no text.
    """
    path = Path(pdf_path)
    if not path.is_file():
        raise FileNotFoundError(f"PDF not found: {path}")

    reader = PdfReader(str(path), strict=False)

    if getattr(reader, "is_encrypted", False):
        try:
            reader.decrypt("")
        except Exception:
            pass
        if reader.is_encrypted:
            raise ValueError(
                "This PDF is encrypted. Remove the password or decrypt it, then upload again."
            )

    chunks: list[str] = []
    for i, page in enumerate(reader.pages):
        raw = page.extract_text()
        text = (raw or "").strip()
        if text:
            chunks.append(f"## Page {i + 1}\n\n{text}")

    body = page_separator.join(chunks)
    if not body.strip():
        return (
            f"# Job description (imported from `{path.name}`)\n\n"
            "> **No extractable text** was found. The PDF may be image-only, scanned without OCR, "
            "or use fonts/layouts that block extraction. Try a text-based PDF or paste the JD manually.\n"
        )

    return (
        f"# Job description (imported from `{path.name}`)\n\n"
        "_Converted automatically from PDF; you may want to edit formatting._\n\n"
        + body
    )
