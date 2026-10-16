# Custra V1 system design

Updated: 16 October 2026. Status: approved by the user on 16 October 2026; implementation not authorized.
No application implementation, deployment, commit or push authorized by this document.
Scope authority: docs/MVP_SCOPE_PROPOSAL.md and latest user decisions recorded in
docs/SESSION_STATE.md. Development ends 18 October 2026 at 16:00 IST.

## 1. Intent and scope boundary

Give users a free product Vault and demonstrate an agent registering a complaint
on their behalf. The user enters basic details; the simulated business asks questions
the Consumer Agent answers from those details. The final registration interaction
is date/time selection in a dialog. Later closure always requires user confirmation.

Confirmed: fixed demo login; shared profile with name/phone/email; saved addresses
with a seeded dummy address; add-address popup saved to Account settings; manual
product entry; optional document storage/viewing; mock service-center cards; product
and global complaint views; automated conversation; no extraction or warranty dispute.
Google sign-in, multi-user authorization and usage quotas are deferred. General
missing-information collection is optional after core acceptance, otherwise future.

This document proposes HOW to deliver that scope. User decision on 16 October:
remove upfront time preference entirely from intake and case data. Date/time is
selected only in the final appointment dialog, after the agent questions finish.

Real: Gemini-generated Consumer Agent answers, A2A transport, saved data, UI actions.
Simulated: business questions/policy, service-center information, complaint reference,
available appointments, booking and repair. Label the simulation throughout.

## 2. Current repository evidence

Inspected frontend/package.json, frontend/src/App.jsx, backend/app/main.py,
backend/requirements.txt, frontend/vite.config.js, firebase.json and README.md.
React/Vite calls a FastAPI validation/echo endpoint. No login, persistent storage,
real uploads or agent runtime currently exists. Firebase rewrites contain placeholders.
backend/app/{agents,api,models,services}, manufacturer-agent and infrastructure contain
placeholders only. Preserve unrelated untracked work. README's earlier extraction/
negotiation description is historical and must be reconciled when implementation
documentation is updated. No application tests were run for this design-only task.

## 3. Architecture choice

Recommendation: use the Custra API plus a separate private Business Agent service,
connected through real A2A. This is the proposed design, not a request for the user
to choose among deployment alternatives. The user approved the overall design on 16 October 2026.

Rationale: keeping the simulator inside the Custra process would reduce deployment
work but remove the independent service boundary being demonstrated. A managed
background-agent platform would add integration work beyond the V1 deadline.
Neither alternative is part of this proposed V1 architecture.

