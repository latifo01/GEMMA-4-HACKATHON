# ImciFlow Frontend Implementation Plan

## 1. Purpose

This document is the execution plan for the ImciFlow frontend.

The backend is already functional. The frontend must now turn the backend capabilities into a
polished, demo-ready product that clearly shows Gemma 4 as the main reasoning engine while also
showing offline/local adaptability for low-connectivity deployments.

Deployment target:

- Frontend: Vercel.
- Source control: GitHub.
- Deployment flow: push to GitHub, Vercel deploys from the frontend project.

## 2. Product Positioning

ImciFlow is a clinical decision-support interface for pediatric triage in low-resource settings.
It is not a diagnosis tool.

The frontend must communicate this clearly:

- Gemma 4 powers structured reasoning and multilingual explanation.
- IMCI retrieval grounds recommendations with citations.
- Deterministic safety tools protect against unsafe model output.
- Offline/local mode is an architectural capability for field deployments where internet access
  is unreliable.
- On this development laptop, offline mode may use a small local Ollama model only to validate
  fallback mechanics. The main hackathon proof remains online Gemma 4.

## 3. Verified Backend Capabilities

Current backend endpoints:

```txt
GET  /health
POST /audio/transcribe
POST /video/analyze
POST /triage/run
GET  /sessions/{session_id}
```

Important backend facts:

- `/triage/run` accepts `model_mode: "auto" | "online" | "offline"`.
- `/triage/run` returns `model.mode`, `model.name`, citations, classification, triage color,
  recommendations, safety flags, and `session_id`.
- `/audio/transcribe` accepts `multipart/form-data`.
- `/video/analyze` accepts `multipart/form-data`.
- `/sessions/{session_id}` returns the stored audit session.
- `/triage/run/stream` is documented but not currently implemented. Do not build an SSE UI until
  that endpoint exists.

Before frontend deployment, verify:

- Backend CORS allows the Vercel frontend origin.
- Deployed backend has `GOOGLE_AI_API_KEY`.
- Deployed backend has a populated RAG index.
- Deployed backend `/health` returns `selected_model_mode: "online"` for the main demo.

## 4. UX Principles

Use the Laws of Simplicity:

- Reduce: one main workflow, no dashboard bloat.
- Organize: input on the left, result on the right.
- Time: clear loading states and visible progress.
- Learn: labels should be self-explanatory.
- Differences: make online/offline mode visibly distinct.
- Context: show citations and audit id without overwhelming the user.
- Emotion: calm, trustworthy, not flashy.

Product rules:

- The app opens directly into the triage workspace.
- No marketing landing page for MVP.
- No nested cards.
- No decorative gradients or visual noise.
- Keep the interface dense enough for real work, but easy for judges to follow.
- Always show human review requirement.

## 5. Recommended Stack

Use:

- Vite.
- React.
- TypeScript.
- Tailwind CSS.
- TanStack Query.
- React Hook Form.
- Zod.
- Lucide React.
- Vitest.
- React Testing Library.
- Playwright.

Avoid:

- Redux for MVP.
- Complex routing.
- Heavy UI frameworks.
- Direct `fetch` calls inside components.

## 6. Frontend App Location

Create:

```txt
apps/frontend/
```

The repo will then contain:

```txt
apps/
  backend/
  frontend/
```

Vercel project root should be:

```txt
apps/frontend
```

Vercel build command:

```txt
npm run build
```

Vercel output directory:

```txt
dist
```

## 7. Environment Variables

Create:

```txt
apps/frontend/.env.example
```

Required:

```txt
VITE_API_BASE_URL=http://localhost:8000
```

For Vercel production:

```txt
VITE_API_BASE_URL=https://YOUR_BACKEND_DOMAIN
```

Rules:

- Never expose backend secrets in frontend env variables.
- `GOOGLE_AI_API_KEY` must stay backend-only.
- The frontend only needs the backend base URL.

## 8. Folder Structure

Use this structure:

