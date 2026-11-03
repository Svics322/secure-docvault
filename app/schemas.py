from __future__ import annotations

from pydantic import BaseModel, Field


class UserRegister(BaseModel):
    # Обмеження та формати перевіряються у сервісі, щоб клієнт
    # отримував усі локалізовані помилки одним пакетом.
    username: str
    email: str
    password: str


class UserLogin(BaseModel):
    username: str
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str | None = Field(default=None, max_length=4096)


class DocumentComment(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    comment: str = Field(min_length=1, max_length=4000)
