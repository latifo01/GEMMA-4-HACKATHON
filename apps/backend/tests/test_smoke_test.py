import pytest

from scripts.smoke_test import SmokeFailure, ensure_gemma4_model, validate_triage_result


def test_smoke_test_accepts_gemma4_model_names():
    ensure_gemma4_model("models/gemma-4-26b-a4b-it")
    ensure_gemma4_model("gemma4:e4b-it")


def test_smoke_test_rejects_non_gemma4_model_names():
    with pytest.raises(SmokeFailure):
        ensure_gemma4_model("gemma3:12b")


def test_smoke_test_validates_triage_result_contract():
    result = {
        "data": {
            "session_id": "session-1",
            "classification": "PNEUMONIA",
            "triage_color": "YELLOW",
            "citations": [{"source": "imci.pdf"}],
            "model": {"mode": "online", "name": "models/gemma-4-26b-a4b-it"},
        }
    }

    summary = validate_triage_result(result, expected_mode="online")

    assert summary["session_id"] == "session-1"
    assert summary["classification"] == "PNEUMONIA"
    assert summary["model_name"] == "models/gemma-4-26b-a4b-it"


def test_smoke_test_allows_non_gemma4_offline_when_explicitly_configured():
    result = {
        "data": {
            "session_id": "session-1",
            "classification": "PNEUMONIA",
            "triage_color": "YELLOW",
            "citations": [{"source": "imci.pdf"}],
            "model": {"mode": "offline", "name": "small-local-model"},
        }
    }

    summary = validate_triage_result(result, expected_mode="offline", require_gemma4=False)

    assert summary["model_name"] == "small-local-model"


def test_smoke_test_rejects_triage_result_without_citations():
    result = {
        "data": {
            "session_id": "session-1",
            "classification": "PNEUMONIA",
            "triage_color": "YELLOW",
            "citations": [],
            "model": {"mode": "online", "name": "models/gemma-4-26b-a4b-it"},
        }
    }

    with pytest.raises(SmokeFailure):
        validate_triage_result(result, expected_mode="online")
