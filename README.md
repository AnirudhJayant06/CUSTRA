# Custra

**Customer Unified Support, Tracking & Resolution Agent**

*Your AI representative across every brand.*

## Overview

Custra is a consumer-side AI representative that manages post-purchase support cases across brands, from issue reporting to verified resolution.

## AI Builder Cup 2026

**Theme:** Retail & Commerce — Intelligent Customer and Business Experiences

### MVP

Demonstrate a washing-machine warranty repair workflow involving:
- Product registration and invoice extraction
- AI-powered issue reporting and evidence gathering
- Consumer Agent and simulated Manufacturer Agent
- Warranty reasoning and claim negotiation
- Technician appointment scheduling
- Persistent case tracking and verified resolution

## Technology Stack

- Frontend: React + Vite
- Backend: Python + FastAPI
- AI: Gemini + Google ADK
- Agent Communication: A2A
- Hosting: Firebase Hosting + Google Cloud Run
- Database: Firestore
- Storage: Google Cloud Storage

## Team

- Anirudh Jayant
- Anshum

## Status

Deployment-ready dummy application implemented. The MVP above is future scope;
this demo only validates and echoes issue text. No AI, persistence, real uploads,
or brand contact is implemented.

## Run locally

Use Python 3.12 and a Node version supported by Vite (Node 24 was tested).
From the repository root, start the backend in one terminal:

```bash
cd backend
# Reuse .venv if present; otherwise: python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

In another terminal, from the repository root:

```bash
cd frontend
npm ci
npm run dev
```

Open http://localhost:5173. For a phone on the same network, open the network
URL printed by Vite and allow port 5173 through your local firewall if necessary.
Vite proxies relative `/api` requests to port 8000; CORS configuration is not needed.

## Test the dummy app

With the backend running, execute from the repository root:

```bash
backend/.venv/bin/python -m unittest discover -s backend/tests
curl http://127.0.0.1:8000/api/health
curl -X POST http://127.0.0.1:8000/api/test-issue \
  -H 'Content-Type: application/json' \
  -d '{"product_name":"Samsung Washing Machine","description":"Water is leaking underneath."}'
```

To run the same HTTP contract tests through Vite, keep both servers running:

```bash
CUSTRA_TEST_URL=http://127.0.0.1:5173 backend/.venv/bin/python -m unittest discover -s backend/tests
```

Product names accept 1–120 characters and descriptions 1–2,000 after trimming.
Missing, blank, whitespace-only, non-string, and overlong values return HTTP 422.
Valid submissions return the actual submitted text, `success: true`,
`message: "Test issue submitted successfully!"`, and `status: "received"`.

In the browser, check required/whitespace validation, select and replace a photo,
remove it, and submit. Only the two text fields appear in the network payload.
Photo previews are local object URLs, released on replacement, removal, and
component unmount. Camera/gallery choices depend on the phone and browser;
unsupported image formats show a preview error. Stop the backend to test the
error message, restart it, and use **Try Again**. Requests time out after 15 seconds.
Check widths 360–430px and desktop for readable, touch-friendly controls.

## Production build

```bash
cd frontend
npm ci
npm run build
```

Output is `frontend/dist`. `npm run preview` previews static assets only; it does
not provide the development API proxy. Use Vite dev or configured Firebase Hosting
to test the complete application.

## Hosting handoff (not deployed)

Firebase Hosting serves `frontend/dist`. Its first rewrite sends `/api/**` to
Cloud Run, preserving the API path; the final rewrite serves `index.html` for SPA
fallback. See the [Firebase Cloud Run integration documentation](https://firebase.google.com/docs/hosting/cloud-run).

The engineer must:

1. Select the Firebase/Google Cloud project and a Firebase Hosting-supported
   Cloud Run region; configure billing, APIs, and deployment permissions.
2. Build and deploy the backend using `backend` as the Docker build context.
   Configure the service for public invocation through the Hosting integration.
3. Replace `REPLACE_WITH_CLOUD_RUN_SERVICE` and `REPLACE_WITH_CLOUD_RUN_REGION`
   in `firebase.json` with the actual deployed service ID and region. These are
   intentional placeholders; this file cannot be deployed unchanged.
4. Select the actual Firebase project using the CLI/project configuration,
   build the frontend, then deploy Hosting. No project ID or region is assumed.
5. Smoke-test health and submission through the public Hosting URL, including
   mobile photo selection. Pin tested Python dependency versions before final submission.

Local container check (no cloud deployment):

```bash
docker build -t custra-backend backend
docker run --rm -p 8080:8080 -e PORT=8080 custra-backend
```

The container runs as a non-root user, binds to `0.0.0.0`, and honors `PORT`
(default 8080). Runtime requirements contain only direct dependencies and remain
unpinned for now. Do not put cloud credentials into the image or repository.
