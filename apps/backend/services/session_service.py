from typing import Any
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.backend.models import TriageSession
from apps.backend.schemas.session import SessionRecord, SessionStatus


class SessionNotFoundError(Exception):
    def __init__(self, session_id: str) -> None:
        super().__init__(f"Session not found: {session_id}")
        self.session_id = session_id


async def create_session(
    db_session: AsyncSession,
    request_payload: dict[str, Any],
    session_id: str | None = None,
    model_mode: str | None = None,
) -> TriageSession:
    audit_session = TriageSession(
        session_id=session_id or str(uuid4()),
        status="running",
        model_mode=model_mode,
        request_json=request_payload,
        result_json=None,
        errors_json=[],
    )

    db_session.add(audit_session)
    await db_session.commit()
    await db_session.refresh(audit_session)
    return audit_session


async def get_session(db_session: AsyncSession, session_id: str) -> TriageSession:
    result = await db_session.execute(
        select(TriageSession).where(TriageSession.session_id == session_id)
    )
    audit_session = result.scalar_one_or_none()
    if audit_session is None:
        raise SessionNotFoundError(session_id)
    return audit_session


async def update_session(
    db_session: AsyncSession,
    session_id: str,
    status: SessionStatus | None = None,
    result_payload: dict[str, Any] | None = None,
    errors: list[dict[str, Any]] | None = None,
    model_mode: str | None = None,
) -> TriageSession:
    audit_session = await get_session(db_session, session_id)

    if status is not None:
        audit_session.status = status
    if result_payload is not None:
        audit_session.result_json = result_payload
    if errors is not None:
        audit_session.errors_json = errors
    if model_mode is not None:
        audit_session.model_mode = model_mode

    await db_session.commit()
    await db_session.refresh(audit_session)
    return audit_session


def serialize_session(audit_session: TriageSession) -> dict[str, Any]:
    record = SessionRecord.model_validate(audit_session)
    return record.model_dump(mode="json")