```txt
apps/frontend/
  index.html
  package.json
  vite.config.ts
  tsconfig.json
  .env.example
  src/
    main.tsx
    App.tsx
    app/
      env.ts
      queryClient.ts
    layouts/
      AppShell.tsx
    pages/
      TriagePage.tsx
      SessionPage.tsx
    components/
      ui/
        Alert.tsx
        Badge.tsx
        Button.tsx
        Field.tsx
        Spinner.tsx
        Tabs.tsx
      shared/
        AppHeader.tsx
        BackendStatus.tsx
        LanguageSelector.tsx
        ModeSelector.tsx
    features/
      health/
        useBackendHealth.ts
      triage/
        TriageWorkspace.tsx
        TriageForm.tsx
        PatientPanel.tsx
        TranscriptInput.tsx
        TriageResult.tsx
        RecommendationsPanel.tsx
        CitationsPanel.tsx
        SafetyPanel.tsx
        AuditPanel.tsx
        useTriageRun.ts
      audio/
        AudioUpload.tsx
        AudioRecorder.tsx
        TranscriptPreview.tsx
        useAudioTranscription.ts
      video/
        VideoUpload.tsx
        RespiratoryRatePanel.tsx
        useVideoAnalysis.ts
    services/
      api/
        client.ts
        health.ts
        audio.ts
        video.ts
        triage.ts
        sessions.ts
    types/
      api.ts
      health.ts
      media.ts
      triage.ts
      sessions.ts
    lib/
      cn.ts
      errors.ts
      files.ts
      format.ts
```

## 9. Page Structure

### Triage Page

Route:

```txt
/
```

Layout:

```txt
Header:
  ImciFlow
  Backend status
  Selected backend model status

Main:
  Left workflow panel:
    Mode selector
    Language selectors
    Patient age
    Transcript input
    Audio upload or recorder
    Optional video upload
    Run triage button

  Right result panel:
    Empty state
    Loading state
    Result state
    Citations
    Safety flags
    Audit link
```

### Session Page

Route:

```txt
/session/:sessionId
```

Purpose:

- Show the persisted audit session returned by `/sessions/{session_id}`.

## 10. API Types

Create shared envelope types:

```ts
export type ApiEnvelope<T> = {
  data: T;
  meta: {
    request_id: string;
    model_mode?: "online" | "offline" | "unavailable";
    duration_ms?: number;
  };
};

export type ApiErrorEnvelope = {
  error: {
    code: string;
    message: string;
    details?: unknown;
  };
  meta?: {
    request_id?: string;
  };
};
```

Core frontend model types:

```ts
export type ModelMode = "auto" | "online" | "offline";
export type SourceLanguage = "auto" | "en" | "fr" | "ar-SD";
export type TargetLanguage = "en" | "fr" | "ar-SD";
```

## 11. API Service Layer

Create one API client:

```ts
// src/services/api/client.ts
import { env } from "../../app/env";
import { normalizeApiError } from "../../lib/errors";

export async function apiFetch<T>(path: string, options: RequestInit = {}): Promise<T> {
  const response = await fetch(`${env.apiBaseUrl}${path}`, options);
  const payload = await response.json().catch(() => null);

  if (!response.ok) {
    throw normalizeApiError(payload, response.status);
  }

  return payload as T;
}
```

Rules:

- No component should call `fetch` directly.
- Multipart services must use `FormData`.
- Do not set `Content-Type` manually for `FormData`.

Services to implement:

```txt
health.ts    -> getHealth()
audio.ts     -> transcribeAudio(file, sourceLanguage)
video.ts     -> analyzeVideo(file, ageMonths)
triage.ts    -> runTriage(payload)
sessions.ts  -> getSession(sessionId)
```

## 12. State Management

Use TanStack Query for server state:

- health query;
- audio transcription mutation;
- video analysis mutation;
- triage mutation;
- session query.

Use React local state for form values:

- selected model mode;
- source language;
- target language;
- transcript;
- patient age;
- respiratory rate;
- selected media files.

Do not add global state unless a concrete cross-page need appears.

## 13. Main Workflow State

Minimum state:

```ts
const [modelMode, setModelMode] = useState<ModelMode>("auto");
const [sourceLanguage, setSourceLanguage] = useState<SourceLanguage>("auto");
const [targetLanguage, setTargetLanguage] = useState<TargetLanguage>("en");
const [ageMonths, setAgeMonths] = useState<number | null>(18);
const [transcript, setTranscript] = useState("");
const [respiratoryRateBpm, setRespiratoryRateBpm] = useState<number | null>(null);
```

