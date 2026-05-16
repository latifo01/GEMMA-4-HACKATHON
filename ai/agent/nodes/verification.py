from ai.agent.state import TriageState


def verify_state(state: TriageState) -> TriageState:
    symptoms = state.extracted_symptoms
    has_danger_sign = any(
        symptoms.get(key, False)
        for key in [
            "unable_to_drink_or_breastfeed",
            "vomits_everything",
            "convulsions",
            "lethargic_or_unconscious",
        ]
    )

    if has_danger_sign and state.triage_color != "PINK":
        state.triage_color = "PINK"
        state.classification = "GENERAL_DANGER_SIGN"
        append_unique(state.safety_flags, "GENERAL_DANGER_SIGN")

    if not state.citations:
        append_unique(state.safety_flags, "INSUFFICIENT_RAG_CONTEXT")

    state.human_review_required = True
    return state


def append_unique(values: list[str], value: str) -> None:
    if value not in values:
        values.append(value)
