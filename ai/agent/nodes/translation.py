from pathlib import Path
from typing import Any

from ai.agent.state import TriageState


async def translate_output(state: TriageState, llm_client: Any) -> TriageState:
    source_text = build_source_text(state)
    if state.target_language == "en":
        state.translated_output = source_text
        return state

    prompt = load_prompt("translation.txt").format(
        target_language=state.target_language,
        source_text=source_text,
    )
    try:
        response = await llm_client.generate_text(prompt, temperature=0.0)
        translated = response.text.strip()
    except Exception as exc:
        translated = source_text
        state.errors.append(
            {
                "code": "TRANSLATION_FALLBACK",
                "message": "Gemma translation failed; source clinical summary was returned.",
                "details": {"error_type": type(exc).__name__},
            }
        )
    if state.classification not in translated:
        translated = f"{state.classification}: {translated}"
    state.translated_output = translated
    return state


def build_source_text(state: TriageState) -> str:
    recommendations = " ".join(state.recommendations)
    return f"{state.classification}: {state.reasoning} {recommendations}".strip()


def load_prompt(filename: str) -> str:
    return (Path(__file__).resolve().parents[2] / "prompts" / filename).read_text(encoding="utf-8")
