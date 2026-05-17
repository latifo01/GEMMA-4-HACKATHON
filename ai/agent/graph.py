from collections.abc import AsyncGenerator

from ai.agent.nodes.imci_reasoning import reason_over_imci
from ai.agent.nodes.intake import run_intake
from ai.agent.nodes.rag_retrieval import retrieve_rag_context
from ai.agent.nodes.symptom_extraction import extract_symptoms
from ai.agent.nodes.translation import translate_output
from ai.agent.nodes.verification import verify_state
from ai.agent.state import TriageInput


class AgentPipeline:
    def __init__(self, llm_client, vector_store) -> None:
        self.llm_client = llm_client
        self.vector_store = vector_store

    async def run(self, request: TriageInput) -> dict:
        if hasattr(self.llm_client, "set_preferred_mode"):
            self.llm_client.set_preferred_mode(request.model_mode)

        state = run_intake(request)
        state = await extract_symptoms(state, self.llm_client)
        state = retrieve_rag_context(state, self.vector_store)
        state = reason_over_imci(state)
        state = verify_state(state)
        state = await translate_output(state, self.llm_client)
        return state.to_result()

    async def stream(self, request: TriageInput) -> AsyncGenerator[dict, None]:
        """Yield SSE-ready events as each pipeline node starts and completes."""
        if hasattr(self.llm_client, "set_preferred_mode"):
            self.llm_client.set_preferred_mode(request.model_mode)

        state = run_intake(request)
        yield {"event": "node_completed", "node": "intake", "data": {}}

        yield {"event": "node_started", "node": "symptom_extraction"}
        state = await extract_symptoms(state, self.llm_client)
        yield {"event": "node_completed", "node": "symptom_extraction",
               "data": {"symptoms": state.extracted_symptoms}}

        yield {"event": "node_started", "node": "rag_retrieval"}
        state = retrieve_rag_context(state, self.vector_store)
        yield {"event": "node_completed", "node": "rag_retrieval",
               "data": {"citations_count": len(state.citations)}}

        yield {"event": "node_started", "node": "imci_reasoning"}
        state = reason_over_imci(state)
        yield {"event": "node_completed", "node": "imci_reasoning",
               "data": {"triage_color": state.triage_color, "classification": state.classification}}

        yield {"event": "node_started", "node": "verification"}
        state = verify_state(state)
        yield {"event": "node_completed", "node": "verification",
               "data": {"safety_flags": state.safety_flags}}

        yield {"event": "node_started", "node": "translation"}
        state = await translate_output(state, self.llm_client)
        yield {"event": "node_completed", "node": "translation", "data": {}}

        yield {"event": "result", "data": state.to_result()}
