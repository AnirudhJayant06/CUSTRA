# Custra A2A Knowledge Retrieval Implementation Plan

> **For agentic workers:** Use superpowers:executing-plans inline. No subagents; user explicitly authorized implementation on 2026-10-18.

**Goal:** Implement the approved natural-language complaint and document-knowledge flow while preserving existing booking and lifecycle behavior.

**Architecture:** Focused model roles use typed outputs; deterministic services own state, evidence and side effects. Product document ingestion persists extracted facts and source passages with vectors in existing Firestore; bounded product-scoped cosine retrieval avoids a new hosted index. Chat-only media uses direct multimodal inspection. Existing leases and replay identities guard external work.

**Tech Stack:** FastAPI/Pydantic, Google ADK/Gen AI, Firestore, private Storage, A2A SDK, React/Vite.

**Spec:** docs/superpowers/specs/2026-10-18-custra-a2a-knowledge-retrieval-design.md

## Global constraints

- Product document ingestion is reusable; chat-only documents are never embedded until explicit promotion.
- Routine factual answers auto-send; sharing and booking require consent. Profile phone is never changed by complaint input.
- No automatic repair/retry loop; initial operation plus at most two manual retries, durably counted.
- Persist history, pending requests, provenance and revisions; retain original/resolved questions internally.
- No cloud mutations, paid acceptance calls, commit/push/deploy or agents without applicable authorization. Offline tests cannot prove live-model understanding.

## Review focus

- Uncertain extraction and wrong-product files cannot overwrite confirmed facts (Tasks 1–2).
- Duplicate ingestion/concurrent corrections cannot corrupt knowledge (Tasks 1–2).
- Pausing/correction during an in-flight send cannot falsely imply retraction (Task 3).
- File consent is bound to the selected version and cannot become a permanent public URL (Task 4).
- Browser reopen cannot reset retry budget or duplicate booking (Tasks 3–5).

## Task 1: Typed knowledge and persisted product evidence

Files: create backend/app/models/knowledge.py, backend/app/services/knowledge.py; extend repository.py. Tests: backend/tests/unit/test_knowledge.py.
Interfaces: KnowledgeService.get(product_id), merge_facts(product_id, facts, source), search(product_id, query), ingest(document_id), inspect_chat(case, document_id, question), promote(case, document_id). Inject store/model/files dependencies. Firestore knowledge updates are transactional; product-scoped passages retain readable source content/version.
- [x] Write failing tests for conflict handling, scope, exact identifiers, revisions and profile isolation.
- [x] Run targeted tests and inspect expected failure.
- [x] Implement validated contracts, provenance, bounded vector matching and Firestore transactions.
- [x] Verify targeted tests pass.

## Task 2: Model roles and reusable ingestion

Files: create backend/app/agents/knowledge.py; modify config.py, main.py, files.py, api/documents.py; extend knowledge tests and API tests.
Interfaces: async resolve(question, context); extract(content, media_type, context); embed(texts, query=False); compose(question, evidence); outputs Pydantic contracts. Ingestion uses content hash/version, max 5 MB existing upload bound, extracted text <= 40k characters, <= 64 passages per document, <= 128 candidate passages per query and 6 evidence passages; model work <= 30s per call and request <= 45s. Publish complete document processing atomically and retain failed status separately from upload readiness.
- [x] Write failing tests: product-only indexing, chat no-embedding, PDF/image classification, promotion and failed extraction.
- [x] Implement bounded multimodal calls, schema validation and shared ingestion entry point.
- [x] Verify no automatic model retries and no whole-file semantic answer shortcut.

## Task 3: Natural-language conversation, handoff and correction

Files: create services/conversation.py; modify cases.py, repository.py, leases.py, api/complaints.py, models/exchange.py, agents/consumer.py; tests/unit/test_conversation.py.
Interfaces: ConversationService.advance uses acquired existing operation; submit_input(case_id, expected_version, text, field, document_id), pause(case_id, expected_version), resume(case_id, expected_version). Persist supported answer/evidence and outgoing payload before send; retries reuse them. Backend progress depends on business replies, not runtime phrase-to-field mappings. Retain legacy snapshot reader for pre-existing cases only.
- [x] Write failing tests: text-only question resolution, missing facts, complaint-local phone, reuse serial, pause/version conflicts, retry exhaustion.
- [x] Implement typed orchestration and additive Firestore case transitions with handoff history.
- [x] Verify invalid model evidence never causes send; inspect app-close recovery and stable IDs.

## Task 4: Business simulator and attachment transport

Files: models/exchange.py, services/a2a_gateway.py, manufacturer-agent/app/executor.py, simulator tests and gateway integration tests.
Interfaces: new natural-language scenario carries text/evidence with optional explicit attachment bytes in A2A file parts; data payload includes validated attachment digest/media/name and receipt. Existing basic scenario remains readable for saved cases. Simulator validates evidence shape, not answer templates; phrasing variations stay solely on business side. No permanent public file URLs.
- [x] Write failing tests: varied question text without requested-field hints, stable replay, consent/receipt, wrong attachment version.
- [x] Implement protocol contract and preserve booking replay.
- [x] Run simulator/gateway tests.

## Task 5: Customer controls and document states

Files: hooks/useCaseProgress.js; create components/ConversationActions.jsx; modify CaseDetail.jsx, CasePhotos.jsx, DocumentUpload.jsx, product document display and styles; frontend browser/unit tests.
Interfaces: pendingUserRequest drives contextual form; Pause and correct/Resume; separate Save to product and Share this/Choose another; internal rewrites/evidence not rendered. Fetch independent state in parallel, abort stale effects and guard writes; preserve compact pastel design and accessible labels.
- [x] Write browser tests for handoff, phone isolation, indexed upload state/promotion, pause/correction and bounded manual resume.
- [x] Implement minimal existing-theme controls; pending/failed/searchable are distinct from stored-file readiness.
- [x] Verify mobile/desktop interaction, keyboard access and refresh restoration.

## Task 6: Whole-flow verification and handoff

Files: backend/tests/integration/test_knowledge_flow.py, tests/support/demo_server.py, docs/LOCAL_VERIFICATION.md, docs/SESSION_STATE.md.
- [x] Add offline vertical-flow tests with actual persistence/model boundaries injected: varied questions, documents, user handoff, sharing, booking, reopen.
- [x] Add opt-in real-model evaluation for four purchase-date phrasings with changed facts and separate expected-answer evaluator; do not run paid calls implicitly.
- [x] Run backend/simulator suite, frontend unit/build and relevant browser checks; self-review against all spec acceptance cases.
- [x] Record actual results, unresolved external acceptance and exact next step. No success claim for tests not executed.

Execution note: user's direct implement instruction preserves inline execution and authorizes application edits; no additional routine permission request. Application work will use a feature branch in the current checkout to keep local development usable and avoid duplicating existing local environment. No commits or shared branch updates are implied.


## Execution results

Implemented inline on `feat/a2a-product-knowledge`; no commit/push/deployment.
A local Firestore emulator exercises actual transactional persistence; model and
bucket doubles keep local tests free of cloud mutations. The live resolver/answer
evaluation is implemented as an explicit opt-in and was not run. See
`docs/LOCAL_VERIFICATION.md` and `docs/SESSION_STATE.md` for final counts and
remaining live-model/business acceptance boundaries. Self-review was used because
the user explicitly prohibits subagents.

Implementation refinements: 256-dimensional embeddings, configurable separate
embedding region; extensible product details; cached complete chat extraction;
withheld uncertain passages; complaint-local intake contact data. Existing basic
cases remain resumable; only new natural cases use the new pipeline.
