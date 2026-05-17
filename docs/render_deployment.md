# Render Backend Deployment

This document describes the Render deployment path for the ImciFlow backend.

## Why Render

Render gives the backend a stable public HTTPS URL under `onrender.com`, which is more credible
for a jury demo than a local tunnel.

The frontend remains on Vercel.

## Service Type

Create a Render Web Service from GitHub:

```txt
Repository: latifo01/GEMMA-4-HACKATHON
Runtime: Docker
Dockerfile Path: apps/backend/Dockerfile
Docker Context: .
Health Check Path: /health
```

The Dockerfile listens on Render's `PORT` environment variable.

For a jury demo, prefer a paid Render instance type if possible. Free web services can spin down
after inactivity, which makes the first request slow and can make the product look unreliable.

## Required Environment Variables

Set these in Render:

```env
APP_ENV=production
GOOGLE_AI_API_KEY=your_google_ai_key
GEMMA_ONLINE_MODEL=models/gemma-4-26b-a4b-it
FRONTEND_ORIGIN=https://gemma-4-hackathon.vercel.app
CHROMA_PATH=/app/data/chroma
RAG_VISUAL_ASSETS_PATH=/app/data/page_images
DB_PATH=/app/data/imciflow.db
WHISPER_DEVICE=cpu
WHISPER_COMPUTE_TYPE=int8
```

Do not set `GOOGLE_AI_API_KEY` in Vercel.

## After Render Deploys

Copy the backend URL, for example:

```txt
https://imciflow-backend.onrender.com
```

Then set this in Vercel:

```env
VITE_API_BASE_URL=https://imciflow-backend.onrender.com
```

Redeploy the Vercel frontend after changing the environment variable.

## RAG Data Caveat

Render does not receive local generated data such as `data/chroma` unless we explicitly provide it.
Render's normal service filesystem is ephemeral, so generated files can disappear after redeploys,
restarts, or free-tier spin-downs.

For the final demo, choose one of these paths:

1. Build-time ingestion from official WHO PDFs.
2. Upload a prepared Chroma index to a Render persistent disk.
3. Commit a minimal demo-safe RAG seed if licensing and size are acceptable.

Until one of these is done, `/health` may report `rag_index_available=false` on Render.
