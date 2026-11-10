"""LLM-backed engine: map-reduce summaries, validated JSON flashcards and quizzes."""
import json
import math
import re
from typing import Type, TypeVar

from pydantic import BaseModel, ValidationError

from . import prompts
from .llm import LLMClient
from .schemas import Flashcard, QuizQuestion

T = TypeVar("T", bound=BaseModel)
MAX_CHUNKS = 24


def parse_json(raw: str) -> object:
    """Parse model output. Tolerates code fences and text around the JSON."""
    raw = raw.strip()
    raw = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw, flags=re.I)
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        m = re.search(r"[\{\[].*[\}\]]", raw, flags=re.S)
        if not m:
            raise
        return json.loads(m.group(0))


def _even_sample(items: list, k: int) -> list:
    if len(items) <= k:
        return items
    step = len(items) / k
    return [items[int(i * step)] for i in range(k)]


class LLMEngine:
    def __init__(self, client: LLMClient, max_repairs: int = 2):
        self.client = client
        self.name = client.name
        self.max_repairs = max_repairs
        self.warnings: list[str] = []

    # -- core call with validation and repair
    def _ask(self, prompt: str, key: str, model: Type[T] | None) -> list:
        user, last_err = prompt, ""
        for attempt in range(self.max_repairs + 1):
            if last_err:
                user = prompt + "\n\n" + prompts.REPAIR.format(err=last_err)
            raw = self.client.complete(prompts.SYSTEM, user)
            try:
                data = parse_json(raw)
                items = data.get(key) if isinstance(data, dict) else data
                if not isinstance(items, list):
                    raise ValueError(f'expected a JSON list under "{key}"')
            except (ValueError, json.JSONDecodeError) as exc:
                last_err = str(exc)[:200]
                continue
            if model is None:
                good = [str(i).strip() for i in items if str(i).strip()]
            else:
                good = []
                for it in items:
                    try:
                        good.append(model.model_validate(it))
                    except ValidationError as exc:
                        last_err = exc.errors()[0]["msg"]
            if good:
                return good
        self.warnings.append(f"Model output unusable for '{key}' after retries: {last_err}")
        return []

    def _chunks(self, chunks: list[str]) -> list[str]:
        if len(chunks) > MAX_CHUNKS:
            self.warnings.append(
                f"Document is long: using {MAX_CHUNKS} evenly spaced sections out of {len(chunks)}."
            )
            return _even_sample(chunks, MAX_CHUNKS)
        return chunks

    def _per_chunk(self, chunks: list[str], n: int, tmpl: str, key: str, model, extra: int = 1) -> list:
        chunks = self._chunks(chunks)
        per = max(1, math.ceil(n / len(chunks))) + (extra if len(chunks) > 1 else 0)
        out = []
        for c in chunks:
            out += self._ask(tmpl.format(n=per, text=c), key, model)
        return out

    def summarize(self, chunks: list[str], n: int) -> list[str]:
        if len(chunks) == 1:
            return self._ask(prompts.SUMMARY.format(n=n, text=chunks[0]), "bullets", None)[:n]
        partial = self._per_chunk(chunks, n, prompts.SUMMARY, "bullets", None)
        if len(partial) <= n:
            return partial
        joined = "\n".join(f"- {b}" for b in partial)
        merged = self._ask(prompts.SUMMARY_REDUCE.format(n=n, text=joined), "bullets", None)
        return (merged or partial)[:n]

    def flashcards(self, chunks: list[str], n: int) -> list[Flashcard]:
        cards = self._per_chunk(chunks, n, prompts.FLASHCARDS, "flashcards", Flashcard)
        seen, out = set(), []
        for c in cards:
            k = c.front.lower()
            if k not in seen:
                seen.add(k); out.append(c)
        return out[:n]

    def quiz(self, chunks: list[str], n: int) -> list[QuizQuestion]:
        qs = self._per_chunk(chunks, n, prompts.QUIZ, "questions", QuizQuestion)
        seen, out = set(), []
        for q in qs:
            k = q.question.lower()
            if k not in seen:
                seen.add(k); out.append(q)
        return out[:n]
