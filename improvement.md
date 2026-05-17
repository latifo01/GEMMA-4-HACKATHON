# ImciFlow — Hackathon Improvement Plan

> **"ImciFlow est une salle de réanimation IA tenue dans la poche d'une infirmière au Soudan du Sud."**

---

## Audit : Ce qui est déjà excellent

Le projet a une base technique irréprochable pour un hackathon :

| Axe | État actuel |
|-----|-------------|
| Pipeline agent 6-nœuds | ✅ Solide — intake → symptoms → RAG → reasoning → verification → translation |
| RAG multimodal | ✅ Texte (FastEmbed) + Images (CLIP) sur les PDFs IMCI de l'OMS |
| Routing online/offline | ✅ Google AI Studio ↔ Ollama avec fallback déterministe |
| Sécurité clinique | ✅ Outils déterministes overrident le LLM sur les danger signs |
| Multilinguisme | ✅ EN/FR/AR-SD avec Whisper local |
| Vidéo respiratoire | ✅ OpenCV sur chest motion → bpm |
| Audit SQLite | ✅ Toutes les sessions loggées |

**Le vrai problème** : trois "killer features" sont **architecturalement construites** mais **pas exposées** :
1. L'endpoint SSE `/triage/run/stream` est documenté mais **absent du router** → le frontend simule des étapes factices
2. Les images IMCI sont extraites et indexées via CLIP mais **jamais affichées** dans les citations
3. La couleur de triage est calculée mais **ignorée par l'UI** — fond statique pour PINK, YELLOW et GREEN

---

## 🌟 Partie 1 : Killer Features

### Feature #1 — Streaming SSE "Live Reasoning Trace" (L'IA qui pense devant vous)

**Pourquoi c'est le "wow"** : aujourd'hui le frontend affiche 5 étapes statiques pendant 8 secondes. Avec le streaming SSE, chaque nœud du pipeline s'allume en temps réel quand Gemma commence à travailler dessus — l'effet "l'IA réfléchit" est exactement ce qui bluff les jurys.

**Backend — `ai/agent/graph.py`** : ajouter une méthode `stream()` qui yield des événements entre chaque nœud :

```python
# ai/agent/graph.py — ajouter après la méthode run()

from collections.abc import AsyncGenerator

async def stream(self, request: TriageInput) -> AsyncGenerator[dict, None]:
    """Yield SSE-ready events as the pipeline progresses."""
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
```

**Backend — `apps/backend/routers/triage.py`** : ajouter l'endpoint SSE :

```python
import json
from fastapi.responses import StreamingResponse

@router.post("/run/stream")
async def stream_triage(
    request: TriageRequest,
    db_session: AsyncSession = Depends(get_db_session),
    pipeline: AgentPipeline = Depends(get_agent_pipeline),
) -> StreamingResponse:
    request_id = str(uuid4())
    request_payload = request.model_dump(mode="json")
    audit_session = await create_session(
        db_session=db_session,
        request_payload=request_payload,
        session_id=request.session_id,
    )

    async def event_generator():
        try:
            async for event in pipeline.stream(
                TriageInput(
                    transcript=request.transcript,
                    source_language=request.source_language,
                    target_language=request.target_language,
                    model_mode=request.model_mode,
                    patient=request.patient,
                    measurements=request.measurements,
                    context=request.context,
                )
            ):
                event_type = event.pop("event", "message")
                payload = json.dumps(event)
                yield f"event: {event_type}\ndata: {payload}\n\n"

                if event_type == "result":
                    result_data = TriageResultData(
                        session_id=audit_session.session_id,
                        **event.get("data", {}),
                    ).model_dump(mode="json")
                    model_mode = result_data.get("model", {}).get("mode", "unavailable")
                    await update_session(
                        db_session=db_session,
                        session_id=audit_session.session_id,
                        status="completed",
                        result_payload=result_data,
                        errors=[],
                        model_mode=model_mode,
                    )
        except Exception as exc:
            error = {"code": "STREAM_ERROR", "message": str(exc)}
            yield f"event: error\ndata: {json.dumps(error)}\n\n"
            await update_session(
                db_session=db_session,
                session_id=audit_session.session_id,
                status="failed",
                errors=[error],
            )

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Access-Control-Allow-Origin": "*",
        },
    )
```

