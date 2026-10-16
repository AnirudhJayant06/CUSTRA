# Run Custra locally

For Anshum and other Custra developers. Commands target Ubuntu or WSL2 with Bash.
Run them from the repository root unless a step says otherwise. This guide runs
the current MVP from `develop`; it does not deploy anything or use the historical
dummy app. Business support and appointments are simulated; no brand is contacted.

## 1. Clone and install dependencies

Prerequisites: Git, Python 3.12 with `venv`/pip, Node.js 24 with npm, and Google
Cloud CLI for real-service mode. Use your own GitHub access if the repo is private.

```bash
git clone --branch develop https://github.com/AnirudhJayant06/CUSTRA.git
cd CUSTRA
python3 --version
node --version
npm --version
python3 -m venv backend/.venv
backend/.venv/bin/python -m pip install -r backend/requirements-dev.txt
npm --prefix frontend ci
```

Use Python 3.12 for the venv. If Ubuntu reports that `ensurepip` is unavailable,
install its Python 3.12 venv package and repeat venv creation. Do not install
project Python packages globally. The backend environment includes the simulator's
runtime dependencies; a second venv is unnecessary.

For an existing clone, run `git status` first. With a clean checkout, switch to
`develop` and run `git pull --ff-only origin develop`. Preserve local changes;
do not reset or clean the working tree to update it.

## 2. Check the code without Google access

These checks use fictional fixtures and do not call Gemini or write cloud data.
Run them in a terminal where live-test opt-ins are unset:

```bash
unset CUSTRA_RUN_LIVE_MODEL CUSTRA_RUN_LIVE_REHEARSAL FIRESTORE_EMULATOR_HOST
backend/.venv/bin/python -m pytest backend/tests manufacturer-agent/tests -q
npm --prefix frontend run test:unit
npm --prefix frontend run build
backend/.venv/bin/python -m pip check
```

Firestore-emulator and opt-in live tests are skipped here. For browser checks:

```bash
cd frontend
npx playwright install chromium
cd ..
npm --prefix frontend run test:e2e
```

On Linux, if Playwright reports missing OS libraries, follow its dependency
installation instructions (`npx playwright install --with-deps chromium` from
`frontend`). Browser tests manage fixture services on ports 8018 and 5178; keep
those ports free. Fixture state is temporary and Gemini/Storage are fake. Do not
deploy the fixture server or its `/test/*` endpoints. An existing compatible
Chromium can be selected with `CUSTRA_CHROMIUM_PATH`.

## 3. Get access for real-service mode

Use your own Google identity with access to the existing Custra project. Never
copy another developer's ADC, password, authentication URL, token or key.

| Resource | Binding |
| --- | --- |
| Project | `custra-mvp-2026` |
| Firestore | `(default)`, Standard / Native, `asia-south1` |
| Private Storage bucket | `custra-mvp-2026-documents`, `asia-south1` |
| Gemini model | `gemini-3.5-flash-lite` through Vertex/Agent Platform |
| Model location | `global` (separate from the database/bucket region) |

Your identity needs permission to use Vertex, read/write Firestore, upload/read
bucket objects, and attribute API usage to this project. Ask the project owner to
confirm access if unsure. Do not create another project, loosen rules, create an
API key, or grant yourself roles as a workaround. Firestore browser rules remain
Restrictive; the backend uses IAM-authenticated server SDKs.

Use a dedicated Custra configuration even if you already use Google Cloud for
other work. Run the following privately and select your own authorized identity:

```bash
export CLOUDSDK_CONFIG="$HOME/.config/gcloud-custra"
gcloud auth application-default login \
  --project=custra-mvp-2026 \
  --no-launch-browser \
  --scopes=openid,https://www.googleapis.com/auth/userinfo.email,https://www.googleapis.com/auth/cloud-platform
gcloud auth application-default set-quota-project custra-mvp-2026
test -f "$CLOUDSDK_CONFIG/application_default_credentials.json"
```

Complete browser/terminal authentication privately. CLI login and application
default credentials are separate; the app uses the latter. Existing valid Custra
ADC can be reused. Do not access or change any unrelated Google configuration.

## 4. Generate private local runtime settings

This creates ignored `.env.local` at the repo root and asks you to choose your own
local demo login. It stores a password hash, not the password. Remember the login
you enter. No `.env` file is loaded automatically by the application.

