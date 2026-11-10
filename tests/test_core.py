import json
import httpx
import pytest

from studykit.chunking import chunk_text
from studykit.config import Settings
from studykit.extractive import ExtractiveEngine
from studykit.generate import run
from studykit.ingest import IngestError, clean_text, load_bytes
from studykit.llm import LLMError, OllamaClient, OpenAICompatClient
from studykit.llm_engine import LLMEngine, parse_json
from studykit.schemas import QuizQuestion


# ---------- ingest
def test_pdf_and_txt(pdf_bytes, text):
    assert "Calvin cycle" in load_bytes(pdf_bytes, "a.pdf")
    assert "Mitochondria" in load_bytes(text.encode(), "a.txt")


def test_ingest_errors():
    with pytest.raises(IngestError):
        load_bytes(b"hi", "a.txt")                      # too short
    with pytest.raises(IngestError):
        load_bytes(b"x" * 100, "a.docx")                # unsupported
    with pytest.raises(IngestError):
        load_bytes(b"%PDF-1.4 garbage", "a.pdf")        # corrupt


def test_clean_text():
    assert clean_text("photo-\nsynthesis is\nnice.") == "photosynthesis is nice."


# ---------- chunking
def test_chunking_respects_limit(text):
    chunks = chunk_text(text * 5, 500)
    assert len(chunks) > 1 and all(len(c) <= 500 for c in chunks)


def test_chunking_no_punctuation():
    assert all(len(c) <= 100 for c in chunk_text("word " * 500, 100))


# ---------- JSON parsing
def test_parse_json_variants():
    assert parse_json('```json\n{"a":1}\n```') == {"a": 1}
    assert parse_json('Sure! {"a": [1,2]} hope it helps') == {"a": [1, 2]}
    with pytest.raises(ValueError):
        parse_json("no json here")


# ---------- schema
def test_quiz_schema_rejects_bad():
    with pytest.raises(ValueError):
        QuizQuestion(question="Which one?", options=["a", "a", "b", "c"], answer_index=0)
    with pytest.raises(ValueError):
        QuizQuestion(question="Which one?", options=["a", "b", "c", "d"], answer_index=4)


# ---------- LLM engine with a fake client
class Fake:
    name = "fake"

    def __init__(self, replies):
        self.replies, self.calls = list(replies), []

    def complete(self, system, user):
        self.calls.append(user)
        return self.replies.pop(0) if self.replies else "{}"


GOOD_QUIZ = {"questions": [{"question": "What does Rubisco do?", "options": ["fixes carbon", "makes ATP", "splits water", "copies DNA"], "answer_index": 0, "explanation": "Carbon fixation."}]}


def test_engine_repairs_bad_json(text):
    fake = Fake(["not json at all", json.dumps({"bullets": ["Plants make glucose.", "Cells burn glucose."]})])
    out = LLMEngine(fake).summarize([text], 2)
    assert out == ["Plants make glucose.", "Cells burn glucose."]
    assert "invalid" in fake.calls[1]                       # repair prompt was sent


def test_engine_drops_invalid_items_keeps_valid(text):
    bad = {"questions": [{"question": "Broken?", "options": ["a", "b"], "answer_index": 0}] + GOOD_QUIZ["questions"]}
    qs = LLMEngine(Fake([json.dumps(bad)])).quiz([text], 5)
    assert len(qs) == 1 and qs[0].answer_index == 0


def test_engine_gives_warning_when_hopeless(text):
    eng = LLMEngine(Fake(["x"] * 10))
    assert eng.flashcards([text], 3) == [] and eng.warnings


def test_map_reduce_and_dedupe():
    chunks = ["alpha " * 10, "beta " * 10, "gamma " * 10]
    fake = Fake([json.dumps({"bullets": [f"b{i}a", f"b{i}b"]}) for i in range(3)]
                + [json.dumps({"bullets": ["merged1", "merged2"]})])
    assert LLMEngine(fake).summarize(chunks, 2) == ["merged1", "merged2"]
    dup = {"flashcards": [{"front": "What is ATP?", "back": "Energy"}, {"front": "what is atp?", "back": "Energy"}]}
    assert len(LLMEngine(Fake([json.dumps(dup)])).flashcards(["x"], 5)) == 1


# ---------- HTTP clients (mocked servers)
def _client(cls, handler, **kw):
    c = cls(Settings(backend=kw.get("b", "openai"), base_url="http://x", api_key="k"))
    c.http = httpx.Client(transport=httpx.MockTransport(handler))
    return c


def test_openai_client_and_retry(monkeypatch):
    monkeypatch.setattr("time.sleep", lambda *_: None)
    n = {"c": 0}

    def h(req):
        n["c"] += 1
        if n["c"] == 1:
            return httpx.Response(503, text="busy")
        assert req.url.path == "/chat/completions"
        return httpx.Response(200, json={"choices": [{"message": {"content": "{}"}}]})

    assert _client(OpenAICompatClient, h).complete("s", "u") == "{}" and n["c"] == 2


def test_ollama_client():
    h = lambda req: httpx.Response(200, json={"message": {"content": '{"ok":1}'}})
    assert _client(OllamaClient, h, b="ollama").complete("s", "u") == '{"ok":1}'


def test_server_down_message():
    def h(req):
        raise httpx.ConnectError("refused")
    with pytest.raises(LLMError, match="Cannot reach"):
        _client(OllamaClient, h, b="ollama").complete("s", "u")


# ---------- extractive engine and orchestration
def test_extractive_outputs_are_valid(text):
    r = run(text, "all", 4, Settings(backend="extractive"))
    assert r.summary and r.flashcards and r.quiz and not r.warnings
    for q in r.quiz:
        assert q.options[q.answer_index].lower() in q.explanation.lower()
    assert all("_____" in c.front for c in r.flashcards)


def test_extractive_is_deterministic(text):
    a = run(text, "quiz", 3, Settings()).model_dump()
    b = run(text, "quiz", 3, Settings()).model_dump()
    assert a == b


def test_run_validates_args(text):
    with pytest.raises(ValueError):
        run(text, "bogus")
    with pytest.raises(ValueError):
        run(text, "quiz", 0)
