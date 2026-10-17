# Custra mobile UI/UX design

Date: 17 October 2026

Status: user explicitly authorized implementation on 17 October 2026. Implemented
locally on `feat/mobile-pastel-ui`; see `docs/MOBILE_UI_IMPLEMENTATION.md` for
delivered behavior, verification and remaining live/hosted acceptance. Earlier
approval-boundary notes below record the design process; the latest explicit
implementation authorization supersedes them.

## Purpose and design authority

Help a user register a complaint with minimal effort by reusing saved product,
contact and address details. Returning users should select a product, describe
the problem once and submit. First-time users must have a clear path to add the
necessary details without losing their complaint draft.

Use Impeccable for UI/UX decisions, Superpowers for the development workflow and
Vercel React Best Practices for React implementation. This is an Operate-mode
application: clear tasks, familiar controls and visible progress take priority.

The user's supplied screenshots establish structural references. The actual
Custra logo establishes brand identity: navy wordmark with blue, cyan and
turquoise symbol. User subsequently approved a minimal pastel theme and explicitly
allowed recoloring the logo while preserving its structure. Use warm ivory/white
surfaces, muted sage actions with dark labels, mist-blue accents and dark slate
text. Preserve the folded-C geometry and lettering; recolor with restrained
sage/teal tones. Use a compact logo in the
app header and the full identity on login. The original asset remains outside
the repository; integrating or preparing asset variants is later implementation
work.

Visual references: `docs/design/previews/custra-mobile-concept-v2-pastel.png`
records the approved theme. `custra-mobile-concept-v3-minimal.png` in the same
directory records the minimal structure the user approved: compact Home rows,
search/product grid and a streamlined agent conversation. User requested one
addition: a single Continue where you left off card below the Products grid.
`custra-mobile-concept-v4-resume.png` shows that revision. The card links to the
most recently active complaint and shows product, issue, reference and date;
omit it when no resumable complaint exists. No extra instructional banner is
needed. The new rendered board is a preview; application edits remain unauthorized.

## Navigation and home

- Bottom navigation: Home, Products, Complaints. Profile is at the top right;
  no location dropdown. Profile contains personal details, addresses and logout.
  Complaint and technician-visit history belongs in Complaints, optionally linked
  from Profile.
- Keep Register a complaint visible near the top of Home without scrolling.
- Show up to two active complaint previews, prioritizing cases needing action,
  then in-progress cases. Provide View all for the full complaint list.
- Complaint previews show product, issue, readable status, registration date,
  reference when issued and one contextual next action. Do not expose raw enum
  labels to the user.
- Label the Home visit section Next technician visit and show the next confirmed
  visit when one exists. Adapt content naturally to empty
  and populated states instead of reserving a fixed half-screen height.
- Call technician is available only with a valid assigned contact. Current
  simulator fixtures contain no technician phone; no placeholder phone action
  should imply that a real person is assigned or contacted.

## Products and registration

Product-form refinement approved after discussion: Model is optional and follows
Type/Brand. Use a searchable filtered suggestion list, Other/manual entry and
I don't know. Sourced suggestions are curated India-market examples, not a full
manufacturer catalog; every entry keeps its official URL and checked date.
Save model independently of nickname and use the actual model in agent facts.
Changing type/brand clears an incompatible model selection.

Keep the base form compact: paired Type/Brand, Model and optional Nickname.
Purchase & warranty is collapsed unless editing recorded data; documents use
an Add document action instead of a persistent native file control. Warranty
amount and Months/Years unit share a row, normalized to months when saved.
Use a compact page title/back row and an accessible Save area; allow scrolling
for expanded optional details, small viewports, keyboard and enlarged text.

Add document opens Take photo / Choose photo / Upload file. Use native camera
capture as a request with file fallback, not a guaranteed browser capability.
Show a local photo preview or filename with Replace/Remove before saving.
Preserve server file validation and existing supported types/size; this is not
OCR, document scanning, multi-page PDF generation or a custom in-app camera.

- Search by nickname, brand or product category.
- Four compact tiles per row on normal phone widths, explicitly confirmed by
  the user. Adapt to fewer columns on narrower screens or enlarged text rather
  than clipping labels or reducing touch areas.
- The first tile is always Add product. Use consistent category icons with
  short, wrapping labels and a visible active-complaint indicator when relevant.
