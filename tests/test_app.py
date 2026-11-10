import json
from fastapi.testclient import TestClient

from studykit.api import create_app
from studykit.cli import main
from studykit.config import Settings


def client(**kw):
    return TestClient(create_app(Settings(**kw)))


def test_health_and_index():
    c = client()
    assert c.get("/health").json()["status"] == "ok"
    assert "StudyKit" in c.get("/").text


def test_generate_pdf(pdf_bytes):
    r = client().post("/api/generate", files={"file": ("n.pdf", pdf_bytes)}, data={"mode": "all", "n": "3"})
    j = r.json()
    assert r.status_code == 200 and j["summary"] and j["flashcards"] and j["quiz"]


def test_generate_errors(pdf_bytes):
    c = client(max_upload_mb=1)
    assert c.post("/api/generate", files={"file": ("a.txt", b"short")}).status_code == 400
    assert c.post("/api/generate", files={"file": ("a.pdf", pdf_bytes)}, data={"mode": "x"}).status_code == 422
    assert c.post("/api/generate", files={"file": ("a.pdf", pdf_bytes)}, data={"n": "99"}).status_code == 422
    assert c.post("/api/generate", files={"file": ("a.txt", b"a" * 1_100_000)}).status_code == 413


def test_llm_down_gives_502(text):
    c = client(backend="ollama", base_url="http://127.0.0.1:9")
    r = c.post("/api/generate", files={"file": ("a.txt", text.encode())}, data={"mode": "summary"})
    assert r.status_code == 502 and "Cannot reach" in r.json()["detail"]


def test_export(text):
    c = client()
    j = c.post("/api/generate", files={"file": ("a.txt", text.encode())}, data={"n": "2"}).json()
    assert "## Quiz" in c.post("/api/export/md", json=j).text
    assert "\t" in c.post("/api/export/anki", json=j).text
    assert c.post("/api/export/pdf", json=j).status_code == 404


def test_cli(tmp_path, text, capsys):
    f = tmp_path / "a.txt"; f.write_text(text)
    out = tmp_path / "o.json"
    assert main([str(f), "-f", "json", "-n", "2", "-o", str(out)]) == 0
    assert json.loads(out.read_text())["summary"]
    assert main([str(tmp_path / "missing.pdf")]) == 1
    assert "error:" in capsys.readouterr().err
