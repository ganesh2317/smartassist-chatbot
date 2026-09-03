import re
from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator

from app.config import get_settings

settings = get_settings()


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=settings.max_message_chars)
    conversation_id: Optional[str] = None

    @field_validator("message")
    @classmethod
    def message_must_not_be_blank(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Please enter a message.")
        return cleaned

    @field_validator("conversation_id")
    @classmethod
    def empty_conversation_id(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None


class SourceReference(BaseModel):
    document_id: str
    name: str
    excerpt: str


class ChatResponse(BaseModel):
    reply: str
    source: Literal["predefined", "ai", "rag", "fallback"]
    conversation_id: str
    sources: list[SourceReference] = Field(default_factory=list)


class HealthResponse(BaseModel):
    status: str
    service: str
    database: str
    ai_configured: bool
    version: str


class AuthRequest(BaseModel):
    username: str = Field(..., min_length=1)
    password: str = Field(..., min_length=1)

    @field_validator("username")
    @classmethod
    def username_must_be_valid(cls, value: str) -> str:
        cleaned = value.strip().lower()
        if len(cleaned) < 3:
            raise ValueError("Username must be at least 3 characters.")
        if len(cleaned) > 32:
            raise ValueError("Username must be at most 32 characters.")
        if not re.fullmatch(r"[a-z0-9_]+", cleaned):
            raise ValueError("Username can only use letters, numbers, and underscores.")
        return cleaned

    @field_validator("password")
    @classmethod
    def password_must_be_valid(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("Please enter a password.")
        if len(value) < 8:
            raise ValueError("Password must be at least 8 characters.")
        if len(value.encode("utf-8")) > 256:
            raise ValueError("Password is too long.")
        return value


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    username: str


class UserResponse(BaseModel):
    username: str


class ConversationSummary(BaseModel):
    id: str
    title: str
    created_at: str
    updated_at: str


class ChatMessage(BaseModel):
    role: Literal["user", "bot"]
    content: str
    timestamp: str


class ConversationDetail(BaseModel):
    id: str
    title: str
    created_at: str
    updated_at: str
    messages: list[ChatMessage]


class DocumentSummary(BaseModel):
    id: str
    name: str
    mime_type: str
    size_bytes: int
    char_count: int
    chunk_count: int
    created_at: str


class DeleteResponse(BaseModel):
    ok: bool
