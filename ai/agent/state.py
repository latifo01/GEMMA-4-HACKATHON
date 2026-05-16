from dataclasses import dataclass, field
from typing import Any


SUPPORTED_LANGUAGES = {"auto", "en", "fr", "ar-SD"}


@dataclass
class TriageInput:
    transcript: str
    source_language: str = "auto"
    target_language: str = "en"
    model_mode: str = "auto"
    patient: dict[str, Any] = field(default_factory=dict)
    measurements: dict[str, Any] = field(default_factory=dict)
    context: dict[str, Any] = field(default_factory=dict)


@dataclass
class TriageState:
    transcript: str
    source_language: str
    target_language: str
    patient: dict[str, Any] = field(default_factory=dict)
    measurements: dict[str, Any] = field(default_factory=dict)
    context: dict[str, Any] = field(default_factory=dict)
    missing_information: list[str] = field(default_factory=list)
    extracted_symptoms: dict[str, Any] = field(default_factory=dict)
    module_hints: list[str] = field(default_factory=list)
    retrieval_query: str = ""
    rag_context: list[dict[str, Any]] = field(default_factory=list)
    tool_results: list[dict[str, Any]] = field(default_factory=list)
    classification: str = "UNCLASSIFIED"
    triage_color: str = "NONE"
    reasoning: str = ""
    recommendations: list[str] = field(default_factory=list)
    translated_output: str = ""
    safety_flags: list[str] = field(default_factory=list)
    citations: list[dict[str, Any]] = field(default_factory=list)
    model: dict[str, Any] = field(default_factory=dict)
    human_review_required: bool = True
    errors: list[dict[str, Any]] = field(default_factory=list)

    def to_result(self) -> dict[str, Any]:
        return {
            "triage_color": self.triage_color,
            "classification": self.classification,
            "human_review_required": self.human_review_required,
            "extracted_symptoms": self.extracted_symptoms,
            "missing_information": self.missing_information,
            "tool_results": self.tool_results,
            "reasoning": self.reasoning,
            "recommendations": self.recommendations,
            "translated_output": self.translated_output,
            "safety_flags": self.safety_flags,
            "citations": self.citations,
            "model": self.model,
            "errors": self.errors,
        }
