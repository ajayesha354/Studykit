# StudyKit

Upload a PDF or text file. Get bullet-point summaries, flashcards and multiple-choice quizzes.
Runs fully offline, with a local model (Ollama), or with any OpenAI-compatible API.

## Backends

| Backend | Setting | Use it for |
|---|---|---|
| `extractive` (default) | none | Offline, instant, no model. Fill-in-the-blank cards and quizzes built from the document's own sentences. Basic quality. |
| `ollama` | `STUDYKIT_MODEL=llama3.2:3b` | Local, private. Real questions and abstractive summaries. |
| `openai` | `STUDYKIT_BASE_URL`, `STUDYKIT_API_KEY`, `STUDYKIT_MODEL` | OpenAI, Groq, Together, OpenRouter, vLLM, llama.cpp server, LM Studio. |

## Quick start

```bash
pip install -e ".[dev]"
cp .env.example .env            # edit the backend settings, then: export $(grep -v '^#' .env | xargs)

studykit notes.pdf -m all -n 8                       # print Markdown
studykit notes.pdf -m flashcards -f anki -o cards.tsv   # import into Anki
studykit notes.pdf -f json -o pack.json --backend ollama --model llama3.2:3b

uvicorn studykit.api:app --port 8000                 # web UI at http://localhost:8000
```

Local model: `ollama pull llama3.2:3b`, then `STUDYKIT_BACKEND=ollama`.
Docker: `docker compose up --build` (reads `.env`).

## API

- `GET /health`
- `POST /api/generate` multipart: `file`, `mode` (summary|flashcards|quiz|all), `n` (1-50). Returns JSON.
- `POST /api/export/{md|anki}` with the JSON result as body.

## How it works

1. **Ingest**: pypdf text extraction, de-hyphenation, line unwrapping. Clear errors for scanned, encrypted or corrupt PDFs.
2. **Chunk**: paragraph-aware chunks (`STUDYKIT_CHUNK_CHARS`, default 6000). Documents over 24 chunks are sampled evenly, with a warning.
3. **Generate**: summaries use map-reduce (per-chunk bullets, then a merge pass). Cards and quizzes are requested per chunk.
4. **Validate**: every item is checked with Pydantic (4 distinct options, valid answer index). Bad JSON triggers up to 2 repair retries that include the error. Invalid items are dropped, duplicates removed.
5. **Export**: Markdown, JSON, Anki TSV.

## Limits

- No OCR. Scanned PDFs need `ocrmypdf` first.
- Small local models may write weaker or occasionally wrong questions. Check the output before studying from it.
- The extractive backend cannot write real questions, so its distractors can be weak.
- Uploads are processed in memory and not stored. There is no auth or rate limiting, so put it behind a proxy before exposing it publicly.

## Tests

`pytest` runs 23 tests: ingest, chunking, JSON repair, schema checks, retry logic, both HTTP clients (mocked), the API and the CLI.

## Browser-only website

`docs/index.html` is a single-file website that runs entirely in the browser (offline engine, no server).
Host it free with GitHub Pages: Settings > Pages > Deploy from a branch > `main` / `/docs`.