**Frontend — `apps/frontend/src/features/triage/useTriageStream.ts`** (nouveau fichier) :

```typescript
import { useCallback, useRef, useState } from "react";
import { env } from "../../app/env";
import type { TriageResultData } from "../../types/triage";
import type { TriageRequest } from "../../types/triage";

export type StreamNode =
  | "intake"
  | "symptom_extraction"
  | "rag_retrieval"
  | "imci_reasoning"
  | "verification"
  | "translation";

export type NodeStatus = "pending" | "running" | "completed";

export type StreamState = {
  nodes: Record<StreamNode, NodeStatus>;
  result: TriageResultData | null;
  sessionId: string | null;
  error: string | null;
  isStreaming: boolean;
};

const ALL_NODES: StreamNode[] = [
  "intake",
  "symptom_extraction",
  "rag_retrieval",
  "imci_reasoning",
  "verification",
  "translation",
];

const initialNodes = Object.fromEntries(
  ALL_NODES.map((n) => [n, "pending" as NodeStatus])
) as Record<StreamNode, NodeStatus>;

export function useTriageStream() {
  const [state, setState] = useState<StreamState>({
    nodes: { ...initialNodes },
    result: null,
    sessionId: null,
    error: null,
    isStreaming: false,
  });
  const abortRef = useRef<(() => void) | null>(null);

  const run = useCallback(async (request: TriageRequest) => {
    abortRef.current?.();

    setState({
      nodes: { ...initialNodes },
      result: null,
      sessionId: null,
      error: null,
      isStreaming: true,
    });

    let cancelled = false;
    abortRef.current = () => { cancelled = true; };

    const response = await fetch(`${env.apiBaseUrl}/triage/run/stream`, {
      method: "POST",
      headers: { "Content-Type": "application/json", "bypass-tunnel-reminder": "true" },
      body: JSON.stringify(request),
    });

    if (!response.ok || !response.body) {
      const text = await response.text().catch(() => "Stream failed");
      setState((s) => ({ ...s, isStreaming: false, error: text }));
      return;
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";

    while (true) {
      const { done, value } = await reader.read();
      if (done || cancelled) break;
      buffer += decoder.decode(value, { stream: true });

      const lines = buffer.split("\n\n");
      buffer = lines.pop() ?? "";

      for (const block of lines) {
        const eventLine = block.split("\n").find((l) => l.startsWith("event: "));
        const dataLine = block.split("\n").find((l) => l.startsWith("data: "));
        if (!eventLine || !dataLine) continue;

        const eventType = eventLine.slice(7).trim();
        const data = JSON.parse(dataLine.slice(6));

        if (eventType === "node_started") {
          setState((s) => ({
            ...s,
            nodes: { ...s.nodes, [data.node]: "running" },
          }));
        } else if (eventType === "node_completed") {
          setState((s) => ({
            ...s,
            nodes: { ...s.nodes, [data.node]: "completed" },
          }));
        } else if (eventType === "result") {
          setState((s) => ({
            ...s,
            isStreaming: false,
            result: data.data,
            sessionId: data.data?.session_id ?? null,
          }));
        } else if (eventType === "error") {
          setState((s) => ({
            ...s,
            isStreaming: false,
            error: data.message ?? "Stream error",
          }));
        }
      }
    }

    setState((s) => ({ ...s, isStreaming: false }));
  }, []);

  const reset = useCallback(() => {
    abortRef.current?.();
    setState({ nodes: { ...initialNodes }, result: null, sessionId: null, error: null, isStreaming: false });
  }, []);

  return { ...state, run, reset };
}
```

**Frontend — `TriageResult.tsx`** : remplacer le faux loader par le composant streaming réel (voir Partie 3 pour les détails UX complets).

