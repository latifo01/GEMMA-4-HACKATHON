from time import perf_counter
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from ai.agent.graph import AgentPipeline
from ai.agent.state import TriageInput
from ai.llm.router import LLMRouter, ModelUnavailableError
from ai.rag.vectorstore import build_vector_store
from apps.backend.config import Settings, get_settings
from apps.backend.database import get_db_session
from apps.backend.schemas.triage import TriageRequest, TriageResultData
from apps.backend.services.session_service import create_session, update_session


router = APIRouter(prefix="/triage", tags=["triage"])


def get_agent_pipeline(settings: Settings = Depends(get_settings)) -> AgentPipeline:
    return AgentPipeline(
        llm_client=LLMRouter(settings),
        vector_store=build_vector_store(settings),
    )


@router.post("/run", response_model=None)
async def run_triage(
    request: TriageRequest,
    db_session: AsyncSession = Depends(get_db_session),
    pipeline: AgentPipeline = Depends(get_agent_pipeline),
) -> dict[str, Any] | JSONResponse:
    started_at = perf_counter()
    request_id = str(uuid4())
    request_payload = request.model_dump(mode="json")

    audit_session = await create_session(
        db_session=db_session,
        request_payload=request_payload,
        session_id=request.session_id,
    )

    try:
        result = await pipeline.run(
            TriageInput(
                transcript=request.transcript,
                source_language=request.source_language,
                target_language=request.target_language,
                model_mode=request.model_mode,
                patient=request.patient,
                measurements=request.measurements,
                context=request.context,
            )
        )
    except ModelUnavailableError as exc:
        error = {
            "code": "MODEL_UNAVAILABLE",
            "message": "No model is available for the requested mode.",
            "details": {
                "session_id": audit_session.session_id,
                "requested_mode": exc.requested_mode,
            },
        }
        await update_session(
            db_session=db_session,
            session_id=audit_session.session_id,
            status="failed",
            errors=[error],
            model_mode="unavailable",
        )
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"error": error, "meta": {"request_id": request_id}},
        )
    except Exception as exc:
        error = {
            "code": "TRIAGE_VERIFICATION_FAILED",
            "message": "Triage pipeline failed.",
            "details": {
                "session_id": audit_session.session_id,
                "error_type": type(exc).__name__,
            },
        }
        await update_session(
            db_session=db_session,
            session_id=audit_session.session_id,
            status="failed",
            errors=[error],
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"error": error, "meta": {"request_id": request_id}},
        )

    model_mode = result.get("model", {}).get("mode", "unavailable")
    result_data = TriageResultData(session_id=audit_session.session_id, **result).model_dump(mode="json")
    await update_session(
        db_session=db_session,
        session_id=audit_session.session_id,
        status="completed",
        result_payload=result_data,
        errors=[],
        model_mode=model_mode,
    )

    duration_ms = round((perf_counter() - started_at) * 1000)
    return {
        "data": result_data,
        "meta": {
            "request_id": request_id,
            "model_mode": model_mode,
            "duration_ms": duration_ms,
        },
    }
