import argparse
import sys
from pathlib import Path

from .config import Settings
from .export import to_anki_tsv, to_json, to_markdown
from .generate import MODES, run
from .ingest import IngestError, load_path
from .llm import LLMError


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="studykit", description="Make study material from a PDF or text file.")
    p.add_argument("file")
    p.add_argument("-m", "--mode", choices=MODES, default="all")
    p.add_argument("-n", type=int, default=10, help="items per type (1-50)")
    p.add_argument("-f", "--format", choices=("md", "json", "anki"), default="md")
    p.add_argument("-o", "--out", help="write to this file instead of the screen")
    p.add_argument("--backend", choices=("extractive", "ollama", "openai"))
    p.add_argument("--model")
    a = p.parse_args(argv)

    s = Settings.from_env()
    if a.backend or a.model:
        s = Settings(**{**s.__dict__, **({"backend": a.backend} if a.backend else {}),
                        **({"model": a.model} if a.model else {})})
    try:
        text = load_path(a.file)
        res = run(text, a.mode, a.n, s, source=Path(a.file).name)
    except (IngestError, LLMError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    out = {"md": to_markdown, "json": to_json, "anki": to_anki_tsv}[a.format](res)
    if a.out:
        Path(a.out).write_text(out, encoding="utf-8")
        print(f"Wrote {a.out}", file=sys.stderr)
    else:
        print(out)
    for w in res.warnings:
        print(f"warning: {w}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
