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

## Product knowledge and natural-language A2A (18 October 2026)

Implementation branch: `feat/a2a-product-knowledge`. The new pipeline is selected
for newly created cases when `CUSTRA_NATURAL_CONVERSATION=true` (default) and an
explicit project/model boundary is configured. Existing `basic` cases keep their
legacy protocol so they can resume. Set the flag false to keep new cases on the
previous demonstration flow.

Product Documents uploads run the shared extraction/indexing module. Chat-only
uploads are directly inspected for the pending question and are not embedded;
Save to product explicitly promotes them. Clear nonconflicting facts populate
versioned product knowledge. Phone edits in intake or chat are complaint-local.

New settings: `CUSTRA_EMBEDDING_MODEL=gemini-embedding-001` and
`CUSTRA_EMBEDDING_LOCATION=us-central1`. Resolver/answer roles use ADK with the
existing `CUSTRA_MODEL_ID` and `GOOGLE_CLOUD_LOCATION`; document extraction uses
multimodal Gen AI. No new dependency or hosted vector service is required.
Document and query vectors use distinct retrieval task types. The bounded
Firestore index stores at most 128 source passages per product with 256-dimensional
vectors and returns at most six supporting passages. These are MVP limits, not
large-corpus search guarantees. Current similarity cutoff is an initial heuristic
and needs real-data evaluation.

New storage is additive under the existing workspace: `knowledge`, `evidence`,
`document_processing`, complaint-scoped `document_inspection`, and private `turns`. Stored-file readiness and processing
readiness are distinct. Existing documents remain viewable; indexing runs for new
Product Documents additions. Existing unindexed documents are not automatically
backfilled. A failed preparation retains the original; enter the needed fact or
supply a corrected/new document. No new automatic model/embedding retry is added.

Original-file sharing requires explicit selected-file/version consent and a
business receipt. The local A2A simulator transfers bytes in a real SDK raw file
part and acknowledges its digest; real business contract compatibility still
requires acceptance testing. No permanent public bucket URL is generated.

Offline verification uses scripted model doubles and cannot establish semantic
understanding/extraction quality. `test_live_knowledge_resolves_purchase_paraphrases_without_runtime_field_hints`
is opt-in with `CUSTRA_RUN_KNOWLEDGE_MODEL=1` and explicit
`GOOGLE_CLOUD_PROJECT=custra-mvp-2026`; it permits at most eight paid resolver/answer
calls. Its four phrasings and changed expected facts are evaluated outside the
runtime prompts. Run only in the dedicated authorized credential environment.
This implementation session did not run paid model tests, mutate cloud resources,
commit, push or deploy.


Review notes: uncertain source passages are withheld from automatic retrieval;
clear facts remain usable. Compatible complete chat inspections can be reused
when the user explicitly saves the original to Product Documents. Additional
registration facts use validated `product.details.<snake_case>` keys rather than
sentence-to-answer mappings. Internal turn artifacts preserve the exact evidence
source and product revision. The index configuration fingerprints the embedding
space to avoid mixing incompatible vectors.


Final local verification: **122 backend/simulator checks passed, 3 live-model tests
skipped** with the loopback Firestore emulator. **30 mobile/desktop browser checks
passed**; the final new-flow subset passed **12/12** after review refinements.
Frontend unit tests and production build passed; new model schemas passed the
installed SDK transformation check. Actual mobile sharing and booking captures
were inspected. Read-only API/proxy/simulator health checks passed after local
service refresh. Review was inline without subagents. The real model, extraction
and embedding quality, and actual business contract remain external acceptance
work; no mocked test result is presented as proof of those capabilities.


## Nonblocking question preparation and removal of Pause and correct

Reproduced an address-grounding failure without a model call: the numeric guard
rejected the digit in an internal fact:address.line1 citation rendered in answer
text. Known citation markers are now removed from visible text before validating
exact values and numeric claims. Structured citations remain in internal evidence.

Address/contact answers use complaint snapshots without depending on product
document retrieval. Resolution is cached per operation; resolver/search/composer
attempt counts are persisted, capped at three per role, and share a 30-second
preparation budget (10 seconds per attempt, 32-second overall preparation bound).
After failures, complete saved facts produce a deterministic grounded answer.
Missing/ambiguous/conflicting details produce an explicit technician-confirmation
answer, are recorded in deferredQuestions, and advance the same A2A context. No
unknown value is saved as a known product fact. Deferral payloads are persisted
before external send and replay identically after lost responses. Optional turn
audit-storage failure does not discard an acknowledged business response.

Pause/resume endpoints, correction dropdown/state, queued-correction generation
and the A2A correct action are removed. A small compatibility path releases old
PAUSED cases. Old exhausted unsent preparation operations receive one bounded
recovery opportunity; this does not reset sent operations or booking limits.
Legacy fact handoffs and original-file consent offer a Continue option. Declining
file sharing sends a deferral, never private bytes. The simulator accepts such
deferrals and advances; actual business acceptance remains an integration boundary.

Transport/storage outages and ambiguous booking outcomes are not reported as
success. Existing saved values and historical messages are not rewritten by this
code change. No paid model calls or cloud-record repair were performed.

Verification for this refinement: 124 backend/simulator tests passed, 10
emulator/live opt-ins skipped in the current environment. Full browser suite:
32 passed across mobile/desktop; final natural-flow recheck 12 passed and final
consent/deferral review 4 passed. Frontend units/build and whitespace passed.
These local doubles establish workflow/grounding regressions, not live LLM
quality or production Firestore/business acceptance.
