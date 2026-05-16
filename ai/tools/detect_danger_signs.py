from typing import Any


def detect_danger_signs(
    unable_to_drink_or_breastfeed: bool = False,
    vomits_everything: bool = False,
    convulsions: bool = False,
    lethargic_or_unconscious: bool = False,
) -> dict[str, Any]:
    inputs = {
        "unable_to_drink_or_breastfeed": unable_to_drink_or_breastfeed,
        "vomits_everything": vomits_everything,
        "convulsions": convulsions,
        "lethargic_or_unconscious": lethargic_or_unconscious,
    }

    safety_flags: list[str] = []
    if unable_to_drink_or_breastfeed:
        safety_flags.append("UNABLE_TO_DRINK_OR_BREASTFEED")
    if vomits_everything:
        safety_flags.append("VOMITS_EVERYTHING")
    if convulsions:
        safety_flags.append("CONVULSIONS")
    if lethargic_or_unconscious:
        safety_flags.append("LETHARGIC_OR_UNCONSCIOUS")

    has_general_danger_sign = bool(safety_flags)

    return {
        "tool_name": "detect_danger_signs",
        "inputs": inputs,
        "outputs": {
            "has_general_danger_sign": has_general_danger_sign,
            "safety_flags": safety_flags,
            "triage_color": "PINK" if has_general_danger_sign else "NONE",
            "human_review_required": True,
        },
        "rationale": "IMCI general danger signs require urgent clinician review and must not be downgraded by generated text.",
    }
