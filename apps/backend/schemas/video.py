from pydantic import BaseModel, Field


class VideoAnalysisData(BaseModel):
    respiratory_rate_bpm: float | None = Field(default=None, ge=0)
    confidence: float = Field(ge=0, le=1)
    frames_analyzed: int = Field(ge=0)
    duration_seconds: float = Field(ge=0)
    quality_flags: list[str] = Field(default_factory=list)
    notes: str
