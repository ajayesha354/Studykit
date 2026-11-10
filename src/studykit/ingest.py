"""Read PDF / text input and return clean text."""
import io
import re
from pathlib import Path


class IngestError(ValueError):
    pass


def clean_text(text: str) -> str:
    text = text.replace("\x00", " ").replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"(\w)-\n(\w)", r"\1\2", text)          # join hyphenated line breaks
    text = re.sub(r"(?<![.!?:\n])\n(?!\n)", " ", text)     # unwrap hard-wrapped lines
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _read_pdf(data: bytes) -> str:
    from pypdf import PdfReader

    try:
        reader = PdfReader(io.BytesIO(data))
        if reader.is_encrypted:
            try:
                reader.decrypt("")
            except Exception:
                raise IngestError("The PDF is password protected.")
        pages = [(p.extract_text() or "") for p in reader.pages]
    except IngestError:
        raise
    except Exception as exc:
        raise IngestError(f"Could not read the PDF: {exc}") from exc
    return "\n\n".join(pages)


def load_bytes(data: bytes, filename: str) -> str:
    ext = Path(filename).suffix.lower()
    if ext == ".pdf" or data[:5] == b"%PDF-":
        raw = _read_pdf(data)
    elif ext in {".txt", ".md", ".text", ""}:
        raw = data.decode("utf-8", errors="replace")
    else:
        raise IngestError(f"Unsupported file type '{ext}'. Use PDF, TXT or MD.")
    text = clean_text(raw)
    if len(text) < 50:
        raise IngestError(
            "Almost no text found. If this is a scanned PDF, run OCR first (for example ocrmypdf)."
        )
    return text


def load_path(path: str) -> str:
    p = Path(path)
    if not p.is_file():
        raise IngestError(f"File not found: {path}")
    return load_bytes(p.read_bytes(), p.name)
