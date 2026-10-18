# Custra: natural-language A2A and product knowledge

Date: 2026-10-18
Status: Approved by the user on 2026-10-18, with explicit subsequent authorization to implement. See the implementation plan and LOCAL_VERIFICATION.md for actual completion and acceptance evidence.

## 1. Outcome and scope

Custra represents a customer in a business conversation to register a product complaint and confirm a technician visit. It understands varied business questions, resolves follow-ups, retrieves supported facts, answers automatically, and requests customer input when needed. Reusable facts improve over successive complaints without changing unrelated profile or appointment information.

The MVP includes product JSON knowledge, product-document ingestion and retrieval, direct inspection of chat-only attachments, complaint memory, human handoff, explicit file-sharing/booking confirmation, pause/correction, and bounded user-initiated recovery.

Service-center appointments, troubleshooting, diagnosis, repair advice, broad warranty interpretation, feedback-driven step retry, specialized extraction models and automatic conditional retries are deferred. See ../../FUTURE_DEVELOPMENT.md. No public-web/manufacturer search is introduced. No autonomous conversation worker continues dispatching turns after the user leaves.

## 2. Current implementation and required change

Current source uses four scripted business questions with requested_fields and stage-to-field mappings. The consumer receives a backend-built exact answer_template and factsSnapshot; the backend sends snapshot values through A2A. Firestore persists cases, events and operation leases. Each consumer answer creates a fresh in-memory ADK session and receives the last eight events. Browser requests drive advancement. Uploaded files are stored and viewed, without semantic extraction or indexing.

The new flow replaces runtime sentence/question-code-to-answer shortcuts with interpretation and evidence retrieval. Product snapshots, events, operation identities, version checks, authentication, private file storage, booking confirmation and user-confirmed resolution remain useful foundations. Do not rebuild them without a specific integration need.

Primary source boundaries: backend/app/agents/consumer.py; services/cases.py, repository.py, files.py, a2a_gateway.py; models/exchange.py; manufacturer-agent/app/executor.py and store.py; frontend/src/hooks/useCaseProgress.js.

## 3. Components

| Component | Responsibility |
| --- | --- |
| Backend coordinator | Explicit workflow, record access, retrieval, persistence, consent, action validation and recovery |
| Resolver role | One focused model task: standalone question, requested information, relevant entities and clarification status |
| Document-understanding role | Multimodal classification, factual extraction, source-grounded description and supporting content |
| Answer role | Compose an answer from supplied evidence or identify missing/conflicting information |
| Product-document ingestion module | Reusable entry point for every new Product Documents attachment; extraction, knowledge updates and indexing |
| Retrieval module | Read structured facts first, then scoped passage search using a query embedding |
| A2A adapter | Exchange messages and supported attachments with the business; retain operation/context identifiers |

These are logical roles within the existing backend, not separate deployments. Closely related resolver tasks share one model call. Deterministic coordination does not require another LLM or a graph framework. Booking authorization is backend code, never a model instruction alone.

## 4. Persisted data and ownership

Keep existing per-complaint event records linked to their product. Do not aggregate all product conversations into one growing document or embed every chat message.

| Record | Proposed content |
| --- | --- |
| Product knowledge | productId, schemaVersion, revision, structured identity/purchase/recorded-warranty facts, provenance and changes |
| Fact provenance | fact path, source type, source/message/document ID, document version/page or passage, review status, update time |
| Document metadata | original storage reference, complaint/product associations, version/content identity, document type, short description, extraction/index status |
| Indexed passage | document/version, product/complaint/access scope, source location, readable content and embedding |
| Complaint | existing issue/contact/address/preference/snapshot and booking state, plus pending user request and workflow state |
| Turn artifact | original business message, internal resolved question, requested facts, evidence actually used, answer/delivery status and knowledge revision |
| Operation | stable identity, lease/version, persisted retry count, result and pending external outcome |

Physical field names and additive migration details belong in the implementation plan. Product JSON is a logical structured record, not a requirement to duplicate the product as a downloadable JSON file. Keep long source content and conversation events outside it.

