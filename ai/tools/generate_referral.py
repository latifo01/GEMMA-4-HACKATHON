from typing import Any


def generate_referral(
    classification: str,
    triage_color: str,
    safety_flags: list[str] | None = None,
    missing_information: list[str] | None = None,
) -> dict[str, Any]:
    safety_flags = safety_flags or []
    missing_information = missing_information or []

    if triage_color == "PINK":
        urgent_referral = True
        actions = [
            "Arrange urgent referral according to local IMCI protocol.",
            "Give appropriate pre-referral care according to local clinical guidance.",
            "Keep the caregiver informed and document danger signs.",
        ]
    elif triage_color == "YELLOW":
        urgent_referral = False
        actions = [
            "Treat according to local IMCI protocol.",
            "Explain return precautions to the caregiver.",
            "Plan follow-up according to local clinical guidance.",
        ]
    elif triage_color == "GREEN":
        urgent_referral = False
        actions = [
            "Provide home-care advice according to local IMCI protocol.",
            "Advise the caregiver when to return immediately.",
            "Schedule routine follow-up if symptoms persist.",
        ]
    else:
        urgent_referral = False
        actions = [
            "Collect missing clinical information before classification.",
            "Keep human clinical review active.",
        ]

    if missing_information:
        actions.append("Resolve missing information before relying on the classification.")

    return {
        "tool_name": "generate_referral",
        "inputs": {
            "classification": classification,
            "triage_color": triage_color,
            "safety_flags": safety_flags,
            "missing_information": missing_information,
        },
        "outputs": {
            "urgent_referral": urgent_referral,
            "human_review_required": True,
            "classification": classification,
            "triage_color": triage_color,
            "safety_flags": safety_flags,
            "missing_information": missing_information,
            "actions": actions,
        },
        "rationale": "Referral text is deterministic and keeps local IMCI guidance plus clinician review as the decision boundary.",
    }