- Add an optional Product nickname field. If omitted or blank after trimming,
  the displayed nickname is `<Brand> <Product type>`, for example Samsung TV.
  A supplied nickname is the primary label; retain brand/type in product details.
- Product identity fields remain required. Purchase date, warranty information
  and documents are optional; missing optional data must not prevent basic use.
- Collect warranty duration with an explicit unit alongside purchase date.
  Derive expiry and show Under warranty / Out of warranty. Show Warranty details
  missing when the inputs are insufficient. A known default may be suggested
  only when supported by product information; it remains editable. Do not invent
  a default based only on category or brand. These are recorded details, not
  manufacturer-verified entitlement. Exact expiry/date-boundary rules must be
  specified consistently before implementation.

## Product detail

Order: product identity, complaint action, active complaint, saved details,
documents, past complaints. Use the supplied product-detail reference as
structural inspiration without unsupported contract or verified-coverage claims.

When a complaint is open, use one Current complaint section showing its issue,
status and reference, with a single contextual action: View conversation while
processing, Choose appointment when selection is needed, or View appointment
after booking. Do not add a separate View ongoing complaint button above that
section: both would lead to the same complaint and duplicate the entry point.
Retain Report another issue as a secondary action. When no complaint is open,
show Register a complaint as the primary action. Do not prevent reporting a
distinct issue.

## Complaint intake

- Preselect the product when starting from its detail page. Otherwise provide
  product selection and a clear route to add one.
- After What's wrong?, use four slim editable/selectable rows: Service address,
  Phone number, Preferred date and Preferred time. Show a compact saved-address
  summary and phone only; do not repeat full name/email on this form. Retain
  existing profile/agent facts unless separately changed.
- Prefer one primary What is wrong? description field, with a concrete example.
  Optional category-specific issue suggestions must allow Other issue and free
  description. Do not require the same explanation twice.
- Keep missing contact/address completion in the journey and preserve draft
  values. Do not send users away to settings and discard their work.
- Register complaint submits once, shows in-progress feedback and opens the case
  conversation. Handle validation and recoverable failures without clearing input.

Single-field intake changes the current summary/description contract. Its
mapping and validation need an implementation decision; this specification does
not claim that the existing API already accepts one field.

## Agent conversation and recovery

- Chat presentation: Business support on the left, Custra on the right, with
  explicit identities and a clear simulated-business label.
- Show product/issue context and readable current progress above the transcript.
  Explain once that Custra answers using saved details and typing is unnecessary.
- Show activity during actual processing. Avoid artificial delays, repeated
  typing playback after refresh or pulling readers away from older messages.
- On completion, emphasize the result and next action. On return visits, lead
  with current status/appointment and retain access to the conversation.
- Show recoverable errors with an explicit retry action. Do not imply completion
  before persisted success or duplicate already committed messages.
- Preserve the current request-bound behavior: leaving the case page stops
  dispatching new steps; an in-flight step can finish. Do not promise background
  completion unless separately designed and implemented.

## Appointment selection

Updated user direction: collect preferred date/time within the initial complaint
form, replacing the earlier end-only full-height picker. Use a compact calendar
popover from the date row and a time dialog with a three-column grid, inspired
by the user's supplied references and styled in the approved pastel theme.
Keep Change date visible in the time dialog. Cancel preserves earlier saved
values; Save preference updates the form without booking anything. Display the
timezone and a short preferred-slot/subject-to-confirmation explanation.

Disable past dates, dates outside the offered schedule and unavailable slots.
Differentiate available, selected and unavailable states with labels as well as
color. Changing the date clears an incompatible time selection without losing
the complaint. A preference is not a reservation or confirmed appointment.
After agent registration, recheck availability and let the user confirm the
preferred slot directly, avoiding repeat date/time selection. If unavailable,
retain context, explain the conflict and offer alternative dates/times. Booking
still requires valid availability and explicit confirmation. This confirmation
behavior is the recommended consequence of the new preference flow, not a claim
that the existing backend supports it.

Define a consistent simulated schedule containing available and unavailable
slots; do not disable arbitrary slots for decoration. Current code returns six
available slots across three days, so pre-registration schedule retrieval,
preference fields/persistence, availability data and calendar presentation
require implementation work. Preserve dismiss/reopen behavior and idempotent
booking/recovery. A booking does not close the complaint; resolution requires
explicit user confirmation.

