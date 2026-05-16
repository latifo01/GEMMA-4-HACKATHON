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