---

### Feature #2 — IMCI Visual Evidence : montrer la page du manuel OMS

**Pourquoi c'est le "wow"** : quand l'IA recommande "Give oral rehydration therapy", et que sous la recommandation apparaît la vignette de la page 14 du guide OMS avec exactement ce tableau — c'est le "money shot" du demo. L'IA ne fabrique rien : elle cite ses sources visuellement.

**Backend — `apps/backend/main.py`** : monter le dossier d'images :

```python
from pathlib import Path
from fastapi.staticfiles import StaticFiles

# Dans create_app(), après app.include_router(video_router) :
page_images_path = Path(settings.page_images_path)
if page_images_path.exists():
    app.mount("/images", StaticFiles(directory=str(page_images_path)), name="page_images")
```

**Backend — `ai/agent/nodes/rag_retrieval.py`** : enrichir `to_citation()` avec l'URL d'image :

```python
import os

PAGE_IMAGES_BASE_URL = os.getenv("PAGE_IMAGES_BASE_URL", "/images")
PAGE_IMAGES_DIR = os.getenv("RAG_PAGE_IMAGES_PATH", "./data/page_images")

def to_citation(item: dict[str, Any]) -> dict[str, Any]:
    page = item.get("page")
    source = item.get("source", "")
    # Convention: page_images/{source_stem}_page_{page}.png
    image_url = None
    if page is not None:
        stem = source.replace(".pdf", "").replace(" ", "_")
        candidate = f"{PAGE_IMAGES_DIR}/{stem}_page_{page}.png"
        if os.path.exists(candidate):
            image_url = f"{PAGE_IMAGES_BASE_URL}/{stem}_page_{page}.png"
    return {
        "source": source,
        "page": page,
        "chunk_id": item["chunk_id"],
        "relevance_score": item.get("relevance_score", 0.0),
        "quote": item.get("text", "")[:240],
        "image_url": image_url,
    }
```

**Frontend — `TriageResult.tsx`** : afficher les vignettes IMCI dans `formatCitation()` :

```tsx
function CitationCard({ citation, index }: { citation: Record<string, unknown>; index: number }) {
  const title = String(citation.title ?? citation.source ?? "IMCI reference");
  const page = citation.page ? ` · page ${String(citation.page)}` : "";
  const excerpt = String(citation.text ?? citation.excerpt ?? citation.quote ?? "");
  const imageUrl = citation.image_url ? String(citation.image_url) : null;
  const score = typeof citation.relevance_score === "number" ? citation.relevance_score : null;

  return (
    <div className="rounded-md border border-slate-200 overflow-hidden text-xs leading-5 text-slate-700">
      {imageUrl && (
        <img
          src={imageUrl}
          alt={`IMCI page ${citation.page ?? ""}`}
          className="w-full max-h-36 object-cover object-top border-b border-slate-200"
        />
      )}
      <div className="px-3 py-2">
        <span className="font-semibold">{title}{page}</span>
        {score !== null && (
          <div className="mt-1 h-1 w-full rounded bg-slate-200">
            <div className="h-1 rounded bg-blue-400" style={{ width: `${Math.round(score * 100)}%` }} />
          </div>
        )}
        {excerpt && <p className="mt-1">{excerpt.slice(0, 180)}</p>}
      </div>
    </div>
  );
}
```

---

## 💻 Partie 2 : Améliorations Architecturales

### A — Gemma 4 Native Function Calling (montrer la vraie puissance du modèle)

Actuellement, les outils cliniques sont appelés de manière conditionnelle (si symptôme X → appeler outil Y). Avec le function calling natif de Gemma 4, c'est le **modèle qui décide quels outils invoquer** — exactement comme le ferait un médecin qui choisit ses examens.

**Fichier** : `ai/agent/nodes/imci_reasoning.py` — variante avec function calling :

