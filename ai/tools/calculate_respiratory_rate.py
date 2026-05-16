from typing import Any


def calculate_respiratory_rate(
    age_months: int | None,
    respiratory_rate_bpm: float | int | None,
) -> dict[str, Any]:
    inputs = {
        "age_months": age_months,
        "respiratory_rate_bpm": respiratory_rate_bpm,
    }

    missing_information: list[str] = []
    errors: list[str] = []

    if age_months is None:
        missing_information.append("age_months")
    elif age_months < 0:
        errors.append("age_months must be greater than or equal to 0.")

    if respiratory_rate_bpm is None:
        missing_information.append("respiratory_rate_bpm")
    elif respiratory_rate_bpm < 0:
        errors.append("respiratory_rate_bpm must be greater than or equal to 0.")

    if errors:
        return {
            "tool_name": "calculate_respiratory_rate",
            "inputs": inputs,
            "outputs": {
                "status": "invalid",
                "age_group": None,
                "threshold_bpm": None,
                "is_fast_breathing": None,
                "missing_information": missing_information,
                "errors": errors,
            },
            "rationale": "Respiratory rate interpretation requires valid non-negative age and rate values.",
        }

    if missing_information:
        return {
            "tool_name": "calculate_respiratory_rate",
            "inputs": inputs,
            "outputs": {
                "status": "uncertain",
                "age_group": None,
                "threshold_bpm": None,
                "is_fast_breathing": None,
                "missing_information": missing_information,
                "errors": [],
            },
            "rationale": "Age and respiratory rate are required to apply IMCI fast-breathing thresholds.",
        }

    assert age_months is not None
    assert respiratory_rate_bpm is not None

    if age_months < 2:
        age_group = "under_2_months"
        threshold_bpm = 60
    elif age_months < 12:
        age_group = "2_to_11_months"
        threshold_bpm = 50
    elif age_months < 60:
        age_group = "12_to_59_months"
        threshold_bpm = 40
    else:
        return {
            "tool_name": "calculate_respiratory_rate",
            "inputs": inputs,
            "outputs": {
                "status": "uncertain",
                "age_group": "outside_imci_under_5_scope",
                "threshold_bpm": None,
                "is_fast_breathing": None,
                "missing_information": ["age_months_under_60"],
                "errors": [],
            },
            "rationale": "This tool is scoped to children under 5 years old.",
        }

    return {
        "tool_name": "calculate_respiratory_rate",
        "inputs": inputs,
        "outputs": {
            "status": "classified",
            "age_group": age_group,
            "threshold_bpm": threshold_bpm,
            "is_fast_breathing": respiratory_rate_bpm >= threshold_bpm,
            "missing_information": [],
            "errors": [],
        },
        "rationale": "IMCI fast breathing is determined by comparing breaths per minute with the age-specific threshold.",
    }
