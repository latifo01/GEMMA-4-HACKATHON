import os
from pathlib import Path
from typing import Any

from ai.agent.state import TriageState
from ai.rag.fallback_imci import query_fallback_evidence

_PAGE_IMAGES_DIR = os.getenv("RAG_VISUAL_ASSETS_PATH", "./data/page_images")
_PAGE_IMAGES_URL = "/images"


def retrieve_rag_context(state: TriageState, vector_store: Any, top_k: int = 5) -> TriageState:
    query = build_retrieval_query(state)
    state.retrieval_query = query
    state.rag_context = query_vector_store(vector_store, query, top_k=top_k)
    if not state.rag_context:
        state.rag_context = query_fallback_evidence(query, top_k=top_k)
    state.citations = [to_citation(item) for item in state.rag_context]
    return state


def query_vector_store(vector_store: Any, query: str, top_k: int) -> list[dict[str, Any]]:
    try:
        return vector_store.query(query, top_k=top_k, include_visual_embeddings=True)
    except TypeError:
        return vector_store.query(query, top_k=top_k)


def build_retrieval_query(state: TriageState) -> str:
    true_symptoms = sorted(
        key for key, value in state.extracted_symptoms.items() if isinstance(value, bool) and value
    )
    parts = [
        state.transcript,
        "modules: " + " ".join(state.module_hints),
        "symptoms: " + " ".join(true_symptoms),
    ]
    age_months = state.patient.get("age_months")
    if age_months is not None:
        parts.append(f"age_months: {age_months}")
    return "\n".join(part for part in parts if part.strip())


def to_citation(item: dict[str, Any]) -> dict[str, Any]:
    source = item.get("source", "")
    page = item.get("page")
    image_url = _resolve_image_url(source, page)
    return {
        "source": source,
        "page": page,
        "chunk_id": item["chunk_id"],
        "relevance_score": item.get("relevance_score", 0.0),
        "quote": item.get("text", "")[:240],
        "image_url": image_url,
    }


def _resolve_image_url(source: str, page: Any) -> str | None:
    """Return the /images URL for an IMCI page image if it exists on disk.

    Filename convention (matches ingest.py): {stem}-p{page:03d}.png
    where stem = Path(source).stem.lower().replace(" ", "-")
    """
    if page is None or not source:
        return None
    stem = Path(source).stem.lower().replace(" ", "-")
    filename = f"{stem}-p{int(page):03d}.png"
    if os.path.exists(os.path.join(_PAGE_IMAGES_DIR, filename)):
        return f"{_PAGE_IMAGES_URL}/{filename}"
    return None