```python
# Schéma des outils pour Gemma 4 function calling
CLINICAL_TOOLS_SCHEMA = [
    {
        "name": "detect_danger_signs",
        "description": "Check for general IMCI danger signs (unable to drink, convulsions, lethargic, vomits everything)",
        "parameters": {
            "type": "object",
            "properties": {
                "unable_to_drink_or_breastfeed": {"type": "boolean"},
                "vomits_everything": {"type": "boolean"},
                "convulsions": {"type": "boolean"},
                "lethargic_or_unconscious": {"type": "boolean"},
            },
            "required": ["unable_to_drink_or_breastfeed", "vomits_everything", "convulsions", "lethargic_or_unconscious"],
        },
    },
    {
        "name": "classify_pneumonia",
        "description": "Classify cough/difficult breathing severity per IMCI respiratory thresholds",
        "parameters": {
            "type": "object",
            "properties": {
                "age_months": {"type": "number"},
                "respiratory_rate_bpm": {"type": "number"},
                "cough_or_difficult_breathing": {"type": "boolean"},
                "chest_indrawing": {"type": "boolean"},
                "stridor_in_calm_child": {"type": "boolean"},
                "general_danger_sign": {"type": "boolean"},
            },
            "required": ["cough_or_difficult_breathing"],
        },
    },
    {
        "name": "assess_dehydration",
        "description": "Assess dehydration level from diarrhea symptoms",
        "parameters": {
            "type": "object",
            "properties": {
                "lethargic_or_unconscious": {"type": "boolean"},
                "sunken_eyes": {"type": "boolean"},
                "unable_to_drink_or_drinking_poorly": {"type": "boolean"},
                "skin_pinch_very_slow": {"type": "boolean"},
                "restless_or_irritable": {"type": "boolean"},
                "drinks_eagerly_or_thirsty": {"type": "boolean"},
                "skin_pinch_slow": {"type": "boolean"},
            },
        },
    },
    {
        "name": "assess_fever",
        "description": "Assess fever risk level and malaria risk",
        "parameters": {
            "type": "object",
            "properties": {
                "fever": {"type": "boolean"},
                "temperature_celsius": {"type": "number"},
                "fever_duration_days": {"type": "number"},
                "general_danger_sign": {"type": "boolean"},
            },
        },
    },
]

# Usage dans GemmaOnlineClient (google-genai SDK)
async def reason_with_function_calling(llm_client, state: TriageState) -> TriageState:
    from google.genai import types

    tools = [types.Tool(function_declarations=[
        types.FunctionDeclaration(**tool) for tool in CLINICAL_TOOLS_SCHEMA
    ])]

    prompt = f"""
    You are an IMCI clinical decision-support system.
    Patient: {state.patient.get('age_months')} months old.
    Symptoms extracted: {state.extracted_symptoms}
    Measurements: {state.measurements}
    IMCI context: {state.rag_context[0].get('text', '') if state.rag_context else 'No context retrieved'}

    Use the available tools to assess this child's condition. Call all relevant tools.
    """

    response = await llm_client._generate_content(
        model=llm_client.model_name,
        contents=prompt,
        config=types.GenerateContentConfig(tools=tools, tool_config=types.ToolConfig(
            function_calling_config=types.FunctionCallingConfig(mode="AUTO")
        )),
    )

    # Execute each function call and collect results
    tool_dispatch = {
        "detect_danger_signs": detect_danger_signs,
        "classify_pneumonia": classify_pneumonia,
        "assess_dehydration": assess_dehydration,
        "assess_fever": assess_fever,
    }

    for part in response.candidates[0].content.parts:
        if part.function_call:
            fn_name = part.function_call.name
            fn_args = dict(part.function_call.args)
            if fn_name in tool_dispatch:
                result = tool_dispatch[fn_name](**fn_args)
                state.tool_results.append(result)

    return state
```

> **Note** : cette variante function calling peut coexister avec la version déterministe actuelle via un flag `USE_GEMMA_FUNCTION_CALLING=true` dans `.env`. Le fallback déterministe reste le défaut pour robustesse en mode offline.

---

