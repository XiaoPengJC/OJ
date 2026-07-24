from typing import Literal

from pydantic import BaseModel, field_validator

from app.config import MAX_SOURCE_SIZE


class SubmissionCreateRequest(BaseModel):
    problem_id: str
    language: Literal["python"]
    source_code: str

    @field_validator("problem_id")
    @classmethod
    def validate_problem_id(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("problem_id cannot be empty")
        return value

    @field_validator("source_code")
    @classmethod
    def validate_source_code(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("source_code cannot be empty")
        if len(value.encode("utf-8")) > MAX_SOURCE_SIZE:
            raise ValueError("source_code must not exceed 64 KiB")
        return value
