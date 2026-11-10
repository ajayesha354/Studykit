import re


def split_sentences(text: str) -> list[str]:
    parts = re.split(r"(?<=[.!?])\s+(?=[A-Z0-9\"'(])", text.replace("\n", " "))
    return [p.strip() for p in parts if p.strip()]


def chunk_text(text: str, max_chars: int = 6000) -> list[str]:
    """Pack paragraphs into chunks of at most max_chars. Long paragraphs are split by sentence."""
    units: list[str] = []
    for para in re.split(r"\n\s*\n", text):
        para = para.strip()
        if not para:
            continue
        if len(para) <= max_chars:
            units.append(para)
            continue
        buf = ""
        for s in split_sentences(para):
            while len(s) > max_chars:                      # no punctuation at all
                units.append(s[:max_chars]); s = s[max_chars:]
            if len(buf) + len(s) + 1 > max_chars and buf:
                units.append(buf); buf = s
            else:
                buf = f"{buf} {s}".strip()
        if buf:
            units.append(buf)
    chunks, cur = [], ""
    for u in units:
        if cur and len(cur) + len(u) + 2 > max_chars:
            chunks.append(cur); cur = u
        else:
            cur = f"{cur}\n\n{u}" if cur else u
    if cur:
        chunks.append(cur)
    return chunks
