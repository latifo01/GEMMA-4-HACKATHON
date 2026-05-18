import argparse
import asyncio
import json
import sys
from pathlib import Path
from typing import Any

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from ai.agent.graph import AgentPipeline
from ai.agent.state import TriageInput
from ai.llm.router import LLMResponse
from ai.rag.vectorstore import build_vector_store
from apps.backend.config import get_settings


class FixtureLLM:
    model_mode = "evaluation"
    model_name = "fixture-symptom-extractor"

    def __init__(self, symptoms: dict[str, Any]) -> None:
        self.symptoms = symptoms

    async def healthcheck(self) -> bool:
        return True

    async def generate_json(
        self,
        prompt: str,
        response_schema: dict[str, Any],
        temperature: float = 0.0,
    ) -> LLMResponse:
        return LLMResponse(
            text=json.dumps(self.symptoms),
            model_mode=self.model_mode,
            model_name=self.model_name,
            parsed_json=self.symptoms,
        )

    async def generate_text(self, prompt: str, temperature: float = 0.0) -> LLMResponse:
        return LLMResponse(
            text="",
            model_mode=self.model_mode,
            model_name=self.model_name,
        )


async def evaluate_case(case: dict[str, Any]) -> dict[str, Any]:
    settings = get_settings()
    pipeline = AgentPipeline(
        llm_client=FixtureLLM(case["symptoms"]),
        vector_store=build_vector_store(settings),
    )
    result = await pipeline.run(
        TriageInput(
            transcript=case["transcript"],
            source_language=case.get("source_language", "en"),
            target_language="en",
            model_mode="auto",
            patient=case.get("patient", {}),
            measurements=case.get("measurements", {}),
            context=case.get("context", {}),
        )
    )

    classification_ok = result["classification"] == case["expected_classification"]
    color_ok = result["triage_color"] == case["expected_triage_color"]
    has_citation = len(result["citations"]) > 0
    passed = classification_ok and color_ok and has_citation and result["human_review_required"] is True

    return {
        "id": case["id"],
        "passed": passed,
        "expected_classification": case["expected_classification"],
        "actual_classification": result["classification"],
        "expected_triage_color": case["expected_triage_color"],
        "actual_triage_color": result["triage_color"],
        "citation_count": len(result["citations"]),
        "top_citation": result["citations"][0] if result["citations"] else None,
        "safety_flags": result["safety_flags"],
        "missing_information": result["missing_information"],
    }


async def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate deterministic IMCI demo cases.")
    parser.add_argument(
        "--cases",
        type=Path,
        default=ROOT_DIR / "tests" / "fixtures" / "clinical_eval_cases.json",
    )
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON.")
    args = parser.parse_args()

    cases = json.loads(args.cases.read_text(encoding="utf-8"))
    results = [await evaluate_case(case) for case in cases]

    passed = sum(1 for result in results if result["passed"])
    total = len(results)
    summary = {
        "total": total,
        "passed": passed,
        "failed": total - passed,
        "pass_rate": round(passed / total, 3) if total else 0.0,
        "results": results,
    }

    if args.json:
        print(json.dumps(summary, indent=2))
    else:
        print(f"Clinical eval: {passed}/{total} passed ({summary['pass_rate']:.0%})")
        for result in results:
            status = "PASS" if result["passed"] else "FAIL"
            print(
                f"{status} {result['id']}: "
                f"{result['actual_classification']} / {result['actual_triage_color']} "
                f"citations={result['citation_count']}"
            )

    return 0 if passed == total else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
