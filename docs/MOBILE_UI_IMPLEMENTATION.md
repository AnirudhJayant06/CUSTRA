# Mobile UI implementation — 17 October 2026

Implemented locally after the user's explicit authorization. Integration branch:
`develop`. Hosting and deployment remain separate from this UI checkpoint.

## Delivered

Pastel brand/theme, original logo rendering, Home/Products/Complaints navigation,
four-column searchable product grid with resume card, product detail with one
complaint entry point, Add/Edit Product with optional nickname/warranty/documents,
Profile/default addresses, Active/Past complaint lists, slim complaint intake,
preferred-slot popups, agent chat, explicit visit confirmation and closure.

## Data/API changes

- Product `nickname` is optional. Blank becomes `<Brand> <Product type>` in
  `displayName`. Legacy displayName and explicit warrantyExpiry remain supported.
- Optional `warrantyMonths` is an integer 1–120. With purchaseDate, expiry adds
  calendar months, clamping to month-end. Coverage is based on saved entries,
  valid through the expiry date in Asia/Kolkata; it is not manufacturer verified.
- Complaint `issueSummary` may be omitted; the server derives it from the first
  120 characters of description. Existing clients supplying both still work.
- Optional `preferredDate` and `preferredSlotId` must be supplied together and
  match available demo times. They are immutable saved preferences, not bookings.
  Legacy request digests exclude missing new fields, preserving replay keys.
- Authenticated `GET /api/availability` returns a clearly simulated seven-day
  schedule: hourly 09:00–18:00 IST, unavailable starts at 10:00, 14:00 and 16:00.
  Business registration offers only available slots. API and simulator schedule
  modules are mirrored for separate Docker contexts, with a parity test.
- Authenticated `PUT /api/profile/default-address/{address_id}` validates the
  address and retains the profile's contact fields.
- Product/address save retries retain a newly created record ID if a subsequent
  optional upload/default operation fails, avoiding duplicate records on retry.

No cloud migration or credential change is needed. Restart both Python services
when applying these changes. Follow [LOCAL_SETUP](LOCAL_SETUP.md) to run locally.

## Verification

- Backend/simulator: **89 passed, 8 skipped**, live-model/emulator opt-ins off.
- Browser: **18 passed** across 390px mobile and desktop, including 320px layout
  fallback, full fake-model A2A flow, preferred-slot booking, refresh/recovery,
  explicit closure, documents, session expiry, model retry, inline profile and
  upload retry without product duplication.
- Frontend unit checks and production build passed. Python dependency check
  reported no broken requirements. Whitespace checks passed.
- Actual screenshots reviewed for Home, Products, product details, intake and
  320px fallback. Screenshots are test artifacts under `frontend/test-results`.
- Local frontend, API, Vite API proxy and simulator Agent Card returned 200 after
  restarting only the known Custra API/simulator processes.

Browser fixtures use fake model/storage boundaries with actual local A2A
transport. The updated UI has not repeated the paid live Gemini rehearsal or
hosted Firestore/Storage booking acceptance; earlier successful cloud persistence
checks remain historical evidence. Deployment/IAM/Hosting remain separate work.

## Review fixes

Contained backward Tab focus in native dialogs, preserved legacy request-key
digests, ensured date-row opens the calendar even with a saved preference,
preserved preference cancellation, kept dark readable pastel controls, corrected
original-logo crop/filter, and retained product IDs through upload retries.

The new code was self-reviewed; no independent subagent reviewer was used, per
the user's project instructions. No application behavior is accepted merely from
the earlier generated images.

## Product form refinements

Optional searchable Model follows Type/Brand and clears when either changes.
Other/manual and unknown entry work for all combinations. The curated list has
22 official-source suggestions across 12 types and 16 of 120 type/brand pairs;
see [sources and coverage](PRODUCT_MODEL_SOURCES.md). modelNumber is separate
from nickname and is used in new complaint agent facts.

Type and Brand share a row; optional purchase/warranty is collapsed initially.
The basic form fits 390×844 without scrolling. Expanded optional sections,
manual model entry, zoom and keyboards may require scrolling. Warranty supports
Months/Years with integer canonical months (2 Years = 24 months).

Add document opens Take photo, Choose photo and Upload file. Photos have a
preview; selections can be replaced/removed. Existing JPG/PNG/PDF and 5 MB limits
remain. Browser tests verify file chooser/capture wiring, not physical cameras;
unsupported browsers can use the file option. No scanner/OCR/HEIC conversion.

Regression coverage includes dependent models, manual model persistence,
years/month-end expiry, viewport fit, photo preview/removal and upload retry.

## App-wide compactness and lifecycle refinement

Tightened shared typography spacing, header padding, form spacing, list rows,
chat bubbles and dialog spacing. The selected preferred time is confirmed once
in a compact A2A popup with Confirm visit, ×, Escape and outside-tap dismissal.
Date/time selection remains in intake. No Choose later or rescheduling picker
appears during A2A. Dismissal does not create a booking. For historical cases
without a preference, the first business offer is shown for explicit confirmation.
Unavailable preferred times are not silently replaced; negotiation is deferred.

DELETE /api/products/{id} requires the existing authenticated session. One
Firestore transaction tombstones the product and closes linked active cases,
clearing pending/error state and incrementing versions so stale operations cannot
commit. Closed cases stay in history with closureReason=product_deleted, shown as
Closed — product deleted. Already resolved cases are preserved. Stale product
edits and concurrent new case creation check the product transactionally.
Deletion is retry-safe. History/documents remain stored; no external cancellation
or physical data purge is implied. A bounded transaction rejects deletion above
200 active cases rather than partially closing them.

New tests cover vault exclusion, stale edit/worker rejection, create-after-delete,
close-all/preserve-resolved behavior, unauthorized deletion, user cancellation,
failed-delete retry, history display, popup close/backdrop behavior and booking
the saved preferred slot. Firestore transaction contracts use a local fake;
real emulator/live checks remain skipped. No hosted record was deleted.

## Shared uploads and closed chats

DocumentUpload + AttachmentPicker provide one common Add document surface across
product create/edit, existing products and complaints. Product creation still
saves its record before uploading, retaining its retry protection. Existing
records upload only after a file is selected, preserving selection on failure.
Complaint uploads accept PDF as well as JPEG/PNG with the same 5 MB signature
validation. PDF attachments show links without invalid image previews.

Resolution checkbox now uses the compact native theme-accented checkbox style
and a 44px label target, fixing inherited full-width text-field dimensions.
Closed chats retain readable/selectable muted history, hide their attachment
section and all active booking/resolution controls, and end with a readable
closure notice plus Start a new complaint. Backend upload requests made after
closure return 409 case_closed; existing document reads remain available.

Verified 89 backend/simulator tests (8 live/emulator opt-ins skipped), 18 mobile
and desktop browser scenarios, frontend unit tests, build and whitespace.
Screenshots reviewed for checked resolution and closed-chat states. Camera
hardware and live hosted storage remain outside this local fixture verification.
