import json

from ai.tools.assess_dehydration import assess_dehydration
from ai.tools.assess_fever import assess_fever
from ai.tools.calculate_respiratory_rate import calculate_respiratory_rate
from ai.tools.classify_pneumonia import classify_pneumonia
from ai.tools.detect_danger_signs import detect_danger_signs
from ai.tools.generate_referral import generate_referral


def assert_json_serializable(payload: dict) -> None:
    json.dumps(payload)


def test_fast_breathing_threshold_for_age_under_2_months():
    fast = calculate_respiratory_rate(age_months=1, respiratory_rate_bpm=60)
    not_fast = calculate_respiratory_rate(age_months=1, respiratory_rate_bpm=59)

    assert fast["outputs"]["threshold_bpm"] == 60
    assert fast["outputs"]["is_fast_breathing"] is True
    assert not_fast["outputs"]["is_fast_breathing"] is False
    assert_json_serializable(fast)


def test_fast_breathing_threshold_for_age_2_to_11_months():
    fast = calculate_respiratory_rate(age_months=2, respiratory_rate_bpm=50)
    not_fast = calculate_respiratory_rate(age_months=11, respiratory_rate_bpm=49)

    assert fast["outputs"]["threshold_bpm"] == 50
    assert fast["outputs"]["is_fast_breathing"] is True
    assert not_fast["outputs"]["is_fast_breathing"] is False


def test_fast_breathing_threshold_for_age_12_to_59_months():
    fast = calculate_respiratory_rate(age_months=12, respiratory_rate_bpm=40)
    not_fast = calculate_respiratory_rate(age_months=59, respiratory_rate_bpm=39)

    assert fast["outputs"]["threshold_bpm"] == 40
    assert fast["outputs"]["is_fast_breathing"] is True
    assert not_fast["outputs"]["is_fast_breathing"] is False


def test_missing_age_returns_explicit_uncertainty():
    result = calculate_respiratory_rate(age_months=None, respiratory_rate_bpm=52)

    assert result["outputs"]["status"] == "uncertain"
    assert result["outputs"]["is_fast_breathing"] is None
    assert "age_months" in result["outputs"]["missing_information"]


def test_chest_indrawing_produces_high_risk_pneumonia_classification():
    result = classify_pneumonia(
        age_months=18,
        respiratory_rate_bpm=30,
        cough_or_difficult_breathing=True,
        chest_indrawing=True,
    )

    assert result["outputs"]["classification"] == "PNEUMONIA"
    assert result["outputs"]["triage_color"] == "YELLOW"
    assert result["outputs"]["risk_level"] == "high"
    assert "CHEST_INDRAWING" in result["outputs"]["safety_flags"]
    assert_json_serializable(result)


def test_general_danger_signs_produce_high_risk_safety_flags():
    danger = detect_danger_signs(unable_to_drink_or_breastfeed=True, convulsions=True)
    pneumonia = classify_pneumonia(
        age_months=9,
        respiratory_rate_bpm=35,
        cough_or_difficult_breathing=True,
        general_danger_sign=True,
    )

    assert danger["outputs"]["has_general_danger_sign"] is True
    assert danger["outputs"]["triage_color"] == "PINK"
    assert "UNABLE_TO_DRINK_OR_BREASTFEED" in danger["outputs"]["safety_flags"]
    assert "CONVULSIONS" in danger["outputs"]["safety_flags"]
    assert pneumonia["outputs"]["classification"] == "SEVERE_PNEUMONIA_OR_VERY_SEVERE_DISEASE"
    assert pneumonia["outputs"]["triage_color"] == "PINK"


def test_dehydration_classification_prioritizes_severe_signs():
    result = assess_dehydration(
        lethargic_or_unconscious=True,
        sunken_eyes=True,
        restless_or_irritable=True,
        drinks_eagerly_or_thirsty=True,
    )

    assert result["outputs"]["classification"] == "SEVERE_DEHYDRATION"
    assert result["outputs"]["triage_color"] == "PINK"


def test_dehydration_classifies_some_dehydration_with_two_moderate_signs():
    result = assess_dehydration(
        restless_or_irritable=True,
        sunken_eyes=True,
    )

    assert result["outputs"]["classification"] == "SOME_DEHYDRATION"
    assert result["outputs"]["triage_color"] == "YELLOW"


def test_referral_tool_returns_human_review_and_actions():
    result = generate_referral(
        classification="SEVERE_PNEUMONIA_OR_VERY_SEVERE_DISEASE",
        triage_color="PINK",
        safety_flags=["GENERAL_DANGER_SIGN"],
        missing_information=[],
    )

    assert result["outputs"]["urgent_referral"] is True
    assert result["outputs"]["human_review_required"] is True
    assert result["outputs"]["actions"]
    assert_json_serializable(result)


def test_fever_tool_records_missing_context_without_escalating_basic_fever():
    result = assess_fever(fever=True)

    assert result["outputs"]["classification"] == "FEVER"
    assert result["outputs"]["triage_color"] == "GREEN"
    assert "measurements.temperature_celsius" in result["outputs"]["missing_information"]
    assert "context.fever_duration_days" in result["outputs"]["missing_information"]
    assert "FEVER" in result["outputs"]["safety_flags"]
    assert_json_serializable(result)
