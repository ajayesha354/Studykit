import csv
import io

from .schemas import Result


def to_markdown(r: Result) -> str:
    out = [f"# Study pack: {r.source or 'document'}", ""]
    if r.summary:
        out += ["## Summary", *[f"- {b}" for b in r.summary], ""]
    if r.flashcards:
        out += ["## Flashcards", ""]
        for i, c in enumerate(r.flashcards, 1):
            out += [f"**{i}. {c.front}**", f"Answer: {c.back}", ""]
    if r.quiz:
        out += ["## Quiz", ""]
        for i, q in enumerate(r.quiz, 1):
            out.append(f"**{i}. {q.question}**")
            out += [f"   {'ABCD'[j]}. {o}" for j, o in enumerate(q.options)]
            out += [f"   Answer: {'ABCD'[q.answer_index]}. {q.explanation}".rstrip(), ""]
    if r.warnings:
        out += ["## Notes", *[f"- {w}" for w in r.warnings]]
    return "\n".join(out).rstrip() + "\n"


def to_anki_tsv(r: Result) -> str:
    """Tab-separated front/back, importable in Anki (File > Import)."""
    buf = io.StringIO()
    w = csv.writer(buf, delimiter="\t", lineterminator="\n")
    for c in r.flashcards:
        w.writerow([c.front, c.back])
    return buf.getvalue()


def to_json(r: Result) -> str:
    return r.model_dump_json(indent=2)