Submit payload:

```ts
{
  transcript,
  source_language: sourceLanguage,
  target_language: targetLanguage,
  model_mode: modelMode,
  patient: {
    age_months: ageMonths,
    sex: "unknown"
  },
  measurements: {
    respiratory_rate_bpm: respiratoryRateBpm
  },
  context: {
    setting: "low_resource_clinic",
    frontend: "vercel_demo"
  }
}
```

## 14. Mode Selector Requirements

Labels:

- `Auto`
- `Online Gemma 4`
- `Offline local`

Behavior:

- `Auto` is default.
- `Online Gemma 4` sends `model_mode: "online"`.
- `Offline local` sends `model_mode: "offline"`.

Health guidance:

- If online unavailable, show warning near `Online Gemma 4`.
- If offline unavailable, show warning near `Offline local`.
- Do not disable unavailable modes by default; allow user to choose and let backend return a clear
  `MODEL_UNAVAILABLE` error. This is better for demo transparency.

## 15. Audio Requirements

Accepted MIME types:

```txt
audio/webm
audio/wav
audio/mpeg
audio/mp4
```

Max file size:

```txt
25 MB
```

MVP:

- Audio upload.

Optional:

- Browser recorder with `MediaRecorder`.

After successful transcription:

- Fill transcript textarea.
- Show detected language.
- Show duration.
- Allow user to edit transcript before triage.

## 16. Video Requirements

Accepted MIME types:

```txt
video/mp4
video/webm
video/quicktime
```

Max file size:

```txt
80 MB
```

Behavior:

- Video is optional.
- If video succeeds and returns `respiratory_rate_bpm`, pass it to triage.
- If video returns `null`, show uncertainty and allow triage to continue.
- Label video result as supportive evidence only.

## 17. Result UI Requirements

Show:

- triage color;
- classification;
- human review required;
- model mode;
- model name;
- recommendations;
- reasoning;
- translated output;
- safety flags;
- citations;
- session id;
- API duration if available.

Triage color display:

- `RED`: urgent / high risk.
- `YELLOW`: clinical assessment / treatment path.
- `GREEN`: lower-risk guidance.
- unknown: neutral.

Do not overclaim diagnosis.

Always include:

```txt
Clinical decision support only. Final decisions remain with qualified medical staff.
```

## 18. Loading States

Health:

- "Checking backend..."

Audio:

- "Transcribing audio..."

Video:

- "Analyzing respiratory video..."

Triage:

Use a step list:

```txt
Preparing case
Retrieving IMCI guidance
Running Gemma reasoning
Applying safety checks
Saving audit session
```

Since backend streaming is not implemented, animate these as local optimistic steps.

## 19. Error Handling

Normalize backend errors into:

```ts
type AppError = {
  code: string;
  message: string;
  status?: number;
  requestId?: string;
  details?: unknown;
};
```

Messages:

- `MODEL_UNAVAILABLE`: "The selected model mode is not available. Try Auto or another mode."
- `VALIDATION_ERROR`: "Some input is invalid. Please review the form."
- `TRANSCRIPTION_FAILED`: "Audio transcription failed. You can type the transcript manually."
- `VIDEO_ANALYSIS_FAILED`: "Video analysis failed. You can continue without video."
- `TRIAGE_VERIFICATION_FAILED`: "The triage workflow failed a safety check. Please retry."
- network error: "Backend is unreachable. Check the API URL or backend deployment."

Show request id when available.

## 20. MVP Build Steps

### Step 1: Scaffold

```bash
npm create vite@latest apps/frontend -- --template react-ts
cd apps/frontend
npm install
```

### Step 2: Install dependencies

```bash
npm install @tanstack/react-query react-hook-form zod @hookform/resolvers lucide-react clsx tailwind-merge
npm install -D tailwindcss postcss autoprefixer vitest @testing-library/react @testing-library/jest-dom playwright
```

### Step 3: Configure Tailwind

```bash
npx tailwindcss init -p
```

### Step 4: Add env validation

Create `src/app/env.ts`.

It must throw a clear error if `VITE_API_BASE_URL` is missing.

### Step 5: Implement API layer