Every read/search/download enforces the current authenticated workspace and relevant product/case boundaries. The existing shared demo workspace is not per-user isolation. Do not claim it is. The design does not introduce a multi-user identity migration; future per-user storage must add actual owner checks.

## 5. Product knowledge updates

Automatically save clear, nonconflicting extracted facts with provenance. Ask the user when identity, characters, dates or competing values are uncertain. A model-reported confidence number alone is insufficient. Preserve raw/source meaning: invoice date is not automatically purchase date; product nickname is not model; recorded warranty duration is not verified coverage.

User-provided reusable product facts (model, serial, purchase detail) and explicit corrections enter product knowledge. Repeated complaints can reuse these facts. Do not promote unsupported assistant/business claims as verified customer facts.

Complaint-time phone changes NEVER update Profile. They are complaint-specific contact overrides, even when phrased as a correction. Profile edits occur in Profile. Selected addresses, visit preferences and current symptoms remain complaint-specific unless the user separately performs an explicit relevant persistent edit.

Product revisions do not freeze a complaint against correction. New confirmed information can update subsequent answers; each already-sent answer retains its evidence/revision. Example: revision 3 supported a sent purchase date of 12 February; the user corrects it to 15 February in revision 4; keep the first message and send a correction, then use revision 4. Discard unsent drafts that depend on superseded facts.

## 6. Product Documents ingestion

All additions to Product Documents use one reusable module, whether uploaded on the product screen or saved from a chat. Process each new document/version; avoid duplicate work for already-processed identical content under the applicable scope and processing version.

1. Retain existing upload validation and private original storage.
2. Save durable processing state independently of upload status. Stored/ready to view does not mean searchable.
3. Use a supported multimodal LLM for MVP classification and extraction. An image may be an invoice, extended warranty, serial label, ordinary product photo or unrelated content; MIME type alone does not determine semantic type.
4. Produce a source-grounded description, supported reusable facts and readable source-linked content in the ingestion task. Distinguish product line items on multi-product invoices.
5. Validate and populate clear facts; retain uncertainty/conflicts for user review.
6. Split meaningful content into bounded passages, preserving identifiers and source locations. For images without text, index a supported factual description only when useful; never invent product facts to satisfy indexing.
7. Generate document embeddings, store readable passages alongside vectors, and expose the new indexed version only after successful completion.

Each addition enters the pipeline; unrelated/unsupported/unreadable content can finish as not indexable rather than fabricated searchable knowledge. Classify ordinary photos and retain them without unnecessary save-to-product prompts when supplied in chat.

Create embeddings once per content/processing version, not once per question. Document replacement stages a new index version; failed replacement does not remove previously usable evidence. Retrieval must not mix incomplete versions. No new automatic retry loop is introduced.

Description selects a document; source passages support an answer; the original file supports inspection and external sharing. The description is not a substitute for missing evidence.

## 7. Chat-only attachments and consent

Files uploaded during registration initially belong to that complaint and can answer its pending question. Inspect a chat-only PDF/image directly with the question and relevant conversation context using the multimodal LLM. Do not embed it merely because it appeared in chat. Where suitable, inspection and answering can be combined into one call.

Reusable facts extracted from the attachment may populate product knowledge with source references and uncertainty handling. This does not imply automatic product-level file association or automatic external transfer.

For a reusable invoice/warranty attachment, offer Save to this product's Documents / Not now. Acceptance adds a product association to the same original, retains complaint provenance, and invokes the shared ingestion module. Reuse compatible prior extraction. Declining keeps it complaint-scoped and unindexed. Do not silently reuse a declined chat-only file as a product-wide source.

When the business requests an original document, find appropriate product-document candidates through scope/type metadata and description. Show the selected original with preview and Share this / Choose another. Equally plausible documents require user selection. Record consent for the particular file/version and recipient exchange; do not treat old consent as unrestricted future permission.

Assume for integration design that a business requesting a document can receive it. The adapter still needs a concrete agreed file-transfer representation, supported types/limits and receipt acknowledgement. Internal inspection is distinct from external transfer. Do not expose permanent public bucket URLs or credentials.

## 8. Question and answer path

