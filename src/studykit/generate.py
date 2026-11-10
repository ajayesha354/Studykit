from .chunking import chunk_text
from .config import Settings
from .extractive import ExtractiveEngine
from .llm import LLMError, make_client
from .llm_engine import LLMEngine
from .schemas import Result

MODES = ("summary", "flashcards", "quiz", "all")


def make_engine(s: Settings):
    if s.backend == "extractive":
        return ExtractiveEngine()
    return LLMEngine(make_client(s))


def run(text: str, mode: str = "all", n: int = 10, settings: Settings | None = None,
        engine=None, source: str = "") -> Result:
    if mode not in MODES:
        raise ValueError(f"mode must be one of {MODES}")
    if not 1 <= n <= 50:
        raise ValueError("n must be between 1 and 50")
    s = settings or Settings.from_env()
    engine = engine or make_engine(s)
    chunks = chunk_text(text, s.chunk_chars)
    res = Result(source=source, backend=engine.name)
    if mode in ("summary", "all"):
        res.summary = engine.summarize(chunks, n)
    if mode in ("flashcards", "all"):
        res.flashcards = engine.flashcards(chunks, n)
    if mode in ("quiz", "all"):
        res.quiz = engine.quiz(chunks, n)
    res.warnings = list(getattr(engine, "warnings", []))
    wanted = {"summary": res.summary, "flashcards": res.flashcards, "quiz": res.quiz}
    for k, v in wanted.items():
        if mode in (k, "all") and not v:
            res.warnings.append(f"No {k} could be generated from this text.")
    return res
