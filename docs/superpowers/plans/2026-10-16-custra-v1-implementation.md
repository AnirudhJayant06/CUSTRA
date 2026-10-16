# Custra V1 Implementation Plan

> Execution method: the user implements; Codex supplies step-by-step code and reviews results. No subagents or application edits without explicit user authorization. If assistant execution is later requested, use superpowers:executing-plans task by task; do not infer execution permission from design approval. Checkboxes track verified work, not proposed work.

**Goal:** Build the approved single-account Vault and automated complaint-registration demo by 18 October 2026, 16:00 IST.

**Architecture:** React/Vite on Firebase Hosting calls FastAPI on Cloud Run. The API uses an ADK/Gemini Consumer Agent and a separate private A2A Business Agent simulator. Firestore stores application state; Cloud Storage holds private files.

**Tech Stack:** Existing React, Vite, Python/FastAPI; Google ADK, official A2A Python SDK, Vertex AI Gemini, Firestore, Cloud Storage, Secret Manager, Cloud Run, Firebase Hosting.

**Spec:** [Approved system design](../specs/2026-10-15-custra-v1-system-design.md). Approved by the user on 16 October 2026. The user explicitly authorized local implementation on 16 October 2026; cloud mutations, commits and pushes remain excluded.

## Latest verification — 16 October 2026

- Local backend/simulator suite with loopback Firestore emulator: **80 passed, 2 skipped** (opt-in single Gemini check and four-answer live rehearsal).
- Browser suite: **6 passed** across 390px mobile and desktop. Three direct client unit tests, Vite build, pip dependency check and whitespace check passed.
- Both Docker images built and ran locally as non-root users on custom ports; API health/private-route denial and simulator Agent Card passed.
- Fresh subprocesses recovered the in-progress case and A2A context from Firestore and completed one booking with 10 unique events. Model/bucket boundaries remain fictional in browser/recovery fixtures.
- Review fixes were verified RED→GREEN: Unicode login, cloud-error JSON, expired-upload redirect, failed logout and backwards address-dialog focus. Optional case photo controls were completed from the approved scope.
- Dedicated Custra ADC/project/quota verified. Single live Vertex answer: **1 passed in 3.02 seconds**; four-answer real-model/local-A2A/emulator rehearsal: **1 passed in 9.82 seconds**. Both had no warnings. Private bucket/hosted IAM/Hosting/rehearsal remain open.
- No cloud mutations, deployments, commits or pushes. All future cloud checks must use dedicated Custra credentials and explicit project/quota; ask whenever identity/resource scope is uncertain.

## Global constraints

- One shared demo username/password, server-side verification and session checks. No Google sign-in, multi-user isolation or per-user/global usage quotas.
- No extraction, serial-number requirement, warranty dispute, live manufacturer contact or real payment.
- No upfront time preference. Exact date/time selection is the final registration step; only confirmation follows. Later closure requires an explicit user action.
- Preserve category/brand selectors, product tabs, global complaints, profile, saved addresses and add-address popup.
- Show mock service centers and simulated business outcomes honestly. Consumer answers are real model output based on supplied facts.
- No background execution promise: closing the browser stops dispatching new steps; refresh recovers saved progress.
- Four business questions maximum, 40-second advance deadline, eight-hour session, PDF/JPEG/PNG uploads up to 5,000,000 bytes each; small bounded responses.
- No process-local authoritative case state. No automatic retries that can generate unbounded model calls.
- Do not touch unrelated untracked files, tooling or CI. Commits/deployments are user actions; this plan is not permission for Codex to perform them.
- General missing-information pause/resume is excluded from the required tasks. Reassess only after core acceptance; do not extend the deadline.

## Review focus

1. Double click, two tabs or a lost booking response: one case/appointment and no duplicated transcript (Tasks 5–7).
2. Browser closes or service restarts: saved progress remains recoverable and stale workers cannot overwrite newer state (Tasks 5–6).
3. A profile/address changes during a case: original facts stay stable; new cases see edits (Tasks 3 and 5).
4. Expired login, direct run.app access or cross-origin mutation: no unauthorized data/model access (Tasks 2 and 9).
5. Malformed model response, stale appointment slot or invalid file: no fabricated success, unauthorized booking or unsafe preview (Tasks 4, 6–8).

## File responsibilities

