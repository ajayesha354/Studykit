import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    backend: str = "extractive"
    model: str = "llama3.2:3b"
    base_url: str = "http://localhost:11434"
    api_key: str = ""
    chunk_chars: int = 6000
    max_upload_mb: int = 10
    timeout: float = 120.0

    @classmethod
    def from_env(cls) -> "Settings":
        e = os.environ.get
        return cls(
            backend=e("STUDYKIT_BACKEND", cls.backend).lower(),
            model=e("STUDYKIT_MODEL", cls.model),
            base_url=e("STUDYKIT_BASE_URL", cls.base_url).rstrip("/"),
            api_key=e("STUDYKIT_API_KEY", cls.api_key),
            chunk_chars=int(e("STUDYKIT_CHUNK_CHARS", cls.chunk_chars)),
            max_upload_mb=int(e("STUDYKIT_MAX_UPLOAD_MB", cls.max_upload_mb)),
        )
