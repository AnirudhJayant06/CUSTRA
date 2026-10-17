# Custra

**Customer Unified Support, Tracking & Resolution Agent**

Custra V1 combines a manually maintained product Vault with automated complaint
registration. A Gemini/Google ADK Consumer Agent answers four scripted business
questions using saved case facts over the official A2A SDK. The user chooses an
appointment in the final dialog and explicitly confirms resolution later.

Business questions, service centers, complaint references and appointments are
**simulated**. No manufacturer is contacted. Invoice extraction, warranty analysis,
negotiation, Google sign-in and missing-information chat are deferred.

The local implementation includes a shared demo login, saved profile/addresses,
products and product complaint tabs, private PDF/JPEG/PNG documents (5,000,000 bytes
maximum), immutable complaint snapshots, durable progress/replay, and appointment
recovery. Real Gemini answers and the local A2A rehearsal have passed using isolated Custra
credentials. Hosted Firestore and private Storage persistence passed through the
local application, API restart and browser refresh. Deployment, hosted IAM/routing,
and the full live conversation with hosted Firestore remain acceptance gates; see the
[deployment record](infrastructure/deployment.md) and
[verification record](docs/LOCAL_VERIFICATION.md).

Development cutoff: **18 October 2026, 16:00 IST**.

## Setup

The approved mobile interface now includes Home, Products and Complaints,
optional product nicknames and warranty duration, compact preferred-date/time
selection, and an agent conversation. See [implementation and verification](docs/MOBILE_UI_IMPLEMENTATION.md)
for the backward-compatible API additions and [design tokens](DESIGN.md).

New developer: follow [the local setup and run guide](docs/LOCAL_SETUP.md) for a
fresh clone, your own Google login, private runtime configuration, all three
services, the agent conversation, and troubleshooting. It requires no files from
another developer's machine.

Use Python 3.12 and Node 24. From the repository root:

```bash
# Reuse backend/.venv; create it only if absent:
# python3.12 -m venv backend/.venv
backend/.venv/bin/python -m pip install -r backend/requirements-dev.txt
npm --prefix frontend ci
```

The project environment is `backend/.venv`. ADK `2.12.0` and A2A SDK `1.2.2`
were pinned after the actual local SDK transport test passed. Do not install
project dependencies globally. Production images install runtime dependencies
only; test fixtures are excluded.

## Local checks without Google credentials

```bash
backend/.venv/bin/python -m pytest backend/tests manufacturer-agent/tests -q
npm --prefix frontend run test:unit
npm --prefix frontend run test:e2e
npm --prefix frontend run build
backend/.venv/bin/python -m pip check
```

Playwright starts its own API on 8018 and Vite on 5178, uses fictional data and
fake model/storage boundaries, and exercises real local A2A messages. Install
Chromium with `cd frontend && npx playwright install chromium`, or set
`CUSTRA_CHROMIUM_PATH` to an existing compatible Chromium executable. Six browser
scenarios cover the full flow, refresh, duplicate submission, failure/retry and
session expiry at 390px and desktop. These checks do not prove live cloud access.
`CUSTRA_UI_URL` selects an existing test UI; fixture scenarios also require an
explicit test-only `CUSTRA_TEST_CONTROL_API`. Never expose the fixture server or
its `/test/*` controls as a production application.

Firestore integration tests skip unless a **loopback** emulator is configured:

```bash
docker run --rm -d --name custra-firestore-verification -p 127.0.0.1:8787:8080 gcr.io/google.com/cloudsdktool/google-cloud-cli:emulators gcloud emulators firestore start --host-port=0.0.0.0:8080 --project=demo-custra-tests --quiet
FIRESTORE_EMULATOR_HOST=127.0.0.1:8787 backend/.venv/bin/python -m pytest backend/tests manufacturer-agent/tests -q
docker stop custra-firestore-verification
```

These tests use `demo-custra-tests` and isolated namespaces. The live model test
is opt-in and remains skipped in normal runs.

## Run the application with real services

Configure the server variables in the deployment record privately. The API needs
Firestore, an accessible private Storage bucket for documents, and ADC for Vertex.
The separate simulator needs Firestore. In WSL, use the dedicated Custra login and explicit credential/project exports in
[the isolation instructions](infrastructure/deployment.md#approved-local-authentication-isolation).
Shared Google credentials/configuration are prohibited; confirm any uncertainty before proceeding.
Never paste credentials or OAuth codes into chat or source control.

For local HTTP only, use `CUSTRA_SECURE_COOKIES=false`,
`CUSTRA_A2A_IAM=false`, `CUSTRA_A2A_URL=http://127.0.0.1:8081`,
`CUSTRA_APP_ORIGIN=http://localhost:5173`, and simulator
`CUSTRA_PUBLIC_URL=http://127.0.0.1:8081`. Configure a demo username and PBKDF2
password hash privately; `app.services.auth.hash_password` generates the supported
hash. Production must use Secure cookies and IAM-authenticated simulator requests.

Run each command in a separate terminal with its server configuration loaded:

```bash
backend/.venv/bin/python -m uvicorn main:app --app-dir manufacturer-agent/app --host 127.0.0.1 --port 8081
backend/.venv/bin/python -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000
npm --prefix frontend run dev
```

Vite proxies `/api` to port 8000 (`CUSTRA_API_URL` overrides it). Open
`http://localhost:5173`. Production output is `frontend/dist`; Vite preview serves
static assets only. Cloud resources and deployments require separate approval.

Closing the case page stops new agent steps. An in-flight request may finish;
reopening recovers saved progress. An explicit retry can repeat interrupted model
compute. Registration and booking never automatically close a complaint.

## Packaging and hosting

```bash
docker build -t custra-backend:local backend
docker build -t custra-business:local manufacturer-agent
```

Both images run as non-root users and honor `PORT` (default 8080). Firebase Hosting
serves the SPA and forwards `/api/**` to the API. `firebase.json` deliberately
retains service/region placeholders until deployment bindings are selected.
The Business Agent service must stay IAM-private. See the deployment record for
configuration, acceptance gates and actions awaiting separate authorization.

## Team

Anirudh Jayant and Anshum · AI Builder Cup 2026 · Retail & Commerce