### B — Contextual Compression RAG (Reranker LLM léger)

Le système récupère les top-5 chunks, mais certains sont peu pertinents. Un reranker LLM post-retrieval améliore la précision des citations sans toucher à l'index.

**Fichier** : `ai/rag/vectorstore.py` — ajouter `rerank()` :

```python
async def rerank(self, chunks: list[dict], query: str, llm_client, top_k: int = 3) -> list[dict]:
    """Use Gemma to rerank retrieved chunks by clinical relevance."""
    if len(chunks) <= top_k:
        return chunks

    chunks_text = "\n\n".join(
        f"[{i}] {chunk.get('text', '')[:200]}" for i, chunk in enumerate(chunks)
    )
    prompt = (
        f"Query: {query}\n\n"
        f"Chunks:\n{chunks_text}\n\n"
        f"Return a JSON array of the {top_k} most clinically relevant chunk indices. "
        f"Format: {{\"indices\": [0, 2, 4]}}"
    )

    schema = {"type": "object", "properties": {"indices": {"type": "array", "items": {"type": "integer"}}}}
    response = await llm_client.generate_json(prompt, response_schema=schema)
    indices = (response.parsed_json or {}).get("indices", list(range(top_k)))
    valid = [i for i in indices if 0 <= i < len(chunks)][:top_k]
    return [chunks[i] for i in valid] if valid else chunks[:top_k]
```

---

### C — Follow-up conversationnel (continuer le dialogue clinique)

Après un triage, l'infirmière peut poser des questions de suivi ("Et si la fièvre dure 5 jours ?", "Ce protocole change-t-il si c'est un nourrisson de 2 mois ?"). Cela transforme l'outil d'un formulaire en un **assistant clinique dialogique**.

**Nouveau fichier** : `apps/backend/routers/followup.py` :

```python
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from ai.llm.router import LLMRouter
from apps.backend.config import Settings, get_settings
from apps.backend.database import get_db_session
from apps.backend.services.session_service import get_session

router = APIRouter(prefix="/triage", tags=["triage"])

class FollowUpRequest(BaseModel):
    session_id: str
    question: str
    target_language: str = "en"

@router.post("/followup")
async def followup(
    request: FollowUpRequest,
    db_session: AsyncSession = Depends(get_db_session),
    settings: Settings = Depends(get_settings),
):
    session = await get_session(db_session, request.session_id)
    prior_result = session.result_payload if session else {}

    prompt = f"""
    Previous triage result:
    - Classification: {prior_result.get('classification', 'unknown')}
    - Triage color: {prior_result.get('triage_color', 'unknown')}
    - Recommendations: {prior_result.get('recommendations', [])}
    - Reasoning: {prior_result.get('reasoning', '')}

    Follow-up question from the clinician: {request.question}

    Answer concisely using IMCI guidelines. Keep the response under 3 sentences.
    Respond in: {request.target_language}
    """

    llm = LLMRouter(settings)
    response = await llm.generate_text(prompt)
    return {"data": {"answer": response.text, "session_id": request.session_id}}
```

**Frontend** : ajouter `FollowUpChat.tsx` sous `TriageResult` quand un résultat est disponible :

```tsx
// apps/frontend/src/features/triage/FollowUpChat.tsx
import { useState } from "react";
import { Button } from "../../components/ui/Button";
import { Field } from "../../components/ui/Field";
import { apiJson } from "../../services/api/client";

export function FollowUpChat({ sessionId, targetLanguage }: { sessionId: string; targetLanguage: string }) {
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  async function handleAsk() {
    if (!question.trim()) return;
    setIsLoading(true);
    try {
      const res = await apiJson<{ data: { answer: string } }>("/triage/followup", {
        session_id: sessionId,
        question,
        target_language: targetLanguage,
      });
      setAnswer(res.data.answer);
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <div className="grid gap-3 rounded-md border border-slate-200 bg-white p-4">
      <h3 className="text-sm font-semibold text-slate-800">Ask a follow-up</h3>
      <Field label="">
        <input
          className="min-h-10 w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
          placeholder="What if fever has been 5 days?..."
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && handleAsk()}
        />
      </Field>
      <Button type="button" variant="primary" onClick={handleAsk} disabled={isLoading || !question.trim()}>
        {isLoading ? "Asking Gemma..." : "Ask"}
      </Button>
      {answer && (
        <p className="rounded-md border border-green-200 bg-green-50 px-3 py-2 text-sm leading-6 text-green-900">
          {answer}
        </p>
      )}
    </div>
  );
}
```

