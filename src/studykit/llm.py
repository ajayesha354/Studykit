"""Thin LLM clients. One interface: complete(system, user) -> str.

Ollama covers local models. The OpenAI-compatible client covers OpenAI, Groq, Together,
OpenRouter, vLLM, llama.cpp server and LM Studio, since they share the same chat API.
"""
import time
from typing import Protocol

import httpx

from .config import Settings


class LLMError(RuntimeError):
    pass


class LLMClient(Protocol):
    name: str

    def complete(self, system: str, user: str) -> str: ...


def _post(client: httpx.Client, url: str, retries: int = 3, **kw) -> dict:
    last: Exception | None = None
    for attempt in range(retries):
        try:
            r = client.post(url, **kw)
            if r.status_code in (429, 500, 502, 503, 504):
                raise LLMError(f"HTTP {r.status_code}: {r.text[:200]}")
            r.raise_for_status()
            return r.json()
        except httpx.ConnectError as exc:
            raise LLMError(f"Cannot reach the model server at {url}. Is it running?") from exc
        except (httpx.HTTPError, LLMError) as exc:
            last = exc
            time.sleep(min(2 ** attempt, 8) * 0.5)
    raise LLMError(f"LLM request failed after {retries} tries: {last}")


class OllamaClient:
    name = "ollama"

    def __init__(self, s: Settings):
        self.s = s
        self.http = httpx.Client(timeout=s.timeout)

    def complete(self, system: str, user: str) -> str:
        data = _post(
            self.http,
            f"{self.s.base_url}/api/chat",
            json={
                "model": self.s.model,
                "stream": False,
                "format": "json",
                "options": {"temperature": 0.2},
                "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
            },
        )
        try:
            return data["message"]["content"]
        except KeyError as exc:
            raise LLMError(f"Unexpected Ollama response: {str(data)[:200]}") from exc


class OpenAICompatClient:
    name = "openai"

    def __init__(self, s: Settings):
        self.s = s
        headers = {"Authorization": f"Bearer {s.api_key}"} if s.api_key else {}
        self.http = httpx.Client(timeout=s.timeout, headers=headers)

    def complete(self, system: str, user: str) -> str:
        body = {
            "model": self.s.model,
            "temperature": 0.2,
            "response_format": {"type": "json_object"},
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
        }
        data = _post(self.http, f"{self.s.base_url}/chat/completions", json=body)
        try:
            return data["choices"][0]["message"]["content"]
        except (KeyError, IndexError) as exc:
            raise LLMError(f"Unexpected API response: {str(data)[:200]}") from exc


def make_client(s: Settings) -> LLMClient:
    if s.backend == "ollama":
        return OllamaClient(s)
    if s.backend == "openai":
        return OpenAICompatClient(s)
    raise LLMError(f"'{s.backend}' is not an LLM backend")
