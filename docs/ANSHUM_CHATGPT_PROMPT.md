# Copy this prompt into ChatGPT

Share `ANSHUM_DUMMY_DEPLOYMENT_GUIDE.md` with this prompt and provide the
repository URL https://github.com/AnirudhJayant06/CUSTRA. Source must come from
GitHub; do not attach code archives, credentials or authentication transcripts.

```text
I am Anshum, working with Anirudh on Custra for AI Builder Cup. Guide me one step
at a time through deploying the historical dummy app. First read the attached
deployment guide and follow its owner/teammate division of responsibilities.

Fixed Google Cloud project: custra-mvp-2026. I use my own Google account with IAM
access to that existing project. Anirudh has invited me as an additional Owner;
the last confirmed status was pending invitation, so verify acceptance first. Do not create a new Cloud project or ask for
Anirudh's account/password/credential file. Never use anything related to Sony,
another project, shared credentials or legacy configuration. If there is even
slight uncertainty about account, project, region, site, source or permissions,
stop and ask for confirmation.

Repository: https://github.com/AnirudhJayant06/CUSTRA
Dummy checkpoint: eb0245188c76052b1296aa7abe0728722c5371d0.
Guide me to clone this repository into a fresh folder and use detached HEAD at
that exact commit. Do not assume the default branch contains the dummy. Verify
GitHub access and commit availability before deployment. Anonymous access was
not verified by Anirudh's assistant; if private, I need my own GitHub access,
separate from Google Cloud IAM. If the commit is missing, stop and ask Anirudh;
do not push, substitute another branch or ask for a source ZIP. Never reset,
clean or overwrite an existing checkout. No commits or pushes are authorized.

The guide/prompt themselves may not yet be published in the repository. Use the
separately provided guide; do not assume you can fetch it from GitHub. If you
cannot access the private repository, guide my own terminal commands and use
sanitized non-sensitive results, rather than requesting credentials or archives.

The dummy is React/Vite plus a FastAPI echo API, with local photo preview. It has
no Gemini, Firestore, real uploads, login or A2A. Its deployment is a rehearsal,
not proof of final submission compliance. The full MVP is separate ongoing work.
Retail & Commerce eligibility has been confirmed by Anirudh. Final submission
needs actual Firebase/Firestore/Cloud Run/Gemini use, public working links,
accessible GitHub source, the prescribed PDF deck and a public 3-minute video.

Deployment approach: Cloud Run source deployment using backend/Dockerfile,
explicit dedicated build and runtime service accounts, then Firebase Hosting
for frontend/dist with /api/** rewritten before the SPA fallback. Use the
guide's isolated gcloud/Firebase configurations and explicit --project and
--account flags. Do not fall back to other ADC or FIREBASE_TOKEN credentials.

Before providing deployment commands, confirm that Anirudh has:
- Confirmed my Owner invitation is accepted and I can access the Custra project.
  Do not add the older narrower-role set on top of accepted Owner access.
- Confirmed GitHub collaborator access where needed and the exact dummy commit.
- Prepared the named build/runtime identities and their required permissions.
- Approved the actual region, backend service name, Hosting site ID and source.
- Verified billing/API/Firebase prerequisites and approved resource creation,
  public dummy access, build/deployment costs and publishing to the chosen site.

Anirudh handles IAM/API enablement, billing and public-access approval. I handle
the reviewed build/deployment and functional checks. The Owner invitation was
already chosen by Anirudh; do not infer it is accepted. Do not add further broad
roles, change IAM, or create service-account keys or API keys as shortcuts.
Do not change any project/resource/billing/IAM setting without its owner's
explicit approval. If you have execution tools, do local preparation first;
ask before any cloud mutation or deployment.

Explain each step's purpose, which person runs it, the expected non-sensitive
result and when to stop. Wait for my result before the next dependent step.
Never ask me to send credentials, tokens, OAuth codes or authentication URLs;
all authentication prompts must be completed privately in my terminal/browser.
Verify current Google/Firebase CLI guidance using official documentation when
needed. Check errors before suggesting changes and avoid repeated blind retries.

End only after checking the public Hosting URL, API health, real echoed form
submission, validation, mobile photo preview and the four standard-library HTTP
tests. Summarize deployment identifiers, URLs, source checkpoint, test evidence
and blockers. Do not claim that this dummy satisfies the final AI requirements.

Begin by checking whether my Google Cloud Owner invitation and any GitHub
invitation are accepted, whether the guide's setup is complete, and which terminal
environment I am using. Do not request secrets.
```
