# Anshum: deploy the Custra dummy app

Prepared 16 October 2026. Project: **`custra-mvp-2026`**.
Anshum signs in with her own Google account. Anirudh has invited her as an
additional project Owner; acceptance is not yet confirmed. Anirudh retains his
own Owner access and control of the linked billing account.

This guide has not been executed against Google Cloud. Its IAM/resource changes
and deployment commands are instructions for the humans to review and perform.
No assistant is authorized to execute them merely by receiving this guide.

## 1. What this deployment contains

The dummy checkpoint is `eb0245188c76052b1296aa7abe0728722c5371d0` (`eb02451`).
It has a React/Vite form, photo preview in the browser, and a FastAPI health and
text-echo API. Photos are not uploaded. It has no login, Gemini, Firestore,
document storage or A2A runtime. Use fictional data.

Deploy this as an infrastructure rehearsal. It does **not** satisfy the final
competition requirement to demonstrate Firebase, Firestore, Cloud Run and Gemini.
The final MVP must replace the dummy and pass a full hosted rehearsal before submission.
Retail & Commerce eligibility has been confirmed by Anirudh.

Source repository: **https://github.com/AnirudhJayant06/CUSTRA**.
Obtain source by cloning this repository into a fresh folder and selecting the
exact dummy commit above. No source ZIP or code-file transfer is part of this handoff.

The main development checkout contains uncommitted MVP changes. Do not deploy that
folder accidentally, reset it, clean it or overwrite it. Do not deploy whichever
branch happens to be the repository default: verify the dummy commit explicitly.
Its old README describes historical future scope; this guide defines the task.

Anonymous access to the GitHub URL could not be verified on 16 October 2026, and
anonymous Git access requested authentication. This does not establish whether
it is private, missing or otherwise unavailable. Anshum must verify access using
her own GitHub account. The dummy commit exists locally; its availability on
GitHub is not yet verified. Do not push anything automatically if it is missing.

## 2. Owner setup: Anirudh enables Anshum

### 2.1 Agree on the deployment inputs first

Fill these in together. Stop and ask Anirudh if a value is unknown.

| Input | Value |
| --- | --- |
| Project ID | `custra-mvp-2026` — fixed |
| Anshum's Google account | Her actual Google account email, exchanged privately |
| Backend service | Proposed `custra-dummy-api`; confirm it is unused or approved for replacement |
| Region | Owner must approve a Firebase Hosting rewrite-supported Cloud Run region |
| Firebase Hosting site ID | Owner must confirm the actual site and approve publishing to it |
| Runtime identity | Proposed `custra-dummy-runtime@custra-mvp-2026.iam.gserviceaccount.com` |
| Build identity | Proposed `custra-dummy-build@custra-mvp-2026.iam.gserviceaccount.com` |

`asia-south1` is on Firebase's supported rewrite list, but it is only a candidate;
this guide does not select a region or inspect your existing resources.
Source deployment builds an image and can create source-build artifacts and an
Artifact Registry repository. Confirm those changes and resulting costs before deployment.

### 2.2 Confirm Anshum's Google Cloud Owner invitation

Anirudh has already invited Anshum as an additional **Owner** of this project.
The last confirmed Console status was **pending invitation**. Anshum must accept
it using the invited Google account, then open `custra-mvp-2026` in Cloud Console.
Anirudh should verify the invitation is no longer pending and retain his own Owner role.
Do not treat an invitation as accepted until Anshum can access the project.

With accepted Owner access, do not add the earlier four project roles merely to
duplicate her access. Owner allows broad project and IAM changes; that technical
ability is not permission to change billing, unrelated resources or deployment
bindings without the team's approval. Build/runtime identities still need setup.

If the team later chooses narrower access, the documented alternative is Cloud
Run Source Developer, Service Usage Consumer, Firebase Hosting Admin and API Keys
Viewer on this project, plus Service Account User on the two named service accounts.
Do not switch access models or revoke Owner access without Anirudh's confirmation.

### 2.2a Confirm GitHub access separately

Google Cloud Owner does not grant GitHub repository access. Anshum should sign in
with her own GitHub account and open:

https://github.com/AnirudhJayant06/CUSTRA

If access is denied or the repository is private, Anirudh opens the repository's
**Settings → Collaborators → Add people**, invites her GitHub account and has her
accept the separate GitHub invitation. Do not share a GitHub password or token.
Do not change repository visibility automatically. The final public-source
submission requirement is a separate review before submission.

Anirudh must confirm that the dummy commit
`eb0245188c76052b1296aa7abe0728722c5371d0` is reachable from the repository she can
clone. If it is absent, stop and request his decision about publishing that exact
checkpoint. This guide does not authorize pushing the dirty MVP checkout.