1. Receive and persist the actual business message with protocol identity.
2. Reconstruct complaint-local context: active product, issue, recent relevant turns, pending decisions and facts. Load only the authorized scope.
3. Resolver emits typed standalone question, requested information/entities, and clarification status. Original and resolved questions are internal persisted artifacts; only actual messages appear in customer chat.
4. If interpretation is unclear, ask an appropriate clarification and pause that turn. Do not manufacture constraints or answers during rewriting.
5. Retrieve product JSON and current complaint facts, respecting complaint-local overrides and newer confirmed corrections.
6. If insufficient, search authorized indexed Product Documents. Generate a query embedding from the resolved information need at search time; document embeddings were generated during ingestion. Query embedding is not an extra generative answer call. Preserve keyword/exact-identifier matching where necessary.
7. Inspect a chat-only attachment directly when supplied for the question; do not index it unless subsequently saved to Product Documents.
8. If evidence remains missing, conflicting or unavailable, ask the user and save the pending question. Distinguish no result from a retrieval-service failure.
9. Answer using the actual evidence. Persist evidence consumed, not merely all retrieval candidates. Preserve exact values and uncertainty; no exact backend-built sentence template or runtime paraphrase-to-answer mapping.
10. Validate output shape, cited source accessibility/version, exact critical facts and allowed actions. Structured checks do not prove all natural-language claims correct; evaluate model grounding separately.
11. Automatically send supported routine factual answers. Record send/result state and delivery identities. No review-and-send requirement on every answer.

Retrieval from indexed passages aims to avoid a separate whole-document extraction call per question. It does not establish a measured one-call or cost saving: direct multimodal inspection and answering can also share a call. Resolver and answer calls remain distinct where retrieval separates them.

## 9. Human handoff and correction

Handoff occurs for missing/conflicting facts, ambiguity, explicit sharing, booking confirmation or voluntary Pause and correct. Customer input answers the pending business question and updates reusable knowledge only in the appropriate scope.

Pause and correct stops dispatching subsequent turns. Determine the outcome of an in-flight request before continuing; a sent message cannot reliably be recalled. Invalidate unsent old-fact drafts via version checks. If an old answer was sent, record and communicate an explicit correction when supported by the business protocol. Preserve both messages. Do not promise every user correction will arrive before automatic sending.

User-facing chat shows actual messages, pending work and contextual actions; internal rewrites, prompts and retrieved bundles stay out of the normal UI. Thumbs feedback and feedback-driven retry are later development.

## 10. Memory, operation state and recovery

Full committed conversation history persists per complaint and reloads on reopen. Working model context is a bounded selection of that history plus explicit pending/fact state; a separate memory service or summary agent is not required. General semantic search across old chats is deferred. Historical references can use direct complaint-record retrieval, while reusable facts are promoted into product knowledge.

Use explicit workflow states for processing, awaiting user fact/clarification, sharing consent, appointment confirmation, paused, recoverable error and completed/closed outcomes. Precise public enum mapping is additive implementation work; preserve existing case lifecycle behavior and versioned leases. Avoid treating a progress label as the complete operation state.

Browser closure stops dispatching new steps; it does not prove failure of an already-dispatched request. On reopen, load saved events/state first. Show a completed result, wait for an active operation, or offer Retry saved step after determining safe recovery. Do not introduce a background queue for autonomous conversations in this scope.

No new automatic extraction, embedding, retrieval or model repair retry is introduced. User-initiated recovery permits the initial attempt plus at most two retries per operation, with durable counts. Reopening does not reset the limit. Exhaustion stops the operation and provides an appropriate restart/correct-input path, retaining complaint history.

Booking retries retain stable operation identities and existing business replay protection. Unknown external outcomes require reconciliation; never blindly restart a booking or mark it failed merely because the browser disconnected. An unrecoverable unknown result is surfaced honestly. Automatic conditional retries remain future work.

Request-bound ingestion/turn work must have explicit time/input/output budgets and save phase outcomes. The implementation plan must choose supported limits before coding. If a document exceeds processing limits, stop and ask for appropriate input; do not silently add a worker or infinite continuation loop.

## 11. Appointment and closure behavior

