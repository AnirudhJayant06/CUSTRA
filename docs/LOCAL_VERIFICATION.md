# Custra local verification — 16 October 2026

This is the final local self-review record for the approved V1 scope. The user
prohibits subagents; no independent reviewer was used.

## Evidence

Pre-push recheck on 16 October: backend/simulator suite **74 passed, 8 skipped**
with emulator and live-model opt-ins disabled; frontend client suite passed;
production build and Python dependency check passed. Browser suite **6 passed**
using installed Chromium selected with `CUSTRA_CHROMIUM_PATH`. Restricted-runner
networking prevented the first server-readiness check; running with loopback
access resolved it. The default Playwright browser was absent, so the documented
browser override was used. No application changes were needed. All eight Bash
blocks in `LOCAL_SETUP.md` parse; its Python configuration generator and shell
sourcing were executed in an isolated fixture, including private file permissions.
The earlier emulator/live results below are historical evidence, not rerun claims.

| Check | Result |
| --- | --- |
| Project Python environment | `backend/.venv`, Python 3.12; ADK 2.12.0, A2A SDK 1.2.2 |
| Full backend/simulator suite with loopback Firestore emulator | 80 passed, 2 opt-in live checks skipped |
| Direct client unit tests | 3 passed |
| Browser suite | 6 passed across mobile 390px and desktop |
| Vite production build | Passed |
| Python dependency consistency | No broken requirements |
| Tracked diff whitespace check | Passed |
| API and simulator Docker builds | Both passed |
| Container smoke checks | API health 200; private data 401/no-store; correct simulator Agent Card URL; custom ports; UID/GID 10001:10001 |
| Real local A2A compatibility | Official SDK messages/context/schema passed |
| Offline real ADK/GenAI execution | One request to explicit Vertex project/global endpoint; no Google call |
| Fresh-process recovery | API/simulator fixture processes discarded; same case/context resumed from emulator, booked with 10 unique events |
| Isolated live Gemini answer | 1 passed in 3.02 seconds, no warnings; dedicated Custra ADC/project/quota |
| Four-answer live-model rehearsal | 1 passed in 9.82 seconds, no warnings; local A2A/emulator persistence, simulated booking and explicit closure |
| Hosted Firestore persistence | Dedicated Custra ADC; create-only fictional write and exact-data read in a fresh process passed; `(default)`, Standard/Native, `asia-south1` |
| Real Storage + hosted Firestore through local app | PNG upload, exact-byte download and saved document metadata passed before/after API restart; anonymous app/bucket requests denied (401/403) |
| Browser refresh with hosted persistence | User confirmed product document remains available after refresh |

The emulator project is `demo-custra-tests`, with isolated random test namespaces.
Browser and process-recovery fixtures use a fictional model boundary. Storage tests
use a fake bucket. These fake boundaries do not establish Storage or hosted IAM behavior. Separately,
the opt-in live model rehearsal passed with four real answers using only dedicated
Custra ADC and the explicit resource/quota project `custra-mvp-2026`.

## Review focus and fixes

- Duplicate creation/advance/booking: transaction races, versions, leases, stable
  operation/event IDs and persistent simulator replay are covered. Stale workers
  cannot commit after lease renewal. Interrupted model compute can repeat on retry.
- Refresh/restart: browser refresh and fresh-process recovery preserve the original
  case snapshot, A2A context and committed events. User edits affect future cases.
- Session boundaries: direct unauthenticated API families are rejected before store
  or model access. Revocation, expiry, Origin checks and no-store responses pass.
- Invalid model content/fact refs/files and stale slots do not fabricate success.
  User confirmation remains the only closure action.
- Five review findings were reproduced and fixed RED→GREEN: Unicode username
  comparison; structured cloud errors; session-expired event on upload; failed
  logout preserving a retryable UI; backwards Tab escaping the address dialog.
- Approved optional case photo upload/view UI was completed with a failing browser
  scenario first, followed by successful refresh/preview checks in both viewports.

No unresolved local code finding from this self-review requires another change.
Live acceptance remains incomplete, as listed below; this is not an MVP-complete
or deployment-ready claim.

## Execution decisions

1. Continue in the existing `develop` checkout to preserve the user's untracked
   source work. No reset, clean, staging, commit or push. An isolated worktree would
   not contain those untracked sources without copying them.
2. Continue independent local tasks while Task 1 authentication is blocked, under
   the user's explicit authorization. The model gate remains open; if access is
   unavailable, the live demo cannot be accepted.
3. Validate generated text against a readable fact template, in addition to exact
   requested field references. This rejects invented content at the cost of rigid
   answer phrasing; successful live behavior is still to be checked.
4. Return the enclosing complaint from booking so uncertain ERROR/recovery state
   is visible to the UI. Recover a pinned pending slot through the fixed server
   operation even after a browser loses its request key; changing that pending
   slot remains rejected.
5. Use repeatable HTTP/browser/process tests for the plan's local manual checks.
   Record local fixture results separately from hosted/live checks. Incorrectly
   treating them as hosted proof would hide IAM, cookie-routing or bucket issues.
6. Use author self-review because the user explicitly forbids subagents. This has
   less independence than a separate reviewer; no external review is claimed.

No additional feature scope or deferred feature was introduced. No cosmetic minors
were added to the work queue.

## Remaining gates

- Verify the complete live complaint/booking conversation using hosted Firestore;
  earlier real Gemini/A2A rehearsal used emulator persistence.
- Confirm project/region/rules and separately authorize cloud resources, IAM,
  secrets/billing changes and deployment before hosted verification.
- Verify Hosting cookie routing, direct API denial, private simulator IAM and one
  complete hosted rehearsal. Freeze by 18 October 2026, 16:00 IST.

For a fresh clone and isolated authentication, follow [LOCAL_SETUP](LOCAL_SETUP.md).
Deployment bindings and commands are in [deployment.md](../infrastructure/deployment.md).
