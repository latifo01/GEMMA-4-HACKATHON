from typing import Any, Literal

from pydantic import BaseModel, Field


LanguageCode = Literal["auto", "en", "fr", "ar-SD"]
TargetLanguageCode = Literal["en", "fr", "ar-SD"]
ModelModePreference = Literal["auto", "online", "offline"]


class TriageRequest(BaseModel):
    session_id: str | None = None
    transcript: str = Field(min_length=1)
    source_language: LanguageCode = "auto"
    target_language: TargetLanguageCode = "en"
    model_mode: ModelModePreference = "auto"
    patient: dict[str, Any] = Field(default_factory=dict)
    measurements: dict[str, Any] = Field(default_factory=dict)
    context: dict[str, Any] = Field(default_factory=dict)


class TriageResultData(BaseModel):
    session_id: str
    triage_color: str
    classification: str
    human_review_required: bool
    extracted_symptoms: dict[str, Any]
    missing_information: list[str]
    tool_results: list[dict[str, Any]]
    reasoning: str
    recommendations: list[str]
    translated_output: str
    safety_flags: list[str]
    citations: list[dict[str, Any]]
    model: dict[str, Any]
    errors: list[dict[str, Any]] = Field(default_factory=list)
