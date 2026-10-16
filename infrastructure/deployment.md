# Custra MVP deployment record

Updated: 16 October 2026. Local development only; no deployment has occurred.
Development cutoff: **18 October 2026, 16:00 IST**.

## Bindings and unresolved inputs

| Binding | Recorded state |
| --- | --- |
| Google Cloud project | `custra-mvp-2026`, user-confirmed previously |
| Billing | User previously confirmed active Free Trial linkage; spend/credits not rechecked |
| Model candidate | `gemini-3.5-flash-lite`; dedicated-ADC single answer and four-answer rehearsal passed |
| Vertex location | `global`; local adapter explicitly selects the project/location and Enterprise backend |
| Cloud Run region | Not selected; verify Firebase rewrite support before selection |
| Firestore | `(default)`, Standard / Native, `asia-south1`; live metadata verified; hosted write/read and local-app API-restart/browser-refresh persistence passed |
| Private Storage bucket | `custra-mvp-2026-documents`, `asia-south1`; dedicated-ADC SDK and application-route upload/read passed, including API restart with hosted Firestore; anonymous bucket GET 403 and unauthenticated app GET 401 |
| Hosting URL / Cloud Run service URLs | Not deployed or supplied |
| Competition restrictions | User supplied excerpts: Firebase/Firestore/Cloud Run/Gemini, public links, deck/video/source; user confirmed Retail & Commerce eligibility. See `docs/SUBMISSION_REQUIREMENTS.md` |
| Local ADC | Dedicated ADC path/quota verified; single answer and four-answer rehearsal passed without warnings; shared credentials are prohibited |

## Approved local authentication isolation

Use only `custra-mvp-2026` and the dedicated directory below. The user prohibits
using the legacy Sony configuration, credentials, project and resources. Ask for
confirmation if there is any doubt about identity, project, credentials or scope.
Do not change the shared gcloud configuration or shared ADC quota project.

Run this privately in WSL:

```bash
CLOUDSDK_CONFIG="$HOME/.config/gcloud-custra" \
gcloud auth application-default login \
  --project=custra-mvp-2026 \
  --no-launch-browser \
  --scopes=openid,https://www.googleapis.com/auth/userinfo.email,https://www.googleapis.com/auth/cloud-platform
```

Open the freshly generated URL, select the requested Google Cloud permissions,
and complete the CLI prompts privately. The saved ADC path must be
`/home/anirudh_jayant/.config/gcloud-custra/application_default_credentials.json`.
Never share authentication URLs, credentials, tokens or codes. Cloud Shell
credentials and older shared local credentials are not authorized for these checks.

Before a local Custra runtime or live test, set these values in that terminal:

```bash
export CLOUDSDK_CONFIG="$HOME/.config/gcloud-custra"
export GOOGLE_APPLICATION_CREDENTIALS="$CLOUDSDK_CONFIG/application_default_credentials.json"
export GOOGLE_CLOUD_PROJECT=custra-mvp-2026
export GOOGLE_CLOUD_QUOTA_PROJECT=custra-mvp-2026
export CLOUDSDK_CORE_PROJECT=custra-mvp-2026
export CLOUDSDK_BILLING_QUOTA_PROJECT=custra-mvp-2026
export GOOGLE_CLOUD_LOCATION=global
export GOOGLE_GENAI_USE_ENTERPRISE=True
```

Check that the dedicated ADC file exists before any cloud request. Explicit file
selection must fail if missing; do not remove it to fall back to shared credentials.
These exports apply to the current shell. They do not change stored global CLI
settings. The quota-project variable selects request attribution; it does not
create resources, grant permissions or alter billing settings. Any permission
failure requires investigation and user confirmation, not an automatic IAM change.

## Server configuration

Load configuration privately in each service's environment. No `.env` auto-loader
is used. Do not place demo passwords or Google credentials in Vite variables.

