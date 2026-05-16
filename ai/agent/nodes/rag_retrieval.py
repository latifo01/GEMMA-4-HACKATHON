from typing import Any

from ai.agent.state import TriageState


def retrieve_rag_context(state: TriageState, vector_store: Any, top_k: int = 5) -> TriageState:
    query = build_retrieval_query(state)
    state.retrieval_query = query
    state.rag_context = vector_store.query(query, top_k=top_k)
    state.citations = [to_citation(item) for item in state.rag_context]
    return state


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
    return {
        "source": item["source"],
        "page": item["page"],
        "chunk_id": item["chunk_id"],
        "relevance_score": item.get("relevance_score", 0.0),
        "quote": item.get("text", "")[:240],
    }