- `backend/app/main.py`: app assembly and health endpoint; retire the dummy endpoint when complaint API replaces it.
- `backend/app/config.py`, `api/auth.py`, `services/auth.py`: validated settings and demo sessions.
- `backend/app/models/{account,product,complaint,exchange}.py`: Pydantic request/response contracts.
- `backend/app/services/{repository,files,cases,a2a_gateway}.py`: persistence, private files, state transitions and A2A transport.
- `backend/app/api/{account,products,complaints}.py`: authenticated HTTP routes, no model logic.
- `backend/app/agents/consumer.py`: bounded ADK answer generation.
- `backend/app/data/{catalog,service_centers}.json`: static demo fixtures.
- `manufacturer-agent/app/{main,executor,store}.py`: A2A interface, deterministic business rules, persistent replay results.
- `frontend/src/api/client.js`: shared session/error-aware client.
- `frontend/src/pages/{Login,Account,Vault,ProductDetail,NewComplaint,Complaints,CaseDetail}.jsx`: route-level screens.
- `frontend/src/components/{AddressDialog,ProductForm,AppointmentDialog,ConversationTimeline}.jsx`: reusable forms/dialogs.
- `frontend/src/hooks/useCaseProgress.js`: one bounded advancement loop for the active case.
- `backend/tests/unit/`, `backend/tests/integration/`, `manufacturer-agent/tests/`, `frontend/tests/`: focused tests owned by tasks below.
- `infrastructure/deployment.md`: project bindings, deployment commands and verification record; no secrets.

## Task 1: Prove the agent boundary and freeze dependencies

**Files:** create `backend/app/models/exchange.py`, `backend/app/agents/consumer.py`, `backend/app/services/a2a_gateway.py`, `manufacturer-agent/app/main.py`, `manufacturer-agent/app/executor.py`, `manufacturer-agent/requirements.txt`, `backend/tests/integration/test_agent_boundary.py`; modify `backend/requirements.txt`.

**Interfaces:** `ExchangeRequest(schema_version, case_id, operation_id, scenario_id, action, stage, data)` and `ExchangeResponse(question_code, requested_fields, display_text, next_stage, reference, slots, appointment)`; action is start/answer/listSlots/book. `A2AGateway.exchange(request: ExchangeRequest) -> ExchangeResponse` is async. `ConsumerAgent.answer(question: ExchangeResponse, facts: dict, transcript: list[dict]) -> ValidatedAnswer` is async; define `ValidatedAnswer(text: str, field_refs: list[str])` in exchange models. Facts contain named profile/product/address/issue sections.

- [ ] Record project ID, billing access, deploy region and Vertex model location in `infrastructure/deployment.md`; check supplied competition rules before selecting restricted services. Never copy credentials into this record.
- [ ] Create an isolated Python environment and resolve a compatible ADK/A2A SDK pair; test one available GA Flash-class Gemini model through Vertex AI. Record exact working versions/model ID and pin dependencies. Do not guess pins in advance.
- [x] Write `test_real_a2a_start_and_answer`: actual SDK transport must produce a product question, then accept a structured answer; assert protocol context correlation and response-schema validation. Run it before implementation and confirm the missing behavior fails.
- [x] Implement minimal start/answer exchanges using official SDK transport and a scripted executor. Implement a one-call Consumer Agent with supplied facts, field references and bounded output; no booking/closure tools. Use fresh per-answer ADK context. Expose pending stages for later tasks.
- [x] Verify real local A2A exchange and real model call using pinned dependencies: SDK checks passed in the backend suite; the isolated live answer check and four-answer rehearsal passed separately. Cloud/model-dependent tests remain explicitly opt-in.
- [x] Record local SDK compatibility results in `infrastructure/deployment.md`. Real A2A transport, offline ADK/GenAI configuration and dedicated-ADC live Gemini checks pass. Private hosted integration remains a separate gate.

## Task 2: Secure demo login and shared API foundation

**Files:** create `backend/app/config.py`, `backend/app/services/repository.py`, `backend/app/services/auth.py`, `backend/app/api/auth.py`, `backend/tests/unit/test_auth.py`; modify `backend/app/main.py`; create `frontend/src/api/client.js`, `frontend/src/pages/Login.jsx`; modify `frontend/src/App.jsx`, `frontend/package.json` and lockfile.

**Interfaces:** `Settings` loads project, model, bucket, A2A URL, credentials and agent-enabled flag. `SessionStore.create(token_hash, expires_at)`, `get(token_hash)`, `revoke(token_hash)` operate in Firestore. `require_session(request) -> DemoSession` protects all data routes. Frontend `api(path, {method, body, signal, headers}) -> Promise<JSON>` handles JSON errors and credentials; use a separate upload helper for FormData.