---

## 🎨 Partie 3 : Révolution de l'Expérience Utilisateur

### A — Triage Color Bleed (CSS conditionnel, impact maximal)

**Fichier** : `apps/frontend/src/features/triage/TriageResult.tsx`

Remplacer la classe fixe `border-slate-200 bg-white` par des classes dynamiques basées sur `triage_color` :

```tsx
const sectionStyle: Record<string, string> = {
  pink: "border-red-400 bg-red-50 shadow-red-100",
  red:  "border-red-400 bg-red-50 shadow-red-100",
  yellow: "border-amber-400 bg-amber-50 shadow-amber-100",
  green: "border-green-400 bg-green-50 shadow-green-100",
};

const badgePulse: Record<string, string> = {
  pink: "animate-pulse",
  red:  "animate-pulse",
};

// Dans le return :
const colorKey = result.triage_color?.toLowerCase() ?? "neutral";
const sectionClass = sectionStyle[colorKey] ?? "border-slate-200 bg-white";
const pulseClass = badgePulse[colorKey] ?? "";

<section className={`grid gap-4 rounded-md border p-5 shadow-subtle transition-colors duration-500 ${sectionClass}`}>
  <Badge tone={tone} className={pulseClass}>{result.triage_color}</Badge>
  ...
```

### B — Reasoning Trace Animée (SSE + transitions CSS)

Remplacer le faux loader statique dans `TriageResult.tsx` par un composant qui reflète l'état SSE réel :

```tsx
const NODE_LABELS: Record<string, string> = {
  intake: "Validating patient data",
  symptom_extraction: "Extracting clinical signals (Gemma 4)",
  rag_retrieval: "Searching IMCI guidelines",
  imci_reasoning: "Running deterministic safety tools",
  verification: "Checking danger signs",
  translation: "Generating multilingual output",
};

function StreamingTrace({ nodes }: { nodes: Record<string, "pending" | "running" | "completed"> }) {
  return (
    <ol className="grid content-start gap-2">
      {Object.entries(NODE_LABELS).map(([node, label], index) => {
        const status = nodes[node] ?? "pending";
        const stateClass = {
          pending: "bg-slate-50 border-slate-200 text-slate-400",
          running: "bg-blue-50 border-blue-300 text-blue-800 animate-pulse",
          completed: "bg-green-50 border-green-300 text-green-800",
        }[status];
        const icon = { pending: "○", running: "◎", completed: "✓" }[status];
        return (
          <li key={node} className={`flex items-center gap-3 rounded-md border px-3 py-2 text-sm transition-all duration-300 ${stateClass}`}>
            <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-md font-bold text-xs">
              {status === "completed" ? icon : index + 1}
            </span>
            <span>{label}</span>
          </li>
        );
      })}
    </ol>
  );
}
```

### C — RTL Support pour l'arabe

```tsx
// Dans TriageResult.tsx — section Reasoning
const isRTL = result.model?.target_language === "ar-SD" ||
              (result.translated_output && /[؀-ۿ]/.test(result.translated_output.slice(0, 20)));

<p
  dir={isRTL ? "rtl" : "ltr"}
  className="whitespace-pre-wrap rounded-md border border-slate-200 bg-slate-50 px-3 py-2 text-sm leading-6"
>
  {result.translated_output || result.reasoning}
</p>
```

### D — Confidence Meter sur les citations

