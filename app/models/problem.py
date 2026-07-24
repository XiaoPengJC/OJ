import re
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator


class Sample(BaseModel):
    input: str
    output: str


class TestCase(BaseModel):
    case_id: str = Field(min_length=1, max_length=64)
    input: str
    output: str
    score: int = Field(ge=0)
    is_hidden: bool

    @field_validator("case_id")
    @classmethod
    def normalize_case_id(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("case_id cannot be empty")
        return normalized


class ProblemCreateRequest(BaseModel):
    id: str = Field(min_length=1, max_length=32)
    title: str = Field(min_length=1, max_length=100)
    description: str = Field(min_length=1)
    input_description: str = Field(min_length=1)
    output_description: str = Field(min_length=1)
    samples: list[Sample] = Field(min_length=1)
    constraints: str
    time_limit: float = Field(gt=0)
    memory_limit: int = Field(gt=0)
    difficulty: Literal["easy", "medium", "hard"]
    tags: list[str] = Field(default_factory=list)
    test_cases: list[TestCase] = Field(min_length=1)

    @field_validator(
        "title",
        "description",
        "input_description",
        "output_description",
    )
    @classmethod
    def reject_blank_text(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("field cannot be blank")
        return value

    @field_validator("tags")
    @classmethod
    def normalize_tags(cls, value: list[str]) -> list[str]:
        return [tag.strip() for tag in value if tag.strip()]

    @model_validator(mode="after")
    def validate_problem(self):
        if re.fullmatch(r"[A-Za-z0-9_-]+", self.id) is None:
            raise ValueError("id may only contain letters, digits, underscores, and hyphens")

        case_ids = [case.case_id for case in self.test_cases]
        if len(case_ids) != len(set(case_ids)):
            raise ValueError("case_id values must be unique within a problem")

        if sum(case.score for case in self.test_cases) != 100:
            raise ValueError("test case scores must total 100")

        return self