- [x] Add test dependencies pytest/httpx and injected fake stores; write `test_login_sets_session`, `test_expired_or_revoked_session_rejected`, `test_cross_origin_mutation_rejected`. Assert 401 without a session, cookie name `__session`, HttpOnly, eight-hour expiry, logout revocation, and production Secure flag.
- [x] Run `python -m pytest backend/tests/unit/test_auth.py -v`; confirm tests fail before implementation.
- [x] Implement password-hash verification, random opaque token/hash persistence, explicit expiry checks, Origin checks and `private, no-store` responses. Keep secrets server-side. Implement the JSON error shape `{code,message,retryable,field_errors?}` consistently.
- [x] Add the login route and client session check, React Router navigation and expired-session redirect. Leave the shared demo identity explicit. No registration screen or provider integration.
- [x] Rerun auth tests, `npm --prefix frontend run build`, and manually verify login/logout on local proxy. Later routes must reuse `require_session`, including downloads and direct Cloud Run requests.

## Task 3: Profile, saved addresses and basic Vault

**Files:** create `backend/app/models/account.py`, `backend/app/models/product.py`, `backend/app/api/account.py`, `backend/app/api/products.py`, `backend/app/data/catalog.json`, `backend/app/data/service_centers.json`, `backend/tests/unit/test_vault.py`; extend repository/main; create Account/Vault/ProductDetail pages, AddressDialog/ProductForm components.

**Interfaces:** GET/PATCH `/api/profile`; GET/POST `/api/addresses`, PATCH `/api/addresses/{id}`; GET/POST `/api/products`, GET/PATCH `/api/products/{id}`; GET `/api/catalog`, `/api/service-centers`. Model fields follow spec section 6. IDs are server-generated. Profile email/phone are saved facts, not verified contact channels.

- [x] Write tests for save/read/edit, required trimmed fields, dependent category/brand validation, invalid record IDs and repeated seed execution. Assert dummy address seeded once, new address visible through the same GET after refresh, and no hidden serial-number requirement.
- [x] Run `python -m pytest backend/tests/unit/test_vault.py -v` and observe expected failures.
- [x] Implement authenticated routes and Firestore records under the shared demo namespace. Seed a fictional profile address; require name/phone/email before starting a complaint. Supply 10–15 product categories and 10–15 brand choices per category as static fixtures; do not present this list as agent coverage.
- [x] Implement screens and product tabs. AddressDialog saves to the common collection, selects the new address after success, preserves complaint draft on cancel/failure, and supports keyboard focus. Keep brand/model/basic dates manual. Display labeled mock centers with no actionable fake phone links.
- [x] Rerun tests and build. Manually add/edit a product and address, refresh, and verify both views use the same data. Show empty Complaints tab until Task 5.

## Task 4: Private document storage and viewing

**Files:** create `backend/app/services/files.py`, `backend/tests/unit/test_files.py`; extend products API/models, ProductDetail and client upload helper.

**Interfaces:** `FileService.upload(parent_id, filename, stream, media_type) -> Document`; `FileService.open(document_id) -> authorized stream`. POST `/api/products/{id}/documents`, GET `/api/documents/{id}/content`; support optional case photo attachment through POST `/api/complaints/{id}/documents` once Task 5 exists, using the same service. Do not send file contents to the model.

- [x] Write `test_rejects_oversize_or_disguised_file`, `test_failed_upload_not_ready`, `test_download_requires_session`. Assert 5,000,001 bytes rejected; PDF/JPEG/PNG accepted only with corresponding content signature; HTML/SVG rejected; unavailable metadata not returned as ready.
- [x] Run `python -m pytest backend/tests/unit/test_files.py -v` and confirm missing behavior fails.
- [x] Implement bounded streaming upload, generated object names, private bucket access, pending/ready metadata and failure cleanup. Stream downloads through authenticated backend with correct content type, nosniff and no-store. Use attachment disposition for PDFs; image preview only for validated images.
- [x] Add optional product document and case photo upload/view controls; rerun local tests/build and verify browser upload/view after refresh.
- [ ] Verify private Cloud Storage content survives process restart and direct bucket URL is inaccessible. Document viewing, not extraction, completes this task.

## Task 5: Persistent complaint snapshots and duplicate protection

**Files:** create `backend/app/models/complaint.py`, `backend/app/services/cases.py`, `backend/app/api/complaints.py`, `backend/tests/unit/test_cases.py`, `backend/tests/integration/test_case_transactions.py`; extend repository/main; create NewComplaint/Complaints pages and product complaint listing.

