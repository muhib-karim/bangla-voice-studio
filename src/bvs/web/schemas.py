"""Versioned request schemas shared by HTTP and CLI."""

from __future__ import annotations

from typing import Literal, Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

JobKind = Literal["speech", "clone", "transcription", "audiobook", "download"]
JobState = Literal[
    "queued", "running", "cancelling", "succeeded", "failed", "cancelled", "interrupted"
]


class Input(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)


class EmptyInput(Input):
    pass


class NormaliseInput(Input):
    text: str = Field(max_length=1_000_000)

    @field_validator("text")
    @classmethod
    def byte_limit(cls, value: str) -> str:
        if len(value.encode("utf-8")) > 4_000_000:
            raise ValueError("Text exceeds 4 MB UTF-8")
        return value


class Reference(Input):
    upload_id: UUID
    transcript: str = Field(min_length=1, max_length=1000)
    language: Literal["bn", "en"] = "bn"

    @field_validator("transcript")
    @classmethod
    def nonblank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Reference transcript is required")
        return value


class SpeechInput(Input):
    engine_id: str = Field(min_length=1, max_length=80)
    text: str = Field(min_length=1, max_length=10_000)
    language: Literal["bn", "en"] = "bn"
    normalize: bool = True
    reference: Reference | None = None
    voice_description: str | None = Field(default=None, max_length=1000)
    seed: int = Field(default=0, ge=0, le=2**32 - 1, strict=True)
    formats: list[Literal["wav", "mp3"]] = Field(default=["wav"], min_length=1)
    captions: list[Literal["srt", "vtt"]] = Field(default_factory=list)

    @field_validator("text")
    @classmethod
    def nonblank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Text is required")
        return value

    @field_validator("formats", "captions")
    @classmethod
    def deduplicate(cls, value: list[str]) -> list[str]:
        return list(dict.fromkeys(value))


class CloneInput(SpeechInput):
    reference: Reference


class TranscribeInput(Input):
    engine_id: str = "faster-whisper"
    upload_id: UUID
    language: Literal["bn", "en"] | None = "bn"
    word_timestamps: bool = True
    captions: list[Literal["srt", "vtt"]] = Field(default=["srt"])


class BookPreviewInput(Input):
    text: str | None = Field(default=None, max_length=1_000_000)
    upload_id: UUID | None = None
    max_chars: int = Field(default=300, ge=50, le=1000, strict=True)
    normalize: bool = True

    @model_validator(mode="after")
    def source(self) -> Self:
        if (self.text is None) == (self.upload_id is None):
            raise ValueError("Provide exactly one of text or upload_id")
        if self.text is not None and (not self.text.strip() or len(self.text.encode()) > 1_000_000):
            raise ValueError("Book text must be nonblank and at most 1 MB UTF-8")
        return self


class AudiobookInput(BookPreviewInput):
    engine_id: str
    title: str = Field(min_length=1, max_length=200)
    author: str = Field(default="", max_length=200)
    language: Literal["bn", "en"] = "bn"
    reference: Reference | None = None
    voice_description: str | None = Field(default=None, max_length=1000)
    seed: int = Field(default=0, ge=0, le=2**32 - 1, strict=True)
    chapter_pause_ms: int = Field(default=750, ge=0, le=5000, strict=True)
    formats: list[Literal["wav", "mp3", "m4b"]] = Field(default=["wav", "mp3", "m4b"], min_length=1)
    captions: list[Literal["srt", "vtt"]] = Field(default=["srt"])


class DownloadJobInput(Input):
    engine_id: str
    model_id: str
    requested_revision: str | None = None


JobPayload = SpeechInput | CloneInput | TranscribeInput | AudiobookInput | DownloadJobInput