The guide and ChatGPT prompt are local handoff documents and have not been
committed/pushed by this task. Share these documents separately, or explicitly
approve publishing them later; do not assume they already exist on GitHub.

### 2.3 Prepare separate runtime and build identities

In **IAM & Admin → Service Accounts**, Anirudh checks for the two agreed accounts.
If absent and he approves creating them:

1. Create `custra-dummy-runtime`. Skip optional project roles: the dummy runtime
   needs no Vertex, Firestore, Storage or Secret Manager access.
2. Create `custra-dummy-build`. Grant this service account **Cloud Run Builder**
   (`roles/run.builder`) on `custra-mvp-2026` so Cloud Build can build the source.
3. Verify Anshum's accepted Owner access permits acting as the two selected
   identities. If using the narrower-role alternative instead, grant her
   **Service Account User** (`roles/iam.serviceAccountUser`) on each named service
   account through its Permissions tab. Stop and ask before any additional grant.
4. Do not create or download service-account keys. Do not give Anshum Anirudh's
   credential file, password or OAuth codes.

The deploy command below explicitly selects both identities. Anshum does not need
to inherit Anirudh's personal Vertex permissions to deploy this dummy app.

### 2.4 Owner verifies the project prerequisites

Anirudh confirms the existing billing link and these enabled APIs in this project:
Cloud Run Admin, Cloud Build, Artifact Registry, IAM, Cloud Resource Manager,
Firebase Management and Firebase Hosting. Enabling a missing API is an owner
action requiring approval; Anshum should not accept unexpected enablement prompts.
Do not modify billing settings as a troubleshooting shortcut.

In Firebase Console, use the **existing Google Cloud project** `custra-mvp-2026`.
If Firebase has not been added, Anirudh must review and approve adding it to that
same project. Confirm the Hosting site ID and that publishing will not overwrite
another approved deployment. A new Google Cloud project is unnecessary.

## 3. Anshum: prepare your terminal and source

Use Google Cloud Shell or a Bash/WSL terminal with `gcloud`, Git, Python 3 and
Node installed. Node 24 was tested. Check tools locally:

```bash
gcloud --version
git --version
node --version
npm --version
python3 --version
```

Set a dedicated configuration for your own Custra login. Use this setup in every
new terminal for this task:

```bash
export CUSTRA_PROJECT_ID=custra-mvp-2026
export CLOUDSDK_CONFIG="$HOME/.config/gcloud-custra-anshum"
export CLOUDSDK_ACTIVE_CONFIG_NAME=default
export CLOUDSDK_CORE_PROJECT="$CUSTRA_PROJECT_ID"
export CLOUDSDK_BILLING_QUOTA_PROJECT="$CUSTRA_PROJECT_ID"
export GOOGLE_CLOUD_PROJECT="$CUSTRA_PROJECT_ID"
export GOOGLE_CLOUD_QUOTA_PROJECT="$CUSTRA_PROJECT_ID"
export XDG_CONFIG_HOME="$HOME/.config/custra-anshum-cli"
# A missing dedicated ADC must not fall back to another account's ADC.
export GOOGLE_APPLICATION_CREDENTIALS="$CLOUDSDK_CONFIG/application_default_credentials.json"
unset FIREBASE_TOKEN GOOGLE_API_KEY GEMINI_API_KEY GOOGLE_GENAI_API_KEY
```

Authenticate the deployment CLI with **Anshum's account**:

```bash
gcloud auth login --no-launch-browser --project="$CUSTRA_PROJECT_ID"
gcloud auth list --filter=status:ACTIVE --format='value(account)'
gcloud projects describe "$CUSTRA_PROJECT_ID" --project="$CUSTRA_PROJECT_ID" --format='value(projectId)'
```

Complete browser/terminal authentication privately. Check the active email yourself
and verify the project output is exactly `custra-mvp-2026`. Stop if either differs.
The dummy needs CLI login only, not an ADC/model login. Do not inspect or use any
Sony/shared configuration, project, credentials or resources. Ask if anything is uncertain.

Clone the repository into a **new** directory. If the target folder already
exists, stop and choose another fresh path; do not reuse/reset a dirty checkout.

```bash
git clone --no-checkout https://github.com/AnirudhJayant06/CUSTRA.git "$HOME/custra-dummy-deploy"
cd "$HOME/custra-dummy-deploy"
git cat-file -e 'eb0245188c76052b1296aa7abe0728722c5371d0^{commit}'
git switch --detach eb0245188c76052b1296aa7abe0728722c5371d0
git rev-parse HEAD
git status --short
```

Run commands one at a time and stop at the first failure. The printed commit must
be exactly `eb0245188c76052b1296aa7abe0728722c5371d0`, with an initially clean status.
Detached HEAD deliberately fixes the deployment source; no branch or commit is needed.

