from typing import Any

from ai.tools.calculate_respiratory_rate import calculate_respiratory_rate


def classify_pneumonia(
    age_months: int | None,
    respiratory_rate_bpm: float | int | None,
    cough_or_difficult_breathing: bool,
    chest_indrawing: bool = False,
    stridor_in_calm_child: bool = False,
    general_danger_sign: bool = False,
) -> dict[str, Any]:
    inputs = {
        "age_months": age_months,
        "respiratory_rate_bpm": respiratory_rate_bpm,
        "cough_or_difficult_breathing": cough_or_difficult_breathing,
        "chest_indrawing": chest_indrawing,
        "stridor_in_calm_child": stridor_in_calm_child,
        "general_danger_sign": general_danger_sign,
    }

    respiratory_result = calculate_respiratory_rate(age_months, respiratory_rate_bpm)
    respiratory_outputs = respiratory_result["outputs"]
    missing_information = list(respiratory_outputs["missing_information"])

    if not cough_or_difficult_breathing:
        classification = "NO_COUGH_OR_DIFFICULT_BREATHING"
        triage_color = "NONE"
        risk_level = "not_applicable"
        safety_flags: list[str] = []
    elif general_danger_sign or stridor_in_calm_child:
        classification = "SEVERE_PNEUMONIA_OR_VERY_SEVERE_DISEASE"
        triage_color = "PINK"
        risk_level = "high"
        safety_flags = []
        if general_danger_sign:
            safety_flags.append("GENERAL_DANGER_SIGN")
        if stridor_in_calm_child:
            safety_flags.append("STRIDOR_IN_CALM_CHILD")
    elif chest_indrawing:
        classification = "PNEUMONIA"
        triage_color = "YELLOW"
        risk_level = "high"
        safety_flags = ["CHEST_INDRAWING"]
    elif respiratory_outputs["is_fast_breathing"] is True:
        classification = "PNEUMONIA"
        triage_color = "YELLOW"
        risk_level = "moderate"
        safety_flags = ["FAST_BREATHING"]
    elif respiratory_outputs["status"] != "classified":
        classification = "UNABLE_TO_CLASSIFY_RESPIRATORY_RATE"
        triage_color = "YELLOW"
        risk_level = "uncertain"
        safety_flags = ["MISSING_RESPIRATORY_INTERPRETATION"]
    else:
        classification = "COUGH_OR_COLD"
        triage_color = "GREEN"
        risk_level = "low"
        safety_flags = []

    return {
        "tool_name": "classify_pneumonia",
        "inputs": inputs,
        "outputs": {
            "classification": classification,
            "triage_color": triage_color,
            "risk_level": risk_level,
            "safety_flags": safety_flags,
            "missing_information": missing_information,
            "human_review_required": True,
            "respiratory_rate": respiratory_outputs,
        },
        "rationale": "IMCI cough or difficult breathing classification prioritizes danger signs and stridor, then chest indrawing or fast breathing.",
    }