Retain the intake preference and explicit confirmation behavior. An offer must belong to this complaint, match the displayed user selection and current business availability, and pass case/version/duplicate checks before booking. Show confirmed only after validated business confirmation. Generated text cannot authorize booking, charges or unrelated commitments.

No automatic schedule negotiation or service-center capability is added here. An unavailable preference requires user action rather than invented availability. Preserve existing product-deletion tombstones, complaint closure and stale-operation rejection; no external cancellation is implied. Resolution remains user-confirmed.

## 12. End-to-end paths

### Product document

Upload → private original/metadata → classification and extraction → validated product facts and description → source-linked passages → embeddings and searchable version.

### Automated complaint

Intake → save case/context → A2A business message → persist → resolve question → JSON/complaint facts → scoped retrieval if needed → supported automatic answer → persist outcome → next question → actual appointment offer → user confirmation → backend booking gate → A2A confirmation → saved visit.

### Missing information

Question → evidence missing → user fact or chat attachment → inspect if needed → validate/update appropriate knowledge → supported answer → resume same complaint. Offer saving a reusable chat document to Product Documents; only acceptance invokes indexing.

### Reopen

Load saved complaint/events → inspect pending operation outcome → display completed work or bounded manual resume → continue from saved turn. Preserve the same external operation identity during recovery.

## 13. Acceptance checks

- Four purchase-date phrasings: What date did you purchase this appliance?; When was this product bought?; Could you provide its purchase date?; after a product discussion, And when did you buy it?
- Change dates/products/order; include held-out wording. No requested_fields hint, answer_template, runtime phrase mapping or expected answer enters resolver/answer input. A separate evaluator may retain expected results.
- Missing fact requests user input; supplied serial number is reused in a later complaint for that product.
- Follow-up resolution uses the current complaint; uncertain meaning asks clarification rather than inventing it.
- Invoice image and equivalent PDF produce traceable facts; ordinary/random photos do not produce fabricated invoice knowledge.
- Product Documents additions invoke the same ingestion module; chat-only uploads do not create embeddings. Accepted promotion does; duplicate processing is bounded and version-aware.
- JSON-missing invoice detail retrieves the correct source passage; exact identifiers survive retrieval and answering.
- Wrong-product/inaccessible/incomplete/stale-version evidence is excluded; descriptions cannot justify unsupported facts.
- Conflicting or uncertain extraction requests review. Corrections affect subsequent answers and retain historical evidence versions.
- Complaint phone change leaves Profile unchanged. Appointment preferences/current symptoms do not become permanent product facts.
- Original-file sharing requires file/version consent; product association requires its separate save choice. Business receipt is tracked.
- Routine answers auto-send; no per-answer review. Pause prevents subsequent dispatch, invalidates stale drafts, and reconciles in-flight sends.
- Reopen reconstructs messages and pending state. Completed work is not blindly repeated; two retries cannot be bypassed by refresh.
- Extraction/index/retrieval outage is distinguishable from absent facts; files/facts already saved remain available; no automatic retry loop.
- Booking requires actual offer/user confirmation; stale or duplicate actions fail safely; unknown outcomes do not trigger duplicate booking.
- Existing login, product CRUD, uploads, complaint history, deletion/closure and mobile flows remain verified by relevant regression checks.

These are required future checks, not tests executed during drafting. Real-model evaluation must exercise understanding/retrieval; mocked flow tests alone cannot establish those capabilities.

## 14. Implementation planning boundary

After written-spec approval, produce a scoped implementation plan with exact data contracts/migrations, existing-file changes, vector backend/embedding-model compatibility and cost checks, model/file limits, A2A message/file acknowledgements, and phased verification. Keep existing Google/Firestore/private Storage/ADK/A2A architecture unless a concrete incompatibility requires a separately reviewed change.

Start with one vertical slice: indexed product invoice + follow-up resolver + supported purchase question + human missing-fact handoff. Then add chat-only extraction/promotion/sharing, correction/resume and booking integration. Do not defer the final acceptance checks merely because the first slice passes.

User preference remains step-by-step implementation instructions. Application edits, deployment, cloud resource changes, commits/pushes and subagents require applicable explicit authorization; this spec does not grant it. The previous shared PDF is a frozen earlier discussion artifact, not this consolidated design.