Implement all files under:

```txt
src/services/api/
```

### Step 6: Implement health bar

Call:

```txt
GET /health
```

Display:

- backend available;
- online model availability;
- offline model availability;
- selected backend model;
- RAG availability.

### Step 7: Implement triage form

Must include:

- mode selector;
- source language;
- target language;
- patient age;
- transcript;
- run button.

### Step 8: Implement audio upload

Call:

```txt
POST /audio/transcribe
```

Then fill transcript.

### Step 9: Implement video upload

Call:

```txt
POST /video/analyze
```

Then store respiratory rate.

### Step 10: Implement triage result

Call:

```txt
POST /triage/run
```

Render result panels.

### Step 11: Implement session page

Call:

```txt
GET /sessions/{session_id}
```

## 21. Local Development Commands

Backend:

```powershell
docker compose up -d backend
```

Frontend:

```bash
cd apps/frontend
cp .env.example .env.local
npm run dev
```

Expected local URLs:

```txt
Frontend: http://localhost:5173
Backend:  http://localhost:8000
```

## 22. Testing Plan

Unit tests:

```bash
npm run test
```

Typecheck:

```bash
npm run typecheck
```

Production build:

```bash
npm run build
```

Playwright:

```bash
npx playwright test
```

Manual test checklist:

- Backend unavailable state works.
- Health state works.
- Mode selector sends correct payload.
- Text-only triage works.
- Audio transcription fills transcript.
- Video analysis fills respiratory rate.
- Triage result displays citations.
- Session link opens.
- `MODEL_UNAVAILABLE` displays useful message.
- Mobile layout is usable.

## 23. Vercel Deployment Via GitHub

### Step 1: Push repo to GitHub

Make sure `.env` is not committed.

### Step 2: Import project in Vercel

Vercel settings:

```txt
Framework Preset: Vite
Root Directory: apps/frontend
Build Command: npm run build
Output Directory: dist
Install Command: npm install
```

### Step 3: Add Vercel environment variable

In Vercel project settings:

```txt
VITE_API_BASE_URL=https://YOUR_BACKEND_DOMAIN
```

### Step 4: Deploy

Vercel deploys automatically on push to the selected GitHub branch.

### Step 5: Verify deployed frontend

Open the deployed Vercel URL in an incognito browser.

Verify:

- `/health` loads through frontend.
- triage text-only run works.
- citations render.
- session id renders.

## 24. Backend Requirements For Vercel Frontend

Because Vercel frontend and backend are on different origins, backend must support CORS.

Before deployment, verify backend has CORS middleware with:

```txt
FRONTEND_ORIGIN=https://YOUR_VERCEL_DOMAIN
```

Allowed methods:

```txt
GET, POST, OPTIONS
```

Allowed headers:

```txt
Content-Type
```

If CORS is missing, the frontend will work locally with same-machine tests but fail on Vercel.

## 25. Demo Script For Jury

Recommended demo:

1. Open Vercel app.
2. Show backend status: online Gemma 4 available.
3. Select `Online Gemma 4`.
4. Enter sample transcript:

```txt
Mother says the 18-month-old child has cough and fast breathing. The child can drink.
```

5. Upload optional respiratory video or use manually entered respiratory rate if video is skipped.
6. Run triage.
7. Show:
   - model used: Gemma 4;
   - classification;
   - triage color;
   - citations;
   - safety flags;
   - audit session.
8. Switch to `Offline local` and explain field deployment:
   - in refugee camps, a local inference machine can run the offline model;
   - the same interface and same endpoint work without changing clinical workflow.

## 26. Winning Criteria

The frontend is successful when a judge can understand in under 30 seconds:

- what problem ImciFlow solves;
- where Gemma 4 is used;
- how the result is grounded;
- why offline mode matters;
- why the system is safe and auditable.

## 27. Definition Of Done

Frontend MVP is done when:

- Vercel deployment is live.
- `VITE_API_BASE_URL` points to deployed backend.
- Main triage flow works.
- Online Gemma 4 run works.
- Result includes citations.
- Session audit opens.
- Error states are graceful.
- Mobile and desktop layouts are usable.
- README includes frontend run/deployment instructions.
- Demo script has been rehearsed at least twice.