```tsx
// Dans CitationCard (voir Partie 1 Feature #2)
{score !== null && (
  <div className="mt-1.5 flex items-center gap-2">
    <div className="h-1 flex-1 rounded bg-slate-200">
      <div
        className="h-1 rounded bg-blue-400 transition-all duration-500"
        style={{ width: `${Math.round(score * 100)}%` }}
      />
    </div>
    <span className="text-xs text-slate-400">{Math.round(score * 100)}%</span>
  </div>
)}
```

---

## 🚀 Partie 4 : Le "Winning Pitch" Angle

### Tagline principale
> **"The AI triage system that works when Google goes down."**

### Architecture du demo (3 actes — 3 minutes)

**Acte 1 — Le problème (30s)**
> "Dans 50% des pays à revenu faible, il n'y a qu'un pédiatre pour 200 000 enfants. Une infirmière seule, sans connexion, doit décider en 2 minutes si un enfant de 18 mois avec fièvre et toux doit être référé à l'hôpital distant de 3 heures ou traité sur place."

**Acte 2 — La démo (2 min)**
1. Charger le cas "Danger sign" (transcript en français)
2. Switcher en mode **Online** → lancer le triage → montrer les **6 étapes SSE qui s'allument** en temps réel
3. Résultat PINK apparaît → le **fond de l'UI devient rouge** → badge pulse
4. Montrer la **vignette IMCI** à côté de la citation : "Page 14 du guide OMS"
5. Switcher en mode **Offline** → même cas → même résultat → *"Même pipeline, zéro cloud"*
6. Changer la langue output → Sudanese Arabic → RTL s'active automatiquement

**Acte 3 — L'argument technique (30s)**
> "Nous sommes les seuls à combiner : pipeline Gemma 4 streamé, RAG multimodal avec CLIP sur les PDFs OMS, outils déterministes qui ne peuvent pas halluciner sur les danger signs, et un fallback offline total avec Ollama. La sécurité clinique est architecturalement garantie, pas promue."

### Mots-clés pour marquer le jury

| Trigger | Ce que ça signifie pour le jury |
|---------|--------------------------------|
| **"offline-first"** | Résilience réelle, pas juste un toggle |
| **"grounded clinical AI"** | Hallucination mitigation avec preuves visuelles |
| **"WHO IMCI protocol"** | Validation par une institution de référence mondiale |
| **"zero LLM override on danger signs"** | Safety architecture au niveau système |
| **"Gemma 4 function calling"** | Usage avancé du modèle, pas juste un chatbot |
| **"deterministic safety layer"** | Les jurys techniques adorent ce mot |

### Le "money shot" de demo

Le moment le plus fort : faire un triage pour un enfant avec danger signs, et montrer **côte-à-côte** :
- À gauche : le streaming des 6 nœuds qui s'allument un par un
- À droite : le fond UI qui devient progressivement rouge
- En bas : la page 7 du guide OMS en miniature, avec une barre bleue à 94% de pertinence

**"Voici Gemma 4 qui sauve une vie — en temps réel, en arabe, sans connexion."**

---

## Ordre de priorité pour la fin du hackathon

| Priorité | Changement | Impact demo | Effort |
|----------|-----------|-------------|--------|
| 🔴 P0 | SSE streaming backend + frontend trace animée | ⭐⭐⭐⭐⭐ | 3h |
| 🔴 P0 | Triage color bleed (CSS conditionnel) | ⭐⭐⭐⭐ | 30min |
| 🟡 P1 | IMCI visual citations (static files + image_url) | ⭐⭐⭐⭐⭐ | 2h |
| 🟡 P1 | RTL arabe | ⭐⭐⭐ | 15min |
| 🟢 P2 | Follow-up conversationnel | ⭐⭐⭐⭐ | 2h |
| 🟢 P2 | Gemma 4 function calling | ⭐⭐⭐⭐ | 2h |
| 🔵 P3 | Confidence meter citations | ⭐⭐⭐ | 20min |
| 🔵 P3 | Contextual compression reranker | ⭐⭐⭐ | 1h |
