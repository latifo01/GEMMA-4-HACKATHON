from typing import Any


def generate_referral(
    classification: str,
    triage_color: str,
    safety_flags: list[str] | None = None,
    missing_information: list[str] | None = None,
    tool_results: list[dict[str, Any]] | None = None,
    measurements: dict[str, Any] | None = None,
    patient: dict[str, Any] | None = None,
) -> dict[str, Any]:
    safety_flags = safety_flags or []
    missing_information = missing_information or []
    tool_results = tool_results or []
    measurements = measurements or {}
    patient = patient or {}

    if triage_color == "PINK":
        urgent_referral = True
        actions = build_urgent_actions(classification, safety_flags, tool_results)
    elif triage_color == "YELLOW":
        urgent_referral = False
        actions = build_same_day_actions(classification, safety_flags, tool_results, measurements, patient)
    elif classification == "FEVER":
        urgent_referral = False
        actions = [
            "Check temperature, malaria risk, and local fever protocol before treatment.",
            "Give fever care according to local clinical guidance and confirm hydration status.",
            "Ask the caregiver to return immediately for poor drinking, repeated vomiting, convulsions, lethargy, or breathing difficulty.",
        ]
    elif triage_color == "GREEN":
        urgent_referral = False
        actions = [
            "Provide home-care advice that matches the current low-risk IMCI classification.",
            "Explain danger signs clearly: poor drinking, repeated vomiting, convulsions, lethargy, fast breathing, or worsening fever.",
            "Schedule routine follow-up if symptoms persist or the caregiver returns with new danger signs.",
        ]
    else:
        urgent_referral = False
        actions = [
            "Pause final classification and collect the missing clinical information listed below.",
            "Keep human clinical review active until the missing data is resolved.",
        ]

    if missing_information:
        actions.extend(build_missing_information_actions(missing_information))

    return {
        "tool_name": "generate_referral",
        "inputs": {
            "classification": classification,
            "triage_color": triage_color,
            "safety_flags": safety_flags,
            "missing_information": missing_information,
            "tool_results_count": len(tool_results),
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


def build_urgent_actions(
    classification: str,
    safety_flags: list[str],
    tool_results: list[dict[str, Any]],
) -> list[str]:
    actions = [
        "Escalate now: keep the child in the urgent/referral area and notify the senior clinician or referral facility.",
    ]

    if "UNABLE_TO_DRINK_OR_BREASTFEED" in safety_flags:
        actions.append("Treat inability to drink or breastfeed as a danger sign; do not rely on home oral intake while referral is arranged.")
    if "VOMITS_EVERYTHING" in safety_flags:
        actions.append("Because the child is vomiting repeatedly, prepare referral without waiting for oral medication or fluids to be tolerated.")
    if "LETHARGIC_OR_UNCONSCIOUS" in safety_flags:
        actions.append("Check airway, breathing, circulation, glucose, and temperature if available while urgent referral is being organized.")
    if "CONVULSIONS" in safety_flags:
        actions.append("Protect the airway and manage convulsions according to the local emergency protocol before transport.")

    if has_tool(tool_results, "classify_pneumonia") or classification == "SEVERE_PNEUMONIA_OR_VERY_SEVERE_DISEASE":
        actions.append("Reassess breathing, chest indrawing, stridor, and oxygen saturation if available; start local pre-referral respiratory care.")
    if has_tool(tool_results, "assess_dehydration"):
        actions.append("Reassess hydration signs and prepare the local severe-dehydration pathway during referral preparation.")
    if has_tool(tool_results, "assess_fever"):
        actions.append("Check temperature and malaria or sepsis pathway if available, but do not delay urgent referral for testing.")

    actions.append("Tell the caregiver exactly which danger sign triggered referral and document it in the audit record.")
    return dedupe(actions)


def build_same_day_actions(
    classification: str,
    safety_flags: list[str],
    tool_results: list[dict[str, Any]],
    measurements: dict[str, Any],
    patient: dict[str, Any],
) -> list[str]:
    actions: list[str] = []

    if classification == "PNEUMONIA" or "FAST_BREATHING" in safety_flags or "CHEST_INDRAWING" in safety_flags:
        respiratory_action = build_respiratory_action(tool_results, measurements, patient)
        actions.append(respiratory_action)
        actions.append("Check for chest indrawing, stridor, oxygen saturation if available, and any general danger sign before discharge.")
        actions.append("Treat as same-day pneumonia care per local IMCI protocol and give clear return precautions for worsening breathing.")
    elif classification == "SOME_DEHYDRATION":
        actions.extend(
            [
                "Start supervised oral rehydration in the clinic if the child can drink, then reassess hydration signs before leaving.",
                "Recheck for sunken eyes, thirst, irritability, skin pinch, and any danger sign during observation.",
                "Give the caregiver clear return precautions for poor drinking, repeated vomiting, blood in stool, lethargy, or worsening diarrhea.",
            ]
        )
    elif classification == "PROLONGED_FEVER":
        actions.extend(
            [
                "Treat fever duration as a same-day assessment problem; check malaria risk, temperature, rash, neck stiffness, and local outbreak context.",
                "Use local testing or referral guidance for fever lasting more than 7 days.",
                "Ask the caregiver to return immediately for convulsions, lethargy, poor drinking, stiff neck, breathing difficulty, or persistent high fever.",
            ]
        )
    else:
        actions.extend(
            [
                "Complete a focused clinician assessment today before relying on a lower-risk classification.",
                "Use the detected symptoms and missing-information list to ask targeted follow-up questions.",
                "Explain return precautions before the caregiver leaves.",
            ]
        )

    return dedupe(actions)


def build_respiratory_action(
    tool_results: list[dict[str, Any]],
    measurements: dict[str, Any],
    patient: dict[str, Any],
) -> str:
    pneumonia = find_tool(tool_results, "classify_pneumonia")
    respiratory = (pneumonia or {}).get("outputs", {}).get("respiratory_rate", {})
    rate = measurements.get("respiratory_rate_bpm")
    threshold = respiratory.get("threshold_bpm")
    age_months = patient.get("age_months")

    if rate is not None and threshold is not None and age_months is not None:
        return (
            f"Use the measured respiratory rate: {rate} breaths/min at {age_months} months "
            f"meets or exceeds the IMCI fast-breathing threshold of {threshold} breaths/min."
        )
    if rate is not None:
        return f"Use the measured respiratory rate of {rate} breaths/min and confirm it against the IMCI age threshold."
    return "Measure respiratory rate for a full minute before finalizing cough or difficult-breathing severity."


def build_missing_information_actions(missing_information: list[str]) -> list[str]:
    actions: list[str] = []
    for item in missing_information:
        label = item.replace("measurements.", "").replace("context.", "")
        if label == "respiratory_rate_bpm":
            actions.append("Before closing the case, count respiratory rate for a full minute; cough severity is uncertain without it.")
        elif label == "temperature_celsius":
            actions.append("Record temperature in Celsius so fever severity is not inferred from caregiver wording alone.")
        elif label == "fever_duration_days":
            actions.append("Ask how many days the fever has lasted to separate short fever from prolonged fever risk.")
        elif label == "patient.age_months" or label == "age_months":
            actions.append("Confirm the child's age in months because IMCI respiratory thresholds depend on age.")
        else:
            actions.append(f"Resolve missing field: {label}.")
    return dedupe(actions)


def find_tool(tool_results: list[dict[str, Any]], tool_name: str) -> dict[str, Any] | None:
    return next((tool for tool in tool_results if tool.get("tool_name") == tool_name), None)


def has_tool(tool_results: list[dict[str, Any]], tool_name: str) -> bool:
    return find_tool(tool_results, tool_name) is not None


def dedupe(actions: list[str]) -> list[str]:
    unique: list[str] = []
    for action in actions:
        if action not in unique:
            unique.append(action)
    return unique
