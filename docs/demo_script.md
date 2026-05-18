# ImciFlow Demo Script and Emergency Recording Guide

This guide is optimized for a 3-minute Kaggle video with less than 4 hours remaining.

The narration should be in English. The recording process can be prepared in French, but the
judges should immediately understand the story, the Gemma 4 usage, and the live product value.

## One-Hour Recording Plan

### 0-10 min: Prepare the browser

Open these tabs:

1. Live app: `https://gemma-4-hackathon.vercel.app`
2. Backend health: `https://imciflow-backend-3yhstsh2za-uc.a.run.app/health`
3. GitHub repository: `https://github.com/latifo01/GEMMA-4-HACKATHON`
4. Kaggle writeup editor

Set the browser zoom to `110%` or `125%` so the UI is readable in the video. Hide the bookmarks
bar and close unrelated tabs.

### 10-20 min: Warm up the demo

1. Open the backend health URL once.
2. Open the live app.
3. Run the primary demo case once before recording.
4. Confirm that the result shows:
   - `General Danger Sign`
   - `Gemma 4 synthesis`
   - `Safety override` or `IMCI rule` reasoning steps
   - IMCI citations
   - missing information or caregiver wording, if available

If the first call takes 20 seconds, that is acceptable. Cloud Run and Gemma 4 can have latency.
During the real recording, keep talking while the stream runs.

### 20-35 min: Record the video

Use OBS Studio, Xbox Game Bar, Loom, or any recorder that exports MP4. Record only the browser
window if possible. Target resolution: `1920x1080`.

Do not record more than three takes. The best video is the one submitted before the deadline.

### 35-55 min: Trim and upload

Trim silence at the beginning and end. Keep the final video under `3:00`. Upload to YouTube as
`Unlisted`, not private. Confirm the link opens in an incognito window without login.

### 55-60 min: Submit

Add the YouTube link, public GitHub repo, live demo, and cover image to the Kaggle writeup. Click
Submit. Do not wait until the final minutes.

## Primary Demo Case

Use this case because it reliably demonstrates safety, evidence, and clinical urgency:

```txt
A 2-year-old child has had fever and cough for 3 days. The caregiver reports fast breathing and difficulty feeding. The child is very tired. Respiratory rate is 52 breaths per minute.
```

Recommended UI settings:

- Model mode: `Auto`
- Source language: `English`
- Output language: `English`
- Child age: `24` months
- Respiratory rate: `52`

Backup French case if needed:

```txt
L'enfant presente une forte fievre, vomit plusieurs fois et refuse de boire.
```

Recommended UI settings:

- Source language: `French`
- Output language: `English`
- Child age: `18` months

## Three-Minute Video Structure

| Time | Screen action | Narration |
| --- | --- | --- |
| 0:00-0:15 | Show the app header and triage form. | "In a crisis clinic, a nurse may have one minute, limited connectivity, and a caregiver speaking another language. ImciFlow turns Gemma 4 into a grounded pediatric triage copilot for that setting." |
| 0:15-0:35 | Paste the primary case into the transcript field. Show age and respiratory rate. | "The clinician enters a messy pediatric case. This child has fever, cough, feeding difficulty, tiredness, and a respiratory rate of 52. The goal is not autonomous diagnosis. The goal is fast, safer decision support." |
| 0:35-0:55 | Point to model mode cards: Auto, Online Gemma 4, Offline local. | "The same workflow can route to online Gemma 4 for the hosted demo, or to a local Ollama deployment for offline field settings. That matters in refugee camps, rural clinics, and disaster response." |
| 0:55-1:20 | Click `Run triage`. Keep the progress stream visible. | "When I run triage, the backend streams real pipeline events: clinical extraction, IMCI retrieval, deterministic safety checks, Gemma 4 synthesis, and audit persistence." |
| 1:20-1:55 | Show the result card: classification, actions, Gemma 4 synthesis. | "The output is decision-first. Gemma 4 explains the case in clinical language, but the safety layer prevents a danger sign from being downgraded. The result gives immediate next actions instead of vague advice." |
| 1:55-2:20 | Scroll slightly to reasoning trace, citations, evidence. | "Here is the proof layer: extracted signals, deterministic IMCI rules, citations from the local evidence index, and missing information. The clinician can see why the system reached this triage level." |
| 2:20-2:40 | Show backend health tab briefly, then GitHub README. | "This is not a mockup. The frontend is deployed on Vercel, the FastAPI backend runs on Cloud Run, and the public repository documents the architecture, evaluation, and deployment path." |
| 2:40-3:00 | Return to final result card. | "ImciFlow shows how Gemma 4 can be used responsibly: multilingual, grounded, auditable, and resilient when connectivity is unreliable. It keeps the human clinician in control while reducing protocol lookup time." |