For a private repository, use your own GitHub-authorized Git/credential manager or
GitHub CLI login, following its private authentication prompts. Never put tokens
in the clone URL or share them with an assistant. If access or the commit check
fails, stop and ask Anirudh; do not use another branch or request a source ZIP.

Confirm `backend/app/main.py` contains `/api/test-issue` and no Google SDK imports.
If the source is the login/Vault/agent MVP instead, stop: it is the wrong checkpoint.
Any later Firebase configuration changes below belong only to this fresh clone.
Do not commit or push them without Anirudh's separate instruction.

## 4. Anshum: deploy the dummy backend

Replace the two placeholder values below with the owner's confirmed inputs:

```bash
export CUSTRA_DUMMY_REGION='OWNER_APPROVED_REGION'
export CUSTRA_DUMMY_SITE='OWNER_APPROVED_HOSTING_SITE_ID'
export CUSTRA_DUMMY_SERVICE=custra-dummy-api
export CUSTRA_DUMMY_RUNTIME_SA="custra-dummy-runtime@${CUSTRA_PROJECT_ID}.iam.gserviceaccount.com"
export CUSTRA_DUMMY_BUILD_SA="custra-dummy-build@${CUSTRA_PROJECT_ID}.iam.gserviceaccount.com"
```

If either placeholder is still present, stop. Confirm deployment approval with
Anirudh, then run from the fresh clone at the verified dummy commit:

```bash
gcloud run deploy "$CUSTRA_DUMMY_SERVICE" \
  --source=backend \
  --project="$CUSTRA_PROJECT_ID" \
  --region="$CUSTRA_DUMMY_REGION" \
  --service-account="$CUSTRA_DUMMY_RUNTIME_SA" \
  --build-service-account="projects/${CUSTRA_PROJECT_ID}/serviceAccounts/${CUSTRA_DUMMY_BUILD_SA}" \
  --min-instances=0 \
  --max-instances=1 \
  --memory=512Mi \
  --cpu=1 \
  --port=8080 \
  --timeout=60 \
  --quiet
```

The source directory contains a Dockerfile; Cloud Build uses it. No local Docker
installation is required for this path. Keep public-access/IAM changes with Anirudh:
this command intentionally omits `--allow-unauthenticated`. A new service is private
until the owner performs the following step. Scaling settings are not a spending cap.
If prompted for missing APIs or if a permission error occurs, stop and show Anirudh
the sanitized error. Do not add broad roles, change projects, or retry repeatedly.

### 4.1 Anirudh: approve public access to this dummy service only

