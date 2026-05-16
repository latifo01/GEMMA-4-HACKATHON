from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


SessionStatus = Literal["running", "completed", "failed"]


class SessionRecord(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    session_id: str
    status: SessionStatus
    model_mode: str | None
    request: dict[str, Any] = Field(validation_alias="request_json")
    result: dict[str, Any] | None = Field(validation_alias="result_json")
    errors: list[dict[str, Any]] = Field(validation_alias="errors_json")
    created_at: datetime
    updated_at: datetime


class SessionResponseData(BaseModel):
    session_id: str
    status: SessionStatus
    created_at: datetime
    updated_at: datetime
    model_mode: str | None
    request: dict[str, Any]
    result: dict[str, Any] | None
    errors: list[dict[str, Any]]

