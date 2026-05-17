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
    symptoms = normalize_symptoms(response.parsed_json or {}, state.transcript)

    state.extracted_symptoms = symptoms
    state.module_hints = list(symptoms.get("modules", []))
    state.model = {
        "mode": response.model_mode,
        "name": response.model_name,
    }
    return state


def normalize_symptoms(symptoms: dict[str, Any], transcript: str = "") -> dict[str, Any]:
    normalized = dict(symptoms)
    for key, value in SYMPTOM_EXTRACTION_SCHEMA["properties"].items():
        if value["type"] == "boolean":
            normalized[key] = bool(normalized.get(key, False))
    normalized["modules"] = list(normalized.get("modules", []))
    apply_deterministic_cues(normalized, transcript)
    return normalized


def apply_deterministic_cues(symptoms: dict[str, Any], transcript: str) -> None:
    text = normalize_text(transcript)
    if not text:
        return

    set_true_if_cued(symptoms, "fever", text, ["fever", "fievre", "hot body", "corps chaud", "temperature"])
    set_true_if_cued(symptoms, "cough", text, ["cough", "toux", "tousse"])
    set_true_if_cued(
        symptoms,
        "difficult_breathing",
        text,
        ["difficult breathing", "breathing fast", "respiration difficile", "respire vite", "gene respiratoire"],
    )
    set_true_if_cued(symptoms, "diarrhea", text, ["diarrhea", "diarrhoea", "diarrhee", "selles liquides"])
    set_true_if_cued(symptoms, "convulsions", text, ["convulsion", "convulsions", "seizure", "crise"])
    set_true_if_cued(
        symptoms,
        "lethargic_or_unconscious",
        text,
        ["lethargic", "unconscious", "inconscient", "lethargique", "somnolent"],
    )
    set_true_if_cued(
        symptoms,
        "unable_to_drink_or_breastfeed",
        text,
        [
            "unable to drink",
            "cannot drink",
            "not able to drink",
            "refuses to drink",
            "refuse to drink",
            "refuse de boire",
            "ne peut pas boire",
            "n'arrive pas a boire",
            "n arrive pas a boire",
            "incapable de boire",
            "unable to breastfeed",
            "cannot breastfeed",
            "refuse le sein",
        ],
    )
    set_true_if_cued(
        symptoms,
        "vomits_everything",
        text,
        [
            "vomits everything",
            "vomit everything",
            "vomits all",
            "vomit all",
            "vomit whenever",
            "vomit after everything",
            "vomit tout",
            "vomit chaque fois",
            "vomissements incoercibles",
        ],
    )

    modules = symptoms["modules"]
    add_module_if(symptoms.get("cough") or symptoms.get("difficult_breathing"), modules, "cough_or_difficult_breathing")
    add_module_if(
        symptoms.get("diarrhea") or symptoms.get("sunken_eyes") or symptoms.get("unable_to_drink_or_breastfeed"),
        modules,
        "diarrhea_dehydration",
    )
    add_module_if(symptoms.get("fever"), modules, "fever")


def set_true_if_cued(symptoms: dict[str, Any], key: str, text: str, cues: list[str]) -> None:
    if any(cue in text for cue in cues):
        symptoms[key] = True


def add_module_if(condition: bool, modules: list[str], module_name: str) -> None:
    if condition and module_name not in modules:
        modules.append(module_name)


def normalize_text(text: str) -> str:
    import unicodedata

    normalized = unicodedata.normalize("NFKD", text.lower())
    return "".join(char for char in normalized if not unicodedata.combining(char))


def load_prompt(filename: str) -> str:
    return (Path(__file__).resolve().parents[2] / "prompts" / filename).read_text(encoding="utf-8")
