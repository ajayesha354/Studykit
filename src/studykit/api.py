from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, PlainTextResponse

from . import __version__
from .config import Settings
from .export import to_anki_tsv, to_markdown
from .generate import MODES, run
from .ingest import IngestError, load_bytes
from .llm import LLMError
from .schemas import Result

STATIC = Path(__file__).parent / "static"


def create_app(settings: Settings | None = None) -> FastAPI:
    s = settings or Settings.from_env()
    app = FastAPI(title="StudyKit", version=__version__)

    @app.get("/health")
    def health():
        return {"status": "ok", "version": __version__, "backend": s.backend, "model": s.model}

    @app.get("/")
    def index():
        return FileResponse(STATIC / "index.html")

    # Sync endpoint: FastAPI runs it in a worker thread, so slow LLM calls do not block the server.
    @app.post("/api/generate", response_model=Result)
    async def generate(file: UploadFile = File(...), mode: str = Form("all"), n: int = Form(10)):
        if mode not in MODES:
            raise HTTPException(422, f"mode must be one of {MODES}")
        if not 1 <= n <= 50:
            raise HTTPException(422, "n must be between 1 and 50")
        limit = s.max_upload_mb * 1024 * 1024
        data = await file.read(limit + 1)
        if len(data) > limit:
            raise HTTPException(413, f"File is larger than {s.max_upload_mb} MB.")
        return await _work(data, file.filename or "upload.txt", mode, n, s)

    @app.post("/api/export/{fmt}", response_class=PlainTextResponse)
    def export(fmt: str, result: Result):
        if fmt == "md":
            return to_markdown(result)
        if fmt == "anki":
            return to_anki_tsv(result)
        raise HTTPException(404, "format must be md or anki")

    return app


async def _work(data: bytes, name: str, mode: str, n: int, s: Settings) -> Result:
    from starlette.concurrency import run_in_threadpool

    def job() -> Result:
        text = load_bytes(data, name)
        return run(text, mode, n, s, source=name)

    try:
        return await run_in_threadpool(job)
    except IngestError as exc:
        raise HTTPException(400, str(exc))
    except LLMError as exc:
        raise HTTPException(502, str(exc))


app = create_app()