After checking the service name/project/region and approving public invocation,
Anirudh runs this using **his own dedicated Custra CLI login** and the same approved
project/service/region values (do not switch to Anshum's credential directory):

```bash
gcloud run services add-iam-policy-binding "$CUSTRA_DUMMY_SERVICE" \
  --project=custra-mvp-2026 \
  --region="$CUSTRA_DUMMY_REGION" \
  --member=allUsers \
  --role=roles/run.invoker
```

This changes access on the named dummy service only. Never apply it to the private
MVP business simulator. If an organization policy rejects public access, stop and
ask; do not change organization policy or grant Anshum project-wide Cloud Run Admin.

### 4.2 Anshum: verify the deployed API

```bash
export CUSTRA_DUMMY_API_URL="$(gcloud run services describe "$CUSTRA_DUMMY_SERVICE" --project="$CUSTRA_PROJECT_ID" --region="$CUSTRA_DUMMY_REGION" --format='value(status.url)')"
curl --fail --silent --show-error "$CUSTRA_DUMMY_API_URL/api/health"
curl --fail --silent --show-error "$CUSTRA_DUMMY_API_URL/api/test-issue" \
  -H 'Content-Type: application/json' \
  -d '{"product_name":"Fictional Washer","description":"Fictional water leak."}'
```

Expect health `healthy` and an echo response with `success: true`,
`status: received` and the submitted text. A browser GET to the backend root `/`
may return 404: test `/api/health`. A 403 before the public-access step is expected.

## 5. Anshum: configure and deploy Firebase Hosting

From the fresh clone's root, update **only that clone's** Firebase configuration:

```bash
python3 - <<'PY'
import json
import os
from pathlib import Path
region = os.environ['CUSTRA_DUMMY_REGION']
site = os.environ['CUSTRA_DUMMY_SITE']
assert region != 'OWNER_APPROVED_REGION' and site != 'OWNER_APPROVED_HOSTING_SITE_ID'
p = Path('firebase.json')
data = json.loads(p.read_text())
data['hosting']['site'] = site
data['hosting']['rewrites'][0]['run'] = {
    'serviceId': os.environ['CUSTRA_DUMMY_SERVICE'], 'region': region,
}
assert data['hosting']['public'] == 'frontend/dist'
assert data['hosting']['rewrites'][-1] == {'source': '**', 'destination': '/index.html'}
p.write_text(json.dumps(data, indent=2) + '\n')
PY
npm --prefix frontend ci
npm --prefix frontend run build
npx --yes firebase-tools --version
npx --yes firebase-tools login --no-localhost
```

Firebase CLI login is separate from `gcloud auth login`; use Anshum's same account
and complete its prompts privately. `XDG_CONFIG_HOME` above separates the CLI's
saved login; never share that directory. These commands do not install Firebase CLI globally.
Record the CLI version in the handoff.

Set your own account email privately, check that it is the account you just used,
and deploy only Hosting after Anirudh has approved the target site:

```bash
export CUSTRA_ANSHUM_EMAIL='YOUR_OWN_GOOGLE_ACCOUNT_EMAIL'
npx --yes firebase-tools login:list
npx --yes firebase-tools deploy --only hosting \
  --project="$CUSTRA_PROJECT_ID" \
  --account="$CUSTRA_ANSHUM_EMAIL" \
  --config=firebase.json
```

Record the actual Hosting URL printed by the CLI. Do not run `firebase init`,
create a new project, deploy Firestore rules, or deploy unrelated Firebase products.
If Firebase login is missing/expired, stop and authenticate again in the dedicated
CLI directory; do not bypass authentication using another account's ADC or a token.

## 6. Verify the link and return the handoff

1. Open the Hosting URL in a private browser window without a Google login.
2. Load `<HOSTING_URL>/api/health`; it must return JSON, not the SPA HTML.
3. Submit a fictional product/issue; confirm the actual entered text is returned.
4. Check empty/whitespace inputs are rejected and the mobile layout is usable.
5. Select/replace/remove a photo. It should preview locally; no server upload is claimed.
6. Refresh the page and repeat one submission. Check browser console/network errors.
7. Run the retained HTTP contract tests against Hosting, in this fresh clone:

```bash
python3 -m venv .verification-venv
CUSTRA_TEST_URL='PASTE_ACTUAL_HOSTING_URL' .verification-venv/bin/python -m unittest discover -s backend/tests
```

These four tests use Python's standard library and check health, echo, invalid
inputs and length boundaries. The Python environment stays local to this clone;
do not install Google SDKs or packages globally. Tests make fictional echo calls only.

Send Anirudh: project ID, approved region/site, Cloud Run service name and URL,
Hosting URL, source checkpoint `eb02451`, Firebase CLI version, test results and
any unresolved error. Never include credential files, tokens, OAuth codes or
authentication URLs. Keep the working deployment available during evaluation;
coordinate any later replacement with the verified full MVP.

If any command fails, capture its non-sensitive error and stop. Do not assume a
successful deployment command means the public app works. Neither min/max instances
nor a billing alert guarantees a fixed cost ceiling.

## 7. Prompt to use with ChatGPT

Use the separate [copyable handoff prompt](ANSHUM_CHATGPT_PROMPT.md). Share this
guide and the repository URL. Anshum clones the source herself; do not attach
source archives, credentials or authentication transcripts. ChatGPT cannot be
assumed to have access to a private repository; it can guide her terminal steps
using this guide and sanitized non-sensitive results.

## Official references checked

- [Inviting GitHub collaborators](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/repository-access-and-collaboration/inviting-collaborators-to-a-personal-repository)

- [Cloud Run source deployment roles and Dockerfile behavior](https://docs.cloud.google.com/run/docs/deploying-source-code)
- [Explicit build identity](https://docs.cloud.google.com/run/docs/configuring/services/build-service-account)
- [Firebase Hosting roles and required API Keys Viewer](https://firebase.google.com/docs/projects/iam/roles-predefined-product#hosting)
- [Cloud Run public access and permission requirements](https://docs.cloud.google.com/run/docs/authenticating/public)
- [Firebase Cloud Run rewrites and supported regions](https://firebase.google.com/docs/hosting/cloud-run)
- [Cloud Run deployment flags](https://docs.cloud.google.com/sdk/gcloud/reference/run/deploy)
- [Firebase CLI credential selection implementation](https://github.com/firebase/firebase-tools/blob/master/src/requireAuth.ts)
- [Firebase CLI config store](https://github.com/firebase/firebase-tools/blob/master/src/configstore.ts)

Verified locally: dummy checkpoint, fresh-clone checkout procedure against a
local fixture, guide shell/Python syntax and rewrite-generation logic. GitHub
access/commit availability, invitation acceptance, cloud identities/APIs, region,
site and hosted success are **not** verified by this document.