| Variable | API | Business simulator |
| --- | --- | --- |
| `GOOGLE_CLOUD_PROJECT` | Explicit target project | Same project, separate `custra_business/shared` namespace |
| `GOOGLE_CLOUD_LOCATION` | Vertex location, default `global` | Unused |
| `CUSTRA_MODEL_ID` | `gemini-3.5-flash-lite`; local live rehearsal passed | Unused |
| `CUSTRA_BUCKET` | Existing private document bucket | No access needed |
| `CUSTRA_DEMO_USERNAME` | Shared demo username | Unused |
| `CUSTRA_DEMO_PASSWORD_HASH` | Hash produced by `app.services.auth.hash_password`, supplied privately | Unused |
| `CUSTRA_APP_ORIGIN` | Exact browser origin; production Hosting origin | Unused |
| `CUSTRA_SECURE_COOKIES` | `true` in production; explicit `false` for local HTTP only | Unused |
| `CUSTRA_A2A_URL` | Simulator's canonical base URL, no `/a2a` suffix | Unused |
| `CUSTRA_A2A_IAM` | `true` in production; `false` only for local loopback simulator | Unused |
| `CUSTRA_AGENT_ENABLED` | `false` disables advance and booking; reads/explicit closure remain available | Unused |
| `CUSTRA_PUBLIC_URL` | Unused | Canonical base URL matching API's A2A URL; required before hosted use |
| `PORT` | Container listen port, default 8080 | Container listen port, default 8080 |

The API stores shared demo records under `custra_demo/shared`. Runtime Firestore
clients use ADC; no browser database access is needed. Session cookies are named
`__session`, HttpOnly, SameSite=Lax and expire after eight hours. Logout revokes
server state. Data responses carry `Cache-Control: private, no-store`.

## Local verification

Project environment: `backend/.venv`, Python 3.12. Direct runtime dependencies are
pinned in each requirements file; ADK `2.12.0`, A2A SDK `1.2.2` with HTTP-server
extra. Requirements were updated after the real SDK compatibility test passed.

Verified local boundaries include actual SDK start/answer exchanges, stable context
IDs, fresh per-answer ADK execution, fixed Agent Card destinations, and audience
headers on both card and RPC requests. An offline real ADK/GenAI test checks a
single request to the explicit Vertex project/global endpoint; it is not proof of
Google authorization or model output quality.

Local Docker builds succeeded for `custra-backend:local` and
`custra-business:local`. Both run as UID/GID `10001:10001`, honor custom `PORT`, and
start without credential files. Loopback health, unauthenticated API denial and
simulator Agent Card checks passed. These local simulator checks do not prove IAM.

The full test commands and current totals are recorded in
[local verification record](../docs/LOCAL_VERIFICATION.md). Browser fixtures use fictional data and
fake model/bucket boundaries. Firestore integration tests use Google's local Docker
emulator, project `demo-custra-tests` and isolated test namespaces. Real private
bucket upload/read and direct URL denial passed. Additional app-route checks used
local Firestore on loopback with project `custra-mvp-2026` and the real private
bucket: tiny fictional PNG upload, exact-content download, authenticated metadata
and file retrieval after backend restart, unauthenticated app denial (401), and
anonymous direct object denial (403). These checks do not prove hosted Firestore,
IAM, browser UI interaction or persistence after restarting the emulator itself.

Subsequent checks used the real `(default)` Firestore database in `asia-south1`:
a fictional create-only write and fresh-process exact-data read passed. The local
API then used hosted Firestore and the real private bucket; upload, exact-byte
download and saved document metadata survived API restart. Authenticated access
passed and anonymous app/bucket requests returned 401/403. The user confirmed the
document remained available after browser refresh. The complete live conversation
with hosted Firestore and deployed IAM/Hosting still require verification.

## One bounded live check after WSL authentication

From the repository root, only after the dedicated login and the isolation exports above are verified:

```bash
GOOGLE_CLOUD_PROJECT=custra-mvp-2026 GOOGLE_CLOUD_LOCATION=global GOOGLE_GENAI_USE_ENTERPRISE=True CUSTRA_RUN_LIVE_MODEL=1 PYTHONPATH=backend backend/.venv/bin/python -m pytest backend/tests/integration/test_agent_boundary.py::test_live_vertex_consumer_answer -q --tb=short
```

This requests one fictional product answer with a 35-second test deadline,
30-second answer deadline and one SDK HTTP attempt. Do not repeatedly retry an
authentication/permission error. After this passes, run the prepared four-answer rehearsal with a local emulator:

```bash
FIRESTORE_EMULATOR_HOST=127.0.0.1:8787 GOOGLE_CLOUD_PROJECT=custra-mvp-2026 CUSTRA_RUN_LIVE_REHEARSAL=1 backend/.venv/bin/python -m pytest backend/tests/integration/test_live_rehearsal.py -q --tb=short
```

This test has at most four real model answers, actual local A2A SDK transport,
emulator-only persistence, simulated booking and explicit closure. It passed with
dedicated Custra ADC in 9.82 seconds; the isolated single-answer check passed in
3.02 seconds. Both had no warnings. It is independent of the separate hosted rehearsal gate and private
Storage access check. Do not infer model success from browser fakes.

## Hosted actions requiring separate user approval

No commands below have been executed against Google Cloud. Before deployment:

1. Confirm competition rules, project access, deployment region, model location,
   Firestore Native database and private Storage bucket. Any resource creation,
   API enablement, IAM or billing change needs separate authorization.
2. Provision separate API/simulator service identities. API needs access to Vertex,
   its Firestore records, document bucket and configured secret. Simulator needs
   its replay records and no profile/document access. Verify Firestore authorization
   limitations of chosen IAM roles; collection naming alone is not an IAM boundary.
3. Deploy both images only after authorization. Keep simulator IAM-private; grant
   only the API identity invoker access. The API sends audience-correct Google
   identity tokens on Agent Card and RPC fetches. Configure `CUSTRA_PUBLIC_URL`
   to the actual service URL, never its local default.
4. Set production credentials via the agreed secret mechanism, Secure cookies,
   exact Hosting origin, min instances 0 and max instances 1 initially. The API
   service must accept Hosting requests while enforcing its own session checks.
5. Replace the intentional Cloud Run service/region placeholders in `firebase.json`
   with verified bindings, build the frontend, and deploy Hosting only after
   approval. Keep the API rewrite before the SPA fallback.
6. Verify Hosting cookie login/logout, direct backend 401, private simulator IAM
   denial, persistent files after process restart, and anonymous object URL denial.
   Use fictional data for one bounded complete live model/A2A rehearsal including
   refresh/recovery, selection, booking and explicit closure.
7. Confirm agent disable switch behavior and inspect logs for accidental sensitive
   data or excessive retries. Billing alerts/scaling limits are not spending caps;
   billing changes require approval. Record final URLs and remaining limitations.

No deployments, Google Cloud resources, IAM bindings, secrets, API keys, billing
settings, commits or pushes were changed during this local development work.

## Anshum's dummy deployment handoff

For owner IAM/setup steps, Anshum's isolated CLI login, the exact historical dummy
GitHub clone at the exact dummy commit, source-build/deploy commands, Firebase routing, hosted checks and the
ChatGPT prompt, use [the dedicated guide](../docs/ANSHUM_DUMMY_DEPLOYMENT_GUIDE.md).
The guide proposes changes for human approval; none have been applied. Do not
substitute the dirty MVP checkout or a moving default branch for its verified dummy commit.
Anshum obtains source from `https://github.com/AnirudhJayant06/CUSTRA`, with her own
GitHub access if required. Remote commit availability is not yet verified. A dummy
hosting rehearsal does not complete final Gemini/Firestore acceptance.