**Interfaces:** `CaseService.create(payload, idempotency_key) -> Complaint`, `get(case_id) -> Complaint`, `list(product_id=None) -> list[Complaint]`. POST/GET `/api/complaints`; GET `/api/complaints/{id}`. Create payload: productId, addressId, issueSummary, description; no timePreference. Store immutable facts snapshot. Define ERROR with recovery_phase and five spec statuses.

- [x] Write `test_duplicate_create_replays`, `test_same_key_changed_payload_conflicts`, `test_snapshot_survives_profile_edit`, `test_incomplete_profile_blocks_creation`. Assert same case ID for replay, 409 for conflicting reuse, original address after edit, and field errors before any model call.
- [x] Run `python -m pytest backend/tests/unit/test_cases.py -v`; implement validation, immutable snapshots and transactional idempotency records. Case state starts PROCESSING; reject unsupported scenario without inventing success.
- [x] Implement the form using saved product/address and an add-address popup. No name/email/time input here. Submit from user event with a stable request key; refresh must not create a case. Wire global/product lists to the same records.
- [x] Against Firestore emulator, race two identical creation requests and assert one case. Run `python -m pytest backend/tests/integration/test_case_transactions.py -v`; configure emulator environment explicitly so tests cannot touch production.
- [x] Rerun unit tests/build; verify with real-adapter HTTP integration checks that edited profile affects only new complaints (automated equivalent of the manual check).

## Task 6: Durable bounded agent conversation

**Files:** extend cases/repository/consumer/gateway/executor; create `manufacturer-agent/app/store.py`, `manufacturer-agent/tests/test_replay.py`, `backend/tests/unit/test_advance.py`; extend transaction integration tests; create CaseDetail, ConversationTimeline and useCaseProgress.

**Interfaces:** async `CaseService.advance(case_id, expected_version) -> Complaint`; GET events with `after=sequence`; POST advance with expectedVersion. Repository acquires lease, returns operation ID, commits only matching lease/version and stable event IDs. Simulator persists response by operation ID before returning it.

- [x] Write tests for expired leases, two simultaneous advances, lost A2A response replay, malformed model output and unsupported fact references. Assert stale commit rejected, one visible event per ID, same business reference on retry, and no advancement from invalid output.
- [x] Run `python -m pytest backend/tests/unit/test_advance.py manufacturer-agent/tests/test_replay.py -v` and confirm failures before implementing recovery logic.
- [x] Implement at most one answer call per advance and four questions total: product, issue, contact, address. Use 40-second total deadline, 60-second expiring lease and explicit SDK timeouts. Run external calls outside transaction callbacks; persist answer before transport where possible. Verify structured values from the snapshot and reject unsupported answer content.
- [x] Implement real A2A context correlation, independent completed protocol exchanges and persistent simulator replay. Registration returns a mock reference and stable future slot IDs. Application transitions to AWAITING_APPOINTMENT only after schema validation.
- [x] Implement single mounted-page progression loop with one in-flight operation; GET does not start work. Stop on unmount, ERROR, appointment selection or completion. Render committed messages only; stop indicators on error and provide explicit retry. React Strict Mode remounts must be harmless through server version checks.
- [x] Rerun unit/transaction tests, real local SDK exchange and frontend build. Browser refresh and fresh-process API/simulator fixtures recover saved progress using the local Firestore emulator; model output is fake only in recovery fixtures. No exactly-once LLM billing claim: retry can repeat compute after an interrupted model call.

## Task 7: Final appointment dialog and user-confirmed closure

**Files:** create `frontend/src/components/AppointmentDialog.jsx`, `backend/tests/unit/test_appointments.py`; extend cases/complaints API, business executor/store, CaseDetail.

**Interfaces:** GET `/api/complaints/{id}/slots`; POST appointment with `{slotId}` and Idempotency-Key; POST confirm-resolution with `{confirmed:true}`. Async `CaseService.book(case_id, slot_id, idempotency_key) -> Appointment`; `CaseService.confirm_resolution(case_id, confirmed) -> Complaint`.