```bash
backend/.venv/bin/python - <<'PY'
import getpass
import os
from pathlib import Path
import shlex
import sys

sys.path.insert(0, 'backend')
from app.services.auth import hash_password

target = Path('.env.local')
if target.exists():
    raise SystemExit('.env.local exists; inspect and reuse it rather than overwriting.')
config = Path.home() / '.config/gcloud-custra'
adc = config / 'application_default_credentials.json'
if not adc.is_file():
    raise SystemExit('Dedicated Custra ADC is missing. Complete step 3 first.')
username = input('Choose a local demo username: ').strip()
password = getpass.getpass('Choose a local demo password: ')
if not username or not password:
    raise SystemExit('Username and password must be nonempty.')
values = {
    'CLOUDSDK_CONFIG': str(config),
    'GOOGLE_APPLICATION_CREDENTIALS': str(adc),
    'GOOGLE_CLOUD_PROJECT': 'custra-mvp-2026',
    'GOOGLE_CLOUD_QUOTA_PROJECT': 'custra-mvp-2026',
    'CLOUDSDK_CORE_PROJECT': 'custra-mvp-2026',
    'CLOUDSDK_BILLING_QUOTA_PROJECT': 'custra-mvp-2026',
    'GOOGLE_CLOUD_LOCATION': 'global',
    'GOOGLE_GENAI_USE_ENTERPRISE': 'True',
    'CUSTRA_MODEL_ID': 'gemini-3.5-flash-lite',
    'CUSTRA_BUCKET': 'custra-mvp-2026-documents',
    'CUSTRA_DEMO_USERNAME': username,
    'CUSTRA_DEMO_PASSWORD_HASH': hash_password(password),
    'CUSTRA_APP_ORIGIN': 'http://localhost:5173',
    'CUSTRA_SECURE_COOKIES': 'false',
    'CUSTRA_A2A_URL': 'http://127.0.0.1:8081',
    'CUSTRA_PUBLIC_URL': 'http://127.0.0.1:8081',
    'CUSTRA_A2A_IAM': 'false',
    'CUSTRA_AGENT_ENABLED': 'true',
}
with open(target, 'x', opener=lambda path, flags: os.open(path, flags, 0o600)) as f:
    f.write('unset FIRESTORE_EMULATOR_HOST GOOGLE_API_KEY GEMINI_API_KEY GOOGLE_GENAI_API_KEY\n')
    for key, value in values.items():
        f.write(f'export {key}={shlex.quote(value)}\n')
print('Created .env.local. Keep it private and source it in each backend terminal.')
PY
git check-ignore .env.local
```

The final command must print `.env.local`. Never commit it or put server
credentials in `VITE_*` variables. Loopback HTTP uses non-Secure cookies and no
simulator IAM; deployed services require Secure cookies and IAM authentication.

The real app shares `custra_demo/shared` and simulator `custra_business/shared`
with other developers. A different demo login does not isolate your data. Use
fictional records, coordinate profile edits, and leave other developers' records
alone. Data survives local service restarts. Real model calls and cloud operations
can consume project credits; the normal complaint flow requests four model answers.

## 5. Start the three services

Open three terminals, each in the repository root. Keep them running.

**Terminal 1 — Business Agent simulator**

```bash
source ./.env.local
backend/.venv/bin/python -m uvicorn main:app --app-dir manufacturer-agent/app --host 127.0.0.1 --port 8081
```

**Terminal 2 — Consumer Agent / API**

```bash
source ./.env.local
backend/.venv/bin/python -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000
```

**Terminal 3 — frontend**

```bash
npm --prefix frontend run dev -- --host 127.0.0.1 --port 5173 --strictPort
```

Open **http://localhost:5173** and use the local demo login you chose. Use exactly
this browser origin because the API checks it. Vite proxies `/api` to port 8000.
Do not use Vite preview for the API flow. Stop each service with Ctrl+C; restart
it with the same command, sourcing `.env.local` again in a new backend terminal.

## 6. Check the user journey and agent conversation

1. Sign in; complete Profile with fictional name, phone and email.
2. Confirm/add a fictional service address.
3. Add a product in Vault. Upload a fictional PDF, JPEG or PNG under 5,000,000
   bytes, open it, and refresh to verify saved data.
4. Open **Complaints → Start a complaint**. Select the product/address, enter a
   fictional issue, and submit once.
5. Keep the case page open. It advances the conversation automatically. The
   scripted Business Agent asks questions over real A2A; the ADK/Gemini Consumer
   Agent answers from the saved case facts. Messages appear in the timeline.
6. Choose an appointment in the final dialog. Verify the simulated booking.
7. Refresh to check recovery. Close the case only by explicitly confirming that
   the issue is resolved.

Closing the page stops dispatching new conversation steps; an in-flight request
can still finish. Reopening resumes saved progress. Avoid repeated retries after
a failure; a retry can repeat model compute. Existing cases retain the details
captured when created, even if you later edit the product/profile.

## Troubleshooting

| Symptom | What to check |
| --- | --- |
| Port already in use | Identify your existing service; reuse or stop your own process. Do not kill unrelated services. |
| Frontend silently uses another port | Start with `--strictPort`; origin must remain `http://localhost:5173`. |
| Login rejected | Use the login generated in step 4; source the file in the API terminal and restart it. |
| 403 Origin error | Use `localhost:5173` in the browser and the matching `CUSTRA_APP_ORIGIN`. |
| 503 / Google permission error | Check dedicated ADC, project access and enabled API with the owner. Do not weaken rules or change IAM blindly. |
| ADC reauthentication needed | Repeat step 3 privately in the dedicated config, then restart both backend services. |
| Gemini or A2A step fails | Read API and simulator terminal errors, confirm both services are running and the model/project bindings. Retry only after the cause is understood. |
| Old emulator data or connection error | Source `.env.local`; it unsets `FIRESTORE_EMULATOR_HOST`. Do not migrate emulator data implicitly. |
| File upload rejected | Use a valid PDF/JPEG/PNG within the size limit; verify private bucket access. |

## Verification status at handoff

Local A2A transport and a four-answer real Gemini rehearsal passed earlier using
emulator persistence. Hosted Firestore/private Storage application upload, download,
API-restart recovery and browser refresh subsequently passed. The complete live
conversation with hosted Firestore and hosted Cloud Run/IAM/Hosting acceptance
remain pending. See [verification](LOCAL_VERIFICATION.md) and
[deployment bindings](../infrastructure/deployment.md). Hosting work is separate;
this guide does not authorize or perform deployment.