Deploy React/Vite static assets on Firebase Hosting. Route /api/** to a FastAPI
Custra service on Cloud Run. That service owns login, application workflows,
Firestore access, private document access and the ADK Consumer Agent. Invoke Gemini
through Vertex AI with the Cloud Run service identity. Use an available GA Flash-class
model that passes the scenario evaluation, selected via configuration; verify model
availability in the selected project/location before pinning the model ID.

Deploy a second private Cloud Run service from manufacturer-agent. It exposes the
official Python A2A SDK interface and a deterministic business scenario. It does not
need a second LLM to ask the agreed basic questions. This is explicitly a scripted
Business Agent simulator; the Consumer Agent is the Gemini/ADK component.

Use Firestore Native mode for structured records and a private Cloud Storage bucket
for PDF/image objects. No Cloud SQL, vector database, Redis, document extraction,
WebSocket server, background queue or managed Agent Engine in V1.

| Component | Owns | Must not own |
| --- | --- | --- |
| React UI | Forms, dialog selection, progress presentation, requests to API | Model secrets, authoritative booking/status changes |
| FastAPI application services | State transitions, validation, snapshots, login, duplicate protection | Fabricated business success from generated text |
| ADK Consumer Agent | Interpret business questions and compose factual responses | Arbitrary storage writes, appointment choice, complaint closure |
| A2A gateway | Structured exchange and response validation | Trust arbitrary model-supplied URLs |
| Business simulator | Fixed question sequence, demo reference and slot issuance, idempotent mock booking | Real business contact or real technician assignment |
| Firestore / Storage | Durable facts/events and file objects | Browser-direct unrestricted access |

## 4. Execution model and persistence

Use short request-bound steps, not an unbounded agent loop or detached FastAPI task.
Firebase Hosting has a documented 60-second request timeout. Target a 40-second
server deadline for each advance operation, including A2A and Gemini work; return a
retryable error before the hosting deadline. SDK calls must have explicit timeouts.

1. Submit the form with a client-generated idempotency key. Backend validates saved
   profile/product/address, snapshots relevant facts and creates one case.
2. Conversation page loads the saved state/events and automatically invokes advance.
3. Start step obtains the first business question. Each following advance answers
   one question with ADK/Gemini, validates the answer, exchanges it over A2A, and
   commits the response/events and next phase. At most four scenario questions.
4. Frontend appends committed messages and calls the next step while phase permits.
   On a conflicting in-flight request, fetch state and retry after the indicated delay.
   GET requests only read; they never start model work.
5. When registration and slots arrive, stop automatic advance and show the scheduling
   dialog. User selects a dated slot and confirms; backend books via the simulator.
6. Return booking confirmation; no further questions or forms in registration flow.
   Later an explicit user resolution-confirmation action closes the case.

Before external work, a Firestore transaction acquires an expiring operation lease
and assigns a stable step/operation ID. Do not call external services inside a
transaction callback, which can rerun. Commit a step only if its lease/version still
matches. Append events with stable IDs so retries do not duplicate visible messages.
An expired lease permits retry; a stale worker cannot overwrite a later result.

Business simulator persists operation results keyed by operation ID. If an A2A
response is lost after booking, replay returns the same appointment. An interrupted
LLM invocation can still incur duplicate compute on retry; do not claim exactly-once
model billing. Cache validated generated answers before business submission when possible.

A closed tab stops dispatching subsequent steps; an in-flight request may finish or
time out. Reopening reads Firestore and continues from the saved step. V1 therefore
does not promise autonomous background progress while the application is closed.
This refresh/recovery behavior is separate from deferred missing-information chat.

Create a short-lived ADK execution context for each answer from the saved case
snapshot, current question and relevant persisted transcript. Firestore is the
source of truth; no dependence on a process-local long-lived ADK session. This is
application-level context reconstruction, not a claimed built-in Firestore ADK
SessionService. Keep the entire small demo conversation available; no summarization
or long-term memory service required.

## 5. Agent exchange contract

Use a real A2A SDK client/server pair and Agent Card; pin compatible SDK/ADK versions
after an early integration check. Do not label ordinary custom REST messages as A2A.
The app-facing API is REST; only the server-to-business boundary uses A2A.

Represent each bounded exchange as a completed A2A task/message response and link
exchanges through the same context ID. Do not continue a protocol task after it has
reached a terminal state. Store returned protocol IDs for diagnosis; app complaint
status remains independent of the A2A task status.

Structured data parts carry schemaVersion, caseId, operationId, scenarioId,
businessStage and action. Actions: start, answer, listSlots, book. Responses contain
questionCode/requestedFields, displayText, nextStage, and where appropriate
complaintReference, slots or appointment. Validate all responses before state changes.

Suggested scenario questions: identify product; describe issue; provide contact
details; confirm service address. Ask only facts required at form/profile validation.
Question order and natural language are presentation; requestedFields is authoritative.
Consumer Agent returns a response plus selected field references. Backend resolves
structured values from the saved snapshot, checks correspondence, and rejects an
answer containing unsupported details. No extra clarifying loop is allowed in core.
Malformed/unsupported output becomes retryable error, never invented success.

The backend A2A gateway controls the fixed destination and allowed actions. Booking
and closure are application actions, not discretionary model tools. Documents and
photos are not sent to the model in this version. User-entered descriptions are data,
not instructions granting access to other tools or records.

## 6. Records and data ownership

Use one demo namespace and one shared logical identity. This does not implement or
claim multi-user isolation. Include stable IDs for migration without building future
account management now. Store timestamps in UTC and render appointment timezone
explicitly; proposal for demo slots is Asia/Kolkata, not a decision on geographic market.

| Record | Main fields |
| --- | --- |
| Profile | name, phone, email, defaultAddressId, updatedAt |
| Address | id, label, address lines, city, region, postal code, country, isDemo |
| Product | id, categoryId, brandId, displayName/model, optional purchaseDate/warrantyExpiry, createdAt |
| Document | id, productId or caseId, objectKey, originalName, mediaType, size, ready/pending status |
| Complaint | id, productId, addressId, issueSummary, description, immutable facts snapshot, status, businessStage, reference, currentVersion |
| Conversation event | caseId, sequence, eventId, role, displayText, eventType, createdAt, simulation marker |
| Execution operation | operationId, caseId, phase, lease token/expiry, saved result, failure details |
| Appointment | caseId, slotId, start/end UTC, timezone, bookingReference, simulation marker |
| Demo session | hashed opaque token, expiry, revoked flag |
| Simulator operation | operationId, scenario state/result, mock reference/slot booking |

Keep messages in a case subcollection instead of an indefinitely growing array.
Static category/brand mappings and labeled mock service-center fixtures ship with the
backend; retain agreed 10–15 category/brand counts. Do not use the LLM for contact data.
No fake center phone number should launch an actual call. Region/brand fixture content
remains a content choice, independent of the architecture.

Profile and address edits affect future cases, not an active case's snapshot.
Save address through API before selecting it for the complaint; cancel popup discards
only unsaved popup edits. After saving, select the new address and keep the issue form.
Account settings reads the same address collection, not a separate duplicate list.

Documents: accept PDF/JPEG/PNG up to proposed 5 MB each through the backend; generate
object keys, check type/size, reject HTML/SVG, and mark metadata ready only after upload.
Clean up failed uploads. Stream authorized downloads from the private bucket; no public
object URLs. Optional case photo uses the same storage path, with no analysis.

## 7. Case state and final scheduling

States: PROCESSING → AWAITING_APPOINTMENT → BOOKED → CLOSED.
ERROR retains the last completed phase so an explicit Retry can resume safely.
Technical validation failures before creation return field errors rather than a case.

- PROCESSING: bounded question/answer steps. Business registration reference may
  appear before booking; do not show Resolved or Closed.
- AWAITING_APPOINTMENT: dialog presents available dates/times. Closing the dialog
  leaves the case here and shows Choose appointment on the case screen.
- BOOKED: backend has a confirmed simulated booking for the user-selected slot.
  Repeated confirm requests replay the same result. Reject a stale slot or a second
  different booking for the same case; keep the user at selection if availability changes.
- CLOSED: only the explicit user confirmation endpoint can enter this state.
  Do not auto-close on elapsed appointment time or an agent message.

Slots are generated for future dates at runtime so fixtures do not expire before
the presentation. The final dialog shows available dated slots without an upfront
preference filter; it is the only place users choose date/time. No rescheduling flow
in core V1.

## 8. API surface

All endpoints except login/health require the demo session, including direct Cloud
Run requests. All mutations validate schema and state. Errors use a consistent code,
message, retryable flag and optional field errors; no stack traces to the UI.

| Endpoint family | Responsibility |
| --- | --- |
| POST /api/auth/login; GET /api/auth/session; POST /api/auth/logout | Create/check/revoke demo session |
| GET/PATCH /api/profile | Basic profile |
| GET/POST /api/addresses; PATCH /api/addresses/{id} | Shared saved addresses |
| GET /api/catalog; GET /api/service-centers | Static selectable data and demo listings |
| GET/POST /api/products; GET/PATCH /api/products/{id} | Product records |
| POST /api/products/{id}/documents; GET /api/documents/{id}/content | Upload and authorized viewing |
| POST /api/complaints; GET /api/complaints | Idempotent creation; global or product-filtered listing |
| GET /api/complaints/{id}; GET /api/complaints/{id}/events?after=sequence | Snapshot and incremental history |
| POST /api/complaints/{id}/advance | At most one bounded conversation step |
| GET /api/complaints/{id}/slots | Saved/current simulated options, no model call |
| POST /api/complaints/{id}/appointment | Validate selected slot and idempotently book |
| POST /api/complaints/{id}/confirm-resolution | Record explicit confirmation and close |

Use idempotency keys on creation and appointment actions; reject reuse with a different
payload. Advance uses case version/step ID to prevent two tabs progressing twice.

## 9. Frontend boundaries

Keep React/Vite; no Next.js migration. Proposed lightweight router supports login,
account settings, Vault, product detail, new complaint, global complaints and case detail.
Share AddressDialog, AppointmentDialog, ProductForm and ConversationTimeline components.
Use one API client for session/errors; keep fetched state separate from temporary form
state. Fetch independent profile/product/address data concurrently and reuse it.
One advancement loop per mounted case; stop on error, selection, completion or unmount.
Do not trigger mutations from generic GET hooks or repeatedly from render effects.

Only committed agent messages appear in the timeline. Animate new messages, not old
history on refresh. Pending indicators correspond to an actual in-flight step and
stop on failure. No composer, fake continuous typing or presentation of hidden model
reasoning. Keep progress descriptions short. Dialogs support focus management,
keyboard access, mobile layout and reduced motion. Avoid adding an animation library.

## 10. Login, deployment and cost boundaries

Fixed username/password configured on the server; store password hash and secrets
outside source control, preferably Secret Manager. Verify password server-side.
Issue an opaque random session token; store its hash with expiry in Firestore.
Set Secure, HttpOnly, SameSite=Lax cookie named __session, which Firebase Hosting
forwards. Proposed lifetime: eight hours. Enforce expiry in application code even if
database cleanup is delayed. Logout revokes the record and clears the cookie.
Check Origin on state-changing browser requests. Set authenticated API/document
responses to Cache-Control: private, no-store. Keep local HTTP cookie settings
explicitly development-only.

Firebase Hosting serves static assets and forwards /api requests to the public Custra
Cloud Run service. Application middleware authenticates every protected route even
when the run.app URL is accessed directly. Service account credentials call Vertex AI,
Firestore and Storage; no browser database access is necessary. Business service is
IAM-private: only Custra service identity gets Cloud Run invoker, and the A2A HTTP
client attaches a Google-signed identity token for the correct audience. Agent Card
fetches also use that authenticated client. Use separate simulator collections and
service identity; no profile or document access is needed by the business service.

Use one project and compatible locations where possible; check Firebase Hosting's
supported rewrite region and the selected model's availability before deployment.
Deploy through existing Hosting/Cloud Run structure; no extra cloud platforms.

Recommended starting operational settings: minimum instances 0, maximum 1 per
Cloud Run service, four business questions per case, at most one model call per
answer step, bounded token output, no automatic repeated retries. Provide a server
configuration switch disabling new agent advances. These settings need validation
against actual demo latency; they are not per-user or global usage quotas.
Per-user/global quotas remain deferred exactly as requested. Alerts and limited
scaling do not guarantee a monetary cap. A shared password permits repeated runs
by anyone holding it. Use fictional data and provide credentials privately to reviewers.

## 11. Verification and delivery order

Proposed sequence, not an implementation plan or authorization:

1. Verify compatible ADK/A2A versions, chosen Gemini model access, and one authenticated
   remote business exchange early. This is the highest integration risk.
2. Demo login plus persistent profile/address/product foundation and deployed routing.
3. Minimal documents/mock centers, complaint snapshots and bounded question/answer flow.
4. Scheduling dialog, idempotent booking, explicit closure and automated UI states.
5. Hosted verification, rehearsal and freeze. General missing-input collection only
   if all core checks pass with time remaining; otherwise future scope.

Required checks: unauthenticated endpoints cannot invoke model or read files;
session works through Hosting; profile/address survives refresh; snapshot is stable
after profile edits; duplicate submit/advance/booking cannot duplicate records;
model answers use supplied facts; no serial number request; failure stops indicators;
refresh recovers the step; server restart does not lose cases; dialog cancellation
does not book; selected slot is confirmed; only user action closes; mock labels visible;
mobile dialogs and keyboard operation work. Test A2A replay after a lost response.

Target: core deployed by 17 October evening. 18 October morning to 14:00 verification,
14:00–16:00 blocker buffer, then code freeze and submission documents. Scope is
ambitious relative to the current shell; make A2A integration the first technical
check and do not spend the early schedule polishing Vault visuals.

## 12. Review decisions and limitations

Architecture approved on 16 October 2026, not coding: two Cloud Run services; deterministic
Business Agent with real A2A; request-bound auto-advancing steps with Firestore context;
server session cookie; Firestore/private Storage. Upfront time preference is removed
by user decision; scheduling occurs only in the final dialog.
Specific project/region, model ID, SDK pins and credential delivery are deployment
bindings to verify before implementation, not claims already validated here.
No submission rules were supplied, so compliance with competition technology or
hosting requirements has not been independently verified.

## Sources checked for platform constraints

- ADK A2A integration (marked experimental in current docs): https://adk.dev/a2a/
- A2A task lifecycle: https://a2a-protocol.org/latest/topics/life-of-a-task/
- Firebase Hosting Cloud Run timeout: https://firebase.google.com/docs/hosting/cloud-run
- Firebase cache/cookie behavior: https://firebase.google.com/docs/hosting/manage-cache
- Cloud Run service authentication: https://docs.cloud.google.com/run/docs/authenticating/service-to-service

Platform facts above come from official documentation; component choices, API
shapes, limits and execution model are Custra design recommendations. Model/SDK
compatibility is to be tested during the authorized implementation phase.
