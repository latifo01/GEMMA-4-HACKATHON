from ai.agent.state import TriageState
from ai.tools.assess_dehydration import assess_dehydration
from ai.tools.assess_fever import assess_fever
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
    temperature_celsius = state.measurements.get("temperature_celsius")
    fever_duration_days = state.context.get("fever_duration_days")

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

    if symptoms.get("fever") or "fever" in state.module_hints:
        candidate_results.append(
            assess_fever(
                fever=True,
                temperature_celsius=temperature_celsius,
                fever_duration_days=fever_duration_days,
                general_danger_sign=danger_result["outputs"]["has_general_danger_sign"],
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
        tool_results=state.tool_results,
        measurements=state.measurements,
        patient=state.patient,
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
    lines = [
        f"Gemma 4 extracted: {format_list(extracted_signal_labels(state))}.",
        f"Final classification: {format_label(state.classification)} with {state.triage_color} triage color; human review remains required.",
    ]

    danger = find_tool_result(state, "detect_danger_signs")
    danger_flags = (danger or {}).get("outputs", {}).get("safety_flags", [])
    if danger_flags:
        lines.append(
            "Safety override: IMCI general danger signs detected "
            f"({format_list(danger_flags)}), so the output is escalated to urgent review and cannot be downgraded by generated text."
        )

    pneumonia = find_tool_result(state, "classify_pneumonia")
    if pneumonia:
        respiratory = pneumonia.get("outputs", {}).get("respiratory_rate", {})
        rate = state.measurements.get("respiratory_rate_bpm")
        threshold = respiratory.get("threshold_bpm")
        age_months = state.patient.get("age_months")
        if rate is not None and threshold is not None and age_months is not None:
            comparison = "meets/exceeds" if respiratory.get("is_fast_breathing") else "is below"
            lines.append(
                f"Respiratory rule: {rate} breaths/min at {age_months} months {comparison} "
                f"the IMCI fast-breathing threshold of {threshold} breaths/min."
            )
        if pneumonia.get("outputs", {}).get("safety_flags"):
            lines.append(f"Respiratory signs: {format_list(pneumonia['outputs']['safety_flags'])}.")

    dehydration = find_tool_result(state, "assess_dehydration")
    if dehydration:
        outputs = dehydration.get("outputs", {})
        matched_signs = outputs.get("matched_signs", [])
        lines.append(
            "Dehydration rule: "
            f"{outputs.get('severe_sign_count', 0)} severe signs and {outputs.get('some_sign_count', 0)} some-dehydration signs matched"
            f"{f' ({format_list(matched_signs)})' if matched_signs else ''}."
        )

    fever = find_tool_result(state, "assess_fever")
    if fever:
        fever_flags = fever.get("outputs", {}).get("safety_flags", [])
        lines.append(f"Fever rule: {format_list(fever_flags) if fever_flags else 'fever module checked with no escalation flag'}.")

    if state.missing_information:
        lines.append(f"Open uncertainty: {format_list(state.missing_information)} must be completed before relying on the case as closed.")

    lines.append(f"Evidence used: {format_citations(state.citations)}.")
    return "\n".join(lines)


def merge_unique(*items: list[str]) -> list[str]:
    merged: list[str] = []
    for values in items:
        for value in values:
            if value not in merged:
                merged.append(value)
    return merged


def find_tool_result(state: TriageState, tool_name: str) -> dict | None:
    return next((tool for tool in state.tool_results if tool.get("tool_name") == tool_name), None)


def extracted_signal_labels(state: TriageState) -> list[str]:
    return [
        key
        for key, value in state.extracted_symptoms.items()
        if key != "modules" and (value is True or (isinstance(value, str) and value.strip()))
    ] or ["no structured symptom confirmed"]


def format_citations(citations: list[dict]) -> str:
    if not citations:
        return "no retrieved citation"
    return "; ".join(f"{citation['source']} page {citation['page']}" for citation in citations[:3])


def format_list(items: list[str]) -> str:
    return ", ".join(format_label(str(item)) for item in items) if items else "none"


def format_label(value: str) -> str:
    return value.replace("measurements.", "").replace("context.", "").replace("_", " ").replace("module:", "").lower()
