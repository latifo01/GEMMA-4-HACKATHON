from typing import Literal

from pydantic import BaseModel, Field


LanguageCode = Literal["auto", "en", "fr", "ar-SD"]


class AudioSegment(BaseModel):
    start_seconds: float = Field(ge=0)
    end_seconds: float = Field(ge=0)
    text: str


class AudioTranscriptionData(BaseModel):
    transcript: str
    detected_language: str
    duration_seconds: float = Field(ge=0)
    segments: list[AudioSegment] = Field(default_factory=list)