- [x] Write tests asserting dismissal creates no booking, stale slot returns conflict, replay returns same appointment, different second booking is rejected, and closure from PROCESSING or `confirmed:false` is rejected.
- [x] Run `python -m pytest backend/tests/unit/test_appointments.py -v`; implement state guards and persistent booking operation/replay. On uncertain response recover through the same operation ID, not a new booking.
- [x] Show available dated slots in Asia/Kolkata with a confirm action. Focus the dialog, preserve selected slot on recoverable error, and show Choose appointment after dismissal. On success show booking confirmation only—no extra registration questions. Later show Confirm issue resolved action on booked case.
- [x] Rerun tests/build; simulate a dropped booking response and ensure one appointment. Verify no background timer or agent message closes the complaint.

## Task 8: End-to-end browser checks and coherent demo presentation

**Files:** create `frontend/playwright.config.js`, `frontend/tests/custra.spec.js`; modify frontend package scripts/lockfile, styles and affected components.

**Interfaces:** test script `npm --prefix frontend run test:e2e`; base URL supplied through `CUSTRA_UI_URL`. Fixtures use a dedicated test namespace and deterministic fake model boundary; a separate live rehearsal verifies real Gemini/A2A.

- [x] Add meaningful browser scenarios: login → profile → address popup → Vault → complaint → automated conversation → appointment dialog → explicit closure. Cover refresh midway, dismiss/reopen scheduling, expired session, model failure and duplicate click. Assert state/results, not animation timings.
- [x] Run against the local fixture application and record failures; fix only behavior within the approved scope. Hosted test deployment remains a Task 9 gate.
- [x] Verify 390px and desktop layouts, keyboard dialog focus, reduced motion, no user composer and simulation labels. Old transcript must not replay typing effects after refresh.
- [x] Run local browser suite and production build.
- [x] Run one bounded real-model/local-A2A/emulator rehearsal using fictional data; four live answers, simulated booking and explicit closure passed.
- [ ] Run the separately authorized hosted rehearsal. Local transport/persistence does not establish hosted IAM/Hosting/private Storage behavior.

## Task 9: Hosted deployment, verification and freeze

**Files:** modify `backend/Dockerfile`, `firebase.json`, `README.md`; create `manufacturer-agent/Dockerfile`; finish `infrastructure/deployment.md`.

**Interfaces:** existing Firebase /api rewrite plus two Cloud Run services; backend session check on every protected route. Private simulator uses IAM invoker permission and audience-correct identity tokens, including Agent Card requests.

- [ ] User creates/selects cloud resources and identities, configures secrets outside Git, selects compatible region/model location and deploys both services. Set min instances 0, max 1 initially; test latency. No public simulator endpoint or unrestricted Storage/Firestore rules.
- [ ] Wire authenticated A2A client, private bucket and Firestore; replace Hosting placeholders and deploy frontend. Configure agent disable switch and billing alerts without representing them as spending caps.
- [ ] Verify login cookie through Hosting; authenticated responses are private/no-store. Direct public backend calls without session return 401; unauthenticated simulator calls fail at IAM. Confirm unauthorized requests never invoke Gemini.
- [ ] Run focused backend tests, browser suite, and full hosted live rehearsal; inspect logs for errors, accidental secrets and excessive retries. Stop model calls when agent switch disabled.
- [x] Update README to match approved scope and actual commands. Preserve evidence: tested versions, URLs, test results and known limitations. No real customer data in screenshots/logs.
- [ ] By 18 October 14:00 IST finish validation; reserve 14:00–16:00 for blockers. At 16:00 freeze development and move to submission documents. Record incomplete items honestly; do not add optional missing-information handling under deadline pressure.

## Schedule and checkpoints

16 October: Tasks 1–3 and earliest cloud connectivity check; start Task 4 if capacity.
17 October: complete storage and core Tasks 5–7; deploy full path by evening.
18 October morning: Tasks 8–9 verification; afternoon buffer then freeze.
This is a target for focused work, not a validated effort estimate. If behind, cut
cosmetic polish first; any removal of an approved core capability needs a scope decision.

After each passing task the user can make a focused checkpoint commit, staging only
that task's files. Do not stage all existing untracked directories. Codex must not
commit, push or deploy merely because those actions are listed here.

## Plan review and first handoff

Coverage self-review: Vault/profile/files Tasks 2–4; agent transport/runtime Tasks 1/6;
case records/recovery Tasks 5–6; final scheduling/closure Task 7; frontend/hosted checks
Tasks 8–9. Review-focus cases map to test tasks above. No application work completed.

Next: user reviews this plan. Then provide the first executable code/instructions for
Task 1 in small increments, with expected output, letting the user run each checkpoint.
Initial inputs needed: chosen Google Cloud project ID, billing/API access, and any
submission constraints on model/region. Never request passwords or API keys in chat.
