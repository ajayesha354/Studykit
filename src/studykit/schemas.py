from pydantic import BaseModel, Field, field_validator, model_validator


class Flashcard(BaseModel):
    front: str = Field(min_length=3)
    back: str = Field(min_length=1)

    @field_validator("front", "back")
    @classmethod
    def _strip(cls, v: str) -> str:
        return v.strip()


class QuizQuestion(BaseModel):
    question: str = Field(min_length=5)
    options: list[str]
    answer_index: int
    explanation: str = ""

    @field_validator("options")
    @classmethod
    def _opts(cls, v: list[str]) -> list[str]:
        v = [str(o).strip() for o in v]
        if len(v) != 4 or len({o.lower() for o in v}) != 4 or any(not o for o in v):
            raise ValueError("need exactly 4 distinct non-empty options")
        return v

    @model_validator(mode="after")
    def _ans(self):
        if not 0 <= self.answer_index < len(self.options):
            raise ValueError("answer_index out of range")
        return self


class Result(BaseModel):
    source: str = ""
    backend: str = ""
    summary: list[str] = []
    flashcards: list[Flashcard] = []
    quiz: list[QuizQuestion] = []
    warnings: list[str] = []
