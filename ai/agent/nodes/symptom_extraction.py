from pathlib import Path
from typing import Any

from ai.agent.state import TriageState


SYMPTOM_EXTRACTION_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "cough": {"type": "boolean"},
        "difficult_breathing": {"type": "boolean"},
        "chest_indrawing": {"type": "boolean"},
        "stridor_in_calm_child": {"type": "boolean"},
        "fever": {"type": "boolean"},
        "diarrhea": {"type": "boolean"},
        "vomits_everything": {"type": "boolean"},
        "unable_to_drink_or_breastfeed": {"type": "boolean"},
        "convulsions": {"type": "boolean"},
        "lethargic_or_unconscious": {"type": "boolean"},
        "sunken_eyes": {"type": "boolean"},
        "restless_or_irritable": {"type": "boolean"},
        "drinks_eagerly_or_thirsty": {"type": "boolean"},
        "skin_pinch_slow": {"type": "boolean"},
        "skin_pinch_very_slow": {"type": "boolean"},
        "modules": {"type": "array", "items": {"type": "string"}},
    },
}


async def extract_symptoms(state: TriageState, llm_client: Any) -> TriageState:
    prompt = load_prompt("symptom_extraction.txt").format(
        transcript=state.transcript,
        source_language=state.source_language,
    )
    response = await llm_client.generate_json(prompt, SYMPTOM_EXTRACTION_SCHEMA, temperature=0.0)
    symptoms = normalize_symptoms(response.parsed_json or {})

    state.extracted_symptoms = symptoms
    state.module_hints = list(symptoms.get("modules", []))
    state.model = {
        "mode": response.model_mode,
        "name": response.model_name,
    }
    return state


def normalize_symptoms(symptoms: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(symptoms)
    for key, value in SYMPTOM_EXTRACTION_SCHEMA["properties"].items():
        if value["type"] == "boolean":
            normalized[key] = bool(normalized.get(key, False))
    normalized["modules"] = list(normalized.get("modules", []))
    return normalized


def load_prompt(filename: str) -> str:
    return (Path(__file__).resolve().parents[2] / "prompts" / filename).read_text(encoding="utf-8")
