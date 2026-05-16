from ai.agent.state import TriageState
from ai.tools.assess_dehydration import assess_dehydration
from ai.tools.classify_pneumonia import classify_pneumonia
from ai.tools.detect_danger_signs import detect_danger_signs
from ai.tools.generate_referral import generate_referral


TRIAGE_PRIORITY = {
    "NONE": 0,
    "GREEN": 1,
    "YELLOW": 2,
    "PINK": 3,
}


def reason_over_imci(state: TriageState) -> TriageState:
    symptoms = state.extracted_symptoms
    age_months = state.patient.get("age_months")
    respiratory_rate_bpm = state.measurements.get("respiratory_rate_bpm")

    danger_result = detect_danger_signs(
        unable_to_drink_or_breastfeed=symptoms.get("unable_to_drink_or_breastfeed", False),
        vomits_everything=symptoms.get("vomits_everything", False),
        convulsions=symptoms.get("convulsions", False),
        lethargic_or_unconscious=symptoms.get("lethargic_or_unconscious", False),
    )
    state.tool_results.append(danger_result)

    candidate_results: list[dict] = []
    if symptoms.get("cough") or symptoms.get("difficult_breathing") or "cough_or_difficult_breathing" in state.module_hints:
        candidate_results.append(
            classify_pneumonia(
                age_months=age_months,
                respiratory_rate_bpm=respiratory_rate_bpm,
                cough_or_difficult_breathing=True,
                chest_indrawing=symptoms.get("chest_indrawing", False),
                stridor_in_calm_child=symptoms.get("stridor_in_calm_child", False),
                general_danger_sign=danger_result["outputs"]["has_general_danger_sign"],
            )
        )

    if symptoms.get("diarrhea") or "diarrhea_dehydration" in state.module_hints:
        candidate_results.append(
            assess_dehydration(
                lethargic_or_unconscious=symptoms.get("lethargic_or_unconscious", False),
                sunken_eyes=symptoms.get("sunken_eyes", False),
                unable_to_drink_or_drinking_poorly=symptoms.get("unable_to_drink_or_breastfeed", False),
                skin_pinch_very_slow=symptoms.get("skin_pinch_very_slow", False),
                restless_or_irritable=symptoms.get("restless_or_irritable", False),
                drinks_eagerly_or_thirsty=symptoms.get("drinks_eagerly_or_thirsty", False),
                skin_pinch_slow=symptoms.get("skin_pinch_slow", False),
            )
        )

    state.tool_results.extend(candidate_results)
    selected = select_highest_priority(candidate_results)
    if selected is None:
        selected_outputs = {
            "classification": "NEEDS_CLINICIAN_ASSESSMENT",
            "triage_color": "YELLOW",
            "safety_flags": ["UNKNOWN_COMPLAINT"],
            "missing_information": [],
        }
    else:
        selected_outputs = selected["outputs"]

    if danger_result["outputs"]["has_general_danger_sign"]:
        state.classification = "GENERAL_DANGER_SIGN"
        state.triage_color = "PINK"
    else:
        state.classification = selected_outputs["classification"]
        state.triage_color = selected_outputs["triage_color"]

    state.safety_flags = merge_unique(
        state.safety_flags,
        danger_result["outputs"]["safety_flags"],
        selected_outputs.get("safety_flags", []),
    )
    state.missing_information = merge_unique(
        state.missing_information,
        selected_outputs.get("missing_information", []),
    )

    referral = generate_referral(
        classification=state.classification,
        triage_color=state.triage_color,
        safety_flags=state.safety_flags,
        missing_information=state.missing_information,
    )
    state.tool_results.append(referral)
    state.recommendations = referral["outputs"]["actions"]
    state.reasoning = build_reasoning(state)
    return state


def select_highest_priority(tool_results: list[dict]) -> dict | None:
    if not tool_results:
        return None
    return max(tool_results, key=lambda item: TRIAGE_PRIORITY[item["outputs"]["triage_color"]])


def build_reasoning(state: TriageState) -> str:
    if state.citations:
        citation_text = "; ".join(
            f"{citation['source']} page {citation['page']}" for citation in state.citations[:3]
        )
    else:
        citation_text = "no retrieved citation"

    return (
        f"Classification {state.classification} with triage color {state.triage_color}. "
        f"Human review is required. Grounding: {citation_text}."
    )


def merge_unique(*items: list[str]) -> list[str]:
    merged: list[str] = []
    for values in items:
        for value in values:
            if value not in merged:
                merged.append(value)
    return merged
