# Google Cloud Run Backend Deployment

This document describes the primary backend deployment path for ImciFlow.

The recommended demo architecture is:

```txt
Vercel frontend -> Google Cloud Run backend -> Google Gemini API
```

Cloud Run is a strong fit for the hackathon demo because it gives the backend a credible HTTPS
URL, keeps the deployment inside the Google ecosystem, and supports the Gemma-first story.

## What Is Already Configured

- `apps/backend/Dockerfile` listens on the Cloud Run `PORT` environment variable.
- `cloudbuild.yaml` builds the backend Docker image and deploys it to Cloud Run.
- `.gcloudignore` and `.dockerignore` exclude local secrets, generated data, virtual
  environments, frontend build output, and large local datasets.

## One-Time Google Cloud Setup

Choose one region and keep it consistent. The default in `cloudbuild.yaml` is:

```txt
us-central1
```

Create or select a Google Cloud project, then enable the required APIs:

```powershell
gcloud services enable run.googleapis.com cloudbuild.googleapis.com artifactregistry.googleapis.com secretmanager.googleapis.com
```

Create the Artifact Registry Docker repository:

```powershell
gcloud artifacts repositories create imciflow --repository-format=docker --location=us-central1 --description="ImciFlow container images"
```

Create the Google AI secret. Do not commit the key and do not put it in Vercel:

```powershell
$keyFile = "$env:TEMP\google-ai-api-key.txt"
Set-Content -Path $keyFile -Value "YOUR_GOOGLE_AI_API_KEY" -NoNewline
gcloud secrets create google-ai-api-key --data-file=$keyFile
Remove-Item $keyFile
```

If the secret already exists, add a new version instead:

```powershell
$keyFile = "$env:TEMP\google-ai-api-key.txt"
Set-Content -Path $keyFile -Value "YOUR_GOOGLE_AI_API_KEY" -NoNewline
gcloud secrets versions add google-ai-api-key --data-file=$keyFile
Remove-Item $keyFile
```

## Deploy From Local Machine

From the repository root:

```powershell
gcloud builds submit --config cloudbuild.yaml --substitutions=_REGION=us-central1,_REPOSITORY=imciflow,_SERVICE=imciflow-backend,_IMAGE=backend
```

After deployment, Cloud Run prints a service URL similar to:

```txt
https://imciflow-backend-xxxxx-uc.a.run.app
```

Verify the backend:

```powershell
Invoke-RestMethod https://YOUR_CLOUD_RUN_URL/health
```

Expected demo-critical fields:

```json
{
  "status": "ok",
  "online_model_available": true,
  "selected_model_mode": "online"
}
```

## Deploy From GitHub

For a more professional workflow, create a Cloud Build trigger:

```txt
Cloud Build -> Triggers -> Connect Repository -> GitHub -> latifo01/GEMMA-4-HACKATHON
Configuration file: cloudbuild.yaml
Branch: main
```

Every push to `main` can then build and deploy the backend automatically.

## Vercel Frontend Configuration

After Cloud Run deploys, set this in Vercel:

```env
VITE_API_BASE_URL=https://YOUR_CLOUD_RUN_URL
```

Then redeploy the Vercel frontend.

The backend CORS origin is configured in `cloudbuild.yaml`:

```env
FRONTEND_ORIGIN=https://gemma-4-hackathon.vercel.app
```

If the Vercel domain changes, update `FRONTEND_ORIGIN` in `cloudbuild.yaml`, redeploy Cloud Run,
then redeploy Vercel.

## Demo Performance Notes

The current Cloud Run config uses:

```txt
CPU: 2
Memory: 2Gi
Timeout: 300 seconds
Concurrency: 4
Min instances: 0
Max instances: 3
```

For the jury demo, set `--min-instances` to `1` if credits allow it. This avoids cold starts and
makes the first request feel much more reliable.

## RAG Data Caveat

Cloud Run instances have an ephemeral writable filesystem. The current deployment uses `/tmp` for
runtime files:

```env
CHROMA_PATH=/tmp/chroma
RAG_VISUAL_ASSETS_PATH=/tmp/page_images
DB_PATH=/tmp/imciflow.db
```

This is acceptable for the first public backend deployment, but it does not solve persistent RAG.
For the final demo, choose one of these paths:

1. Build a small licensed demo RAG index into the Docker image.
2. Load the RAG index from Cloud Storage at startup.
3. Move vector retrieval to a managed service such as Vertex AI Vector Search or another hosted
   vector database.

Until that is done, `/health` may report `rag_index_available=false` on Cloud Run.

## Troubleshooting

If deployment fails because the Artifact Registry repository already exists, continue with the next
step.

If deployment fails on `GOOGLE_AI_API_KEY=google-ai-api-key:latest`, verify that the secret exists
and that the Cloud Run runtime service account has permission to access it.

If the frontend says the backend is offline, check:

1. `VITE_API_BASE_URL` in Vercel points to the Cloud Run URL.
2. `FRONTEND_ORIGIN` in Cloud Run matches the Vercel URL.
3. `https://YOUR_CLOUD_RUN_URL/health` returns `status: ok`.
