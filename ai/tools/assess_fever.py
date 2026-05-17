from typing import Any


def assess_fever(
    fever: bool = False,
    temperature_celsius: float | int | None = None,
    fever_duration_days: int | None = None,
    general_danger_sign: bool = False,
) -> dict[str, Any]:
    inputs = {
        "fever": fever,
        "temperature_celsius": temperature_celsius,
        "fever_duration_days": fever_duration_days,
        "general_danger_sign": general_danger_sign,
    }

    missing_information: list[str] = []
    if temperature_celsius is None:
        missing_information.append("measurements.temperature_celsius")
    if fever_duration_days is None:
        missing_information.append("context.fever_duration_days")

    safety_flags: list[str] = []
    if fever:
        safety_flags.append("FEVER")
    if temperature_celsius is not None and temperature_celsius >= 38.5:
        safety_flags.append("HIGH_FEVER")
    if fever_duration_days is not None and fever_duration_days > 7:
        safety_flags.append("PROLONGED_FEVER")

    if not fever:
        classification = "NO_FEVER"
        triage_color = "NONE"
        risk_level = "not_applicable"
    elif general_danger_sign:
        classification = "FEVER_WITH_GENERAL_DANGER_SIGN"
        triage_color = "PINK"
        risk_level = "high"
        safety_flags.append("GENERAL_DANGER_SIGN")
    elif "PROLONGED_FEVER" in safety_flags:
        classification = "PROLONGED_FEVER"
        triage_color = "YELLOW"
        risk_level = "moderate"
    else:
        classification = "FEVER"
        triage_color = "GREEN"
        risk_level = "low"

    return {
        "tool_name": "assess_fever",
        "inputs": inputs,
        "outputs": {
            "classification": classification,
            "triage_color": triage_color,
            "risk_level": risk_level,
            "safety_flags": safety_flags,
            "missing_information": missing_information,
            "human_review_required": True,
        },
        "rationale": "IMCI fever assessment keeps danger signs urgent and records missing fever context for clinician review.",
    }