## Full Narration Script

Read this naturally. Do not rush.

```txt
In a crisis clinic, a nurse may have one minute, limited connectivity, and a caregiver speaking another language. ImciFlow turns Gemma 4 into a grounded pediatric triage copilot for that setting.

The clinician enters a messy pediatric case. This child has fever, cough, feeding difficulty, tiredness, and a respiratory rate of 52. The goal is not autonomous diagnosis. The goal is fast, safer decision support.

The same workflow can route to online Gemma 4 for the hosted demo, or to a local Ollama deployment for offline field settings. That matters in refugee camps, rural clinics, and disaster response.

When I run triage, the backend streams real pipeline events: clinical extraction, IMCI retrieval, deterministic safety checks, Gemma 4 synthesis, and audit persistence.

The output is decision-first. Gemma 4 explains the case in clinical language, but the safety layer prevents a danger sign from being downgraded. The result gives immediate next actions instead of vague advice.

Here is the proof layer: extracted signals, deterministic IMCI rules, citations from the local evidence index, and missing information. The clinician can see why the system reached this triage level.

This is not a mockup. The frontend is deployed on Vercel, the FastAPI backend runs on Cloud Run, and the public repository documents the architecture, evaluation, and deployment path.

ImciFlow shows how Gemma 4 can be used responsibly: multilingual, grounded, auditable, and resilient when connectivity is unreliable. It keeps the human clinician in control while reducing protocol lookup time.
```

## What To Show On Screen

Minimum required shots:

1. Live app URL visible in the browser.
2. Clinical case entered in the form.
3. Model routing cards showing `Auto`, `Online Gemma 4`, and `Offline local`.
4. The triage result with classification and actions.
5. Gemma 4 synthesis panel.
6. Reasoning trace and IMCI citations.
7. Backend health tab showing the API is real.
8. GitHub README showing public code and architecture.

Optional, only if time remains:

- Click the microphone icon once to show live dictation exists.
- Show the `Audit` button.
- Show the Kaggle writeup title.

## If Something Goes Wrong

### Backend latency

Do not stop the recording. Say:

```txt
The hosted model call can take a few seconds because it is running through a real deployed backend and online Gemma 4, not a pre-rendered mock.
```

### Backend unavailable

Use the already loaded result if it exists, then say:

```txt
The architecture is deployed on Cloud Run and the repository contains the reproducible local and cloud setup. The live demo link is included for judges to retry.
```

### Microphone permission fails

Do not debug on camera. Paste the prepared text and continue.

### Output looks too long

Do not scroll through every citation. Show the decision, one reasoning step, and the citations list.

## What Not To Say

Do not say:

- "It diagnoses patients."
- "It replaces doctors."
- "It is clinically validated for real use."
- "Offline mode is running on Cloud Run."
- "The model alone decides the classification."

Say instead:

- "Clinical decision support."
- "Human clinician remains in control."
- "Offline-ready architecture."
- "Gemma 4 synthesis combined with deterministic safety checks."
- "A hackathon prototype with a reproducible evaluation harness."

## Final Submission Checklist

Before clicking submit on Kaggle:

- [ ] YouTube video is under 3 minutes.
- [ ] YouTube visibility is `Unlisted`, not private.
- [ ] YouTube link opens in incognito without login.
- [ ] GitHub repository is public.
- [ ] Live demo URL is attached.
- [ ] Cover image `docs/media/kaggle-card-thumbnail.png` is uploaded.
- [ ] Writeup is under 1,500 words.
- [ ] Track is selected: `Health & Sciences`.
- [ ] Submit button has been clicked, not just saved as draft.
