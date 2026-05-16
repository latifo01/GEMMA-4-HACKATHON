from typing import Any


def assess_dehydration(
    lethargic_or_unconscious: bool = False,
    sunken_eyes: bool = False,
    unable_to_drink_or_drinking_poorly: bool = False,
    skin_pinch_very_slow: bool = False,
    restless_or_irritable: bool = False,
    drinks_eagerly_or_thirsty: bool = False,
    skin_pinch_slow: bool = False,
) -> dict[str, Any]:
    inputs = {
        "lethargic_or_unconscious": lethargic_or_unconscious,
        "sunken_eyes": sunken_eyes,
        "unable_to_drink_or_drinking_poorly": unable_to_drink_or_drinking_poorly,
        "skin_pinch_very_slow": skin_pinch_very_slow,
        "restless_or_irritable": restless_or_irritable,
        "drinks_eagerly_or_thirsty": drinks_eagerly_or_thirsty,
        "skin_pinch_slow": skin_pinch_slow,
    }

    severe_signs = []
    if lethargic_or_unconscious:
        severe_signs.append("LETHARGIC_OR_UNCONSCIOUS")
    if sunken_eyes:
        severe_signs.append("SUNKEN_EYES")
    if unable_to_drink_or_drinking_poorly:
        severe_signs.append("UNABLE_TO_DRINK_OR_DRINKING_POORLY")
    if skin_pinch_very_slow:
        severe_signs.append("SKIN_PINCH_VERY_SLOW")

    some_signs = []
    if restless_or_irritable:
        some_signs.append("RESTLESS_OR_IRRITABLE")
    if sunken_eyes:
        some_signs.append("SUNKEN_EYES")
    if drinks_eagerly_or_thirsty:
        some_signs.append("DRINKS_EAGERLY_OR_THIRSTY")
    if skin_pinch_slow:
        some_signs.append("SKIN_PINCH_SLOW")

    if len(severe_signs) >= 2:
        classification = "SEVERE_DEHYDRATION"
        triage_color = "PINK"
        risk_level = "high"
        matched_signs = severe_signs
    elif len(some_signs) >= 2:
        classification = "SOME_DEHYDRATION"
        triage_color = "YELLOW"
        risk_level = "moderate"
        matched_signs = some_signs
    else:
        classification = "NO_DEHYDRATION"
        triage_color = "GREEN"
        risk_level = "low"
        matched_signs = severe_signs + some_signs

    return {
        "tool_name": "assess_dehydration",
        "inputs": inputs,
        "outputs": {
            "classification": classification,
            "triage_color": triage_color,
            "risk_level": risk_level,
            "matched_signs": matched_signs,
            "severe_sign_count": len(severe_signs),
            "some_sign_count": len(some_signs),
            "human_review_required": True,
        },
        "rationale": "IMCI dehydration classification uses two or more severe signs before considering some dehydration signs.",
    }
