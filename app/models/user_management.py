from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator


class UserCreateRequest(BaseModel):
    username: str = Field(min_length=3, max_length=32)
    password: str = Field(min_length=8)
    role: Literal["student", "teacher", "admin"]

    @field_validator("username")
    @classmethod
    def normalize_username(cls, value: str) -> str:
        normalized = value.strip()
        if len(normalized) < 3:
            raise ValueError("username must contain at least 3 non-space characters")
        return normalized


class UserUpdateRequest(BaseModel):
    role: Literal["student", "teacher", "admin"] | None = None
    is_active: bool | None = None

    @model_validator(mode="after")
    def require_at_least_one_field(self):
        if self.role is None and self.is_active is None:
            raise ValueError("at least one field must be provided")
        return self
