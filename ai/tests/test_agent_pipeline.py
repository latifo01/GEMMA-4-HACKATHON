from typing import Any

import pytest

from ai.agent.graph import AgentPipeline
from ai.agent.nodes.intake import run_intake
from ai.agent.nodes.verification import verify_state
from ai.agent.state import TriageInput, TriageState
from ai.llm.router import LLMResponse


class FakeLLM:
    model_mode = "online"
    model_name = "fake-gemma"

    def __init__(self, symptoms: dict[str, Any], translated_text: str = "PNEUMONIA: translated text") -> None:
        self.symptoms = symptoms
        self.translated_text = translated_text

    async def healthcheck(self) -> bool:
        return True

    async def generate_json(
        self,
        prompt: str,
        response_schema: dict[str, Any],
        temperature: float = 0.0,
    ) -> LLMResponse:
        return LLMResponse(
            text="{}",
            model_mode=self.model_mode,
            model_name=self.model_name,
            parsed_json=self.symptoms,
        )

    async def generate_text(self, prompt: str, temperature: float = 0.0) -> LLMResponse:
        return LLMResponse(
            text=self.translated_text,
            model_mode=self.model_mode,
            model_name=self.model_name,
        )


class FailingJsonLLM(FakeLLM):
    async def generate_json(
        self,
        prompt: str,
        response_schema: dict[str, Any],
        temperature: float = 0.0,
    ) -> LLMResponse:
        raise RuntimeError("model failed")


class FakeStore:
    def __init__(self) -> None:
        self.queries: list[str] = []

    def query(self, query_text: str, top_k: int = 5) -> list[dict[str, Any]]:
        self.queries.append(query_text)
        return [
            {
                "chunk_id": "imci-chart-booklet-p006-c000",
                "source": "imci-chart-booklet.pdf",
                "page": 6,
                "chunk_type": "text",
                "section_title": "Cough or difficult breathing",
                "text": "IMCI cough or difficult breathing guidance.",
                "relevance_score": 0.91,
                "visual_asset_path": None,
            }
        ]


class EmptyStore:
    def query(self, query_text: str, top_k: int = 5) -> list[dict[str, Any]]:
        return []


def test_intake_normalizes_language_and_missing_age():
    state = run_intake(
        TriageInput(
            transcript="L'enfant tousse.",
            source_language="français",
            target_language="fr",
        )
    )

    assert state.source_language == "fr"
    assert state.target_language == "fr"
    assert "patient.age_months" in state.missing_information


@pytest.mark.asyncio
async def test_pipeline_returns_grounded_pneumonia_result_with_citations():
    llm = FakeLLM(
        symptoms={
            "cough": True,
            "difficult_breathing": True,
            "chest_indrawing": True,
            "modules": ["cough_or_difficult_breathing"],
        },
        translated_text="PNEUMONIA: texte traduit pour le soignant.",
    )
    store = FakeStore()
    pipeline = AgentPipeline(llm_client=llm, vector_store=store)

    result = await pipeline.run(
        TriageInput(
            transcript="The child has cough, difficult breathing, and chest indrawing.",
            source_language="en",
            target_language="fr",
            patient={"age_months": 18},
            measurements={"respiratory_rate_bpm": 52},
        )
    )

    assert result["classification"] == "PNEUMONIA"
    assert result["triage_color"] == "YELLOW"
    assert result["human_review_required"] is True
    assert result["citations"][0]["source"] == "imci-chart-booklet.pdf"
    assert result["tool_results"]
    assert "PNEUMONIA" in result["translated_output"]
    assert "cough_or_difficult_breathing" in store.queries[0]


@pytest.mark.asyncio
async def test_pipeline_handles_diarrhea_and_dehydration_module():
    llm = FakeLLM(
        symptoms={
            "diarrhea": True,
            "sunken_eyes": True,
            "restless_or_irritable": True,
            "modules": ["diarrhea_dehydration"],
        },
        translated_text="SOME_DEHYDRATION: translated text.",
    )
    pipeline = AgentPipeline(llm_client=llm, vector_store=FakeStore())

    result = await pipeline.run(
        TriageInput(
            transcript="The child has diarrhea, sunken eyes, and is restless.",
            target_language="en",
            patient={"age_months": 20},
        )
    )

    assert result["classification"] == "SOME_DEHYDRATION"
    assert result["triage_color"] == "YELLOW"
    assert any(tool["tool_name"] == "assess_dehydration" for tool in result["tool_results"])


@pytest.mark.asyncio
async def test_pipeline_uses_deterministic_french_cues_and_fallback_evidence():
    llm = FakeLLM(symptoms={"modules": []})
    pipeline = AgentPipeline(llm_client=llm, vector_store=EmptyStore())

    result = await pipeline.run(
        TriageInput(
            transcript="L'enfant presente une forte fievre, vomit plusieurs fois et refuse de boire.",
            source_language="fr",
            target_language="en",
            patient={"age_months": 18},
        )
    )

    assert result["classification"] == "GENERAL_DANGER_SIGN"
    assert result["triage_color"] == "PINK"
    assert result["extracted_symptoms"]["fever"] is True
    assert result["extracted_symptoms"]["unable_to_drink_or_breastfeed"] is True
    assert result["citations"]
    assert result["citations"][0]["source"] == "imci-chart-booklet.pdf"
    assert "INSUFFICIENT_RAG_CONTEXT" not in result["safety_flags"]


@pytest.mark.asyncio
async def test_pipeline_falls_back_when_model_symptom_extraction_fails():
    llm = FailingJsonLLM(symptoms={})
    pipeline = AgentPipeline(llm_client=llm, vector_store=EmptyStore())

    result = await pipeline.run(
        TriageInput(
            transcript="L'enfant refuse de boire et a de la fievre.",
            source_language="fr",
            target_language="en",
            patient={"age_months": 18},
        )
    )

    assert result["classification"] == "GENERAL_DANGER_SIGN"
    assert result["extracted_symptoms"]["unable_to_drink_or_breastfeed"] is True
    assert result["errors"][0]["code"] == "SYMPTOM_EXTRACTION_FALLBACK"


@pytest.mark.asyncio
async def test_pipeline_classifies_fever_module_without_pneumonia():
    llm = FakeLLM(symptoms={"fever": True, "modules": ["fever"]})
    pipeline = AgentPipeline(llm_client=llm, vector_store=EmptyStore())

    result = await pipeline.run(
        TriageInput(
            transcript="The child has fever only.",
            source_language="en",
            target_language="en",
            patient={"age_months": 18},
        )
    )

    assert result["classification"] == "FEVER"
    assert result["triage_color"] == "GREEN"
    assert any(tool["tool_name"] == "assess_fever" for tool in result["tool_results"])
    assert result["citations"]


def test_verification_corrects_low_risk_output_when_danger_sign_exists():
    state = TriageState(
        transcript="The child cannot drink.",
        source_language="en",
        target_language="en",
        extracted_symptoms={"unable_to_drink_or_breastfeed": True},
        classification="COUGH_OR_COLD",
        triage_color="GREEN",
        safety_flags=[],
        citations=[{"source": "imci-chart-booklet.pdf", "page": 4, "chunk_id": "c1"}],
    )

    verified = verify_state(state)

    assert verified.triage_color == "PINK"
    assert verified.classification == "GENERAL_DANGER_SIGN"
    assert "GENERAL_DANGER_SIGN" in verified.safety_flags