Complaints shows active and past complaints, with their statuses and any linked
technician-visit details. Preserve access to upcoming/past visit information
through the associated complaint; a complaint need not have a booked visit.

Terminology update: replace the earlier Appointments bottom-tab label with
Complaints and Next appointment with Next technician visit. Earlier generated
previews retain superseded text until regenerated; this specification controls
the current labels. This is a navigation/home-copy change, not a rename of
backend appointment concepts or an assertion that any technician is assigned.

## Usability and responsive behavior

Use one readable sans-serif family, consistent icons and controls, short
purposeful transitions and reduced-motion support. Aim for 44–48 px important
touch controls, visible keyboard focus and readable disabled states. Provide
loading, empty, error and success states across the journeys.

Keep bottom navigation and fixed actions clear of device safe areas and the
keyboard. Desktop layouts may use more columns and structured panels rather
than stretching phone forms across the full viewport.

## Scope and next step

The user approved `docs/design/previews/custra-product-and-complaints-v1.png`:
Add/Edit Product layout with optional nickname, warranty and documents, plus
Active/Past Complaints views with contextual actions and visit details. The
matching sidecar records approval. This is design approval, not application-edit
authorization. The user also approved
`docs/design/previews/custra-profile-addresses-v1.png`: editable name/phone/email,
Saved addresses and logout; address list with default/Edit/Set as default; shared
add/edit address form with label, line1/optional line2, city/state, postal code,
country and default selection. Preserve entered values on errors/cancel and
complaint drafts when this form is opened from complaint intake. No geolocation,
address deletion or account deletion is introduced. Use the approved muted theme
tokens for links and borders rather than the generated board's brighter blue.

Agreed design additions include nickname/default naming, recorded warranty
inputs, mobile navigation/overview, compact product grid, simplified intake,
agent chat and date/time availability presentation. They require deliberate
data/API/UI work and verification, not styling alone. Maintain clearly simulated
business registration and booking. No real brand integration, contract
verification, technician assignment or background agent work is implied.

Next: translate the agreed design into an implementation plan covering shared
visual tokens/navigation, product/account flows, complaint preference contracts,
chat and visit confirmation, plus focused regression verification. Reuse existing
case persistence/idempotency and dedicated Custra credential isolation. Provide
step-by-step implementation instructions for the user. Application edits continue to require the user's explicit
instruction. No deployment, commit or push is part of this design finalization.


## Latest refinements — compactness, visit confirmation and product deletion

User clarified that preferred date/time is selected at complaint registration,
assuming it remains available for this iteration. During A2A, keep explicit
Confirm visit with saved time; remove Choose later and all date/time selection.
Close via ×, Escape or outside tap; inside taps do not dismiss. No booking is
created by dismissal. For old cases without a saved preference, show the first
business-offered time for explicit confirmation (no silent booking). Unavailable
saved preferences remain unbookable; replacement negotiation is deferred.

Apply compact header/section/form/list/chat spacing across existing pages,
retaining readability, focus visibility and usable controls. Preserve theme.

Delete product from details through a confirmation explaining active complaint
closure and retained history. Persist a product tombstone and close linked
active complaints atomically, with closureReason=product_deleted and incremented
versions to reject stale worker results. Previously resolved cases stay intact.
Never claim resolution or external business cancellation. Documents/history are
retained; this is removal from the active vault, not a personal-data purge.

The prior inline Model suggestion proposal remains unapproved and outside this
implementation scope.


## Shared uploads and closed-case presentation — latest user request

Replace the oversized browser-blue resolution tick with a 20px native checkbox
using the theme accent and a comfortably sized label. Reuse the existing Add
document action sheet (Take photo / Choose photo / Upload file) in every upload
context; no public native file-picker controls remain. Keep product creation
retry-safe by selecting its attachment before saving/uploading to a persisted ID.
Allow the same JPEG/PNG/PDF <=5 MB scope on complaint uploads.

Closed cases have no case-photo/document section or upload controls. Mute history
bubbles without lowering text opacity or blocking selection/reading. Show a
small readable end-of-chat notice and Start a new complaint link. No new
resolution/visit controls appear. Server rejects new closed-case uploads with
409 case_closed; saved documents remain stored and authenticated read access is
preserved. Hiding the attachment section is not document deletion.
