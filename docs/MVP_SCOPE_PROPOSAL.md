# Custra MVP scope — revised requirements

Updated: 2026-10-16. Requirements discussion only; no implementation authorized.
Development cutoff: 18 October 2026, 4:00 pm IST.
User decisions below supersede the earlier proposal. Recommendations are labeled.

## User decisions

- Two pillars: free Product Vault and future paid Complaint Resolution Agent.
- Single demo account with fixed username/password for V1. Google sign-in,
  multi-user ownership checks, and per-user/global usage quotas are future scope.
- After login, collect reusable profile name, phone number and email address.
  Include saved addresses with one dummy demo address pre-added. Reuse profile
  details when the Business Agent asks; do not ask for contact name per complaint.
- Add address beside the saved-address selector opens an overlay dialog. Saving
  persists the new address under Account settings → Addresses for later reuse.
  Proposed behavior: select the newly saved address for the current complaint;
  cancel leaves the existing selection and form unchanged.
- User enters basic product details. No document/image field extraction in V1.
  Serial numbers and difficult-to-find details are not required by the simulated
  Business Agent. Extraction belongs to future scope.
- Show mock service-center data inside Custra, clearly labeled as demo data.
  Official manufacturer locator links belong to future scope.
- Complaint intake: a short basic form with a saved-address dropdown, then a
  visibly automated Consumer Agent ↔ simulated Business Agent conversation.
  Business questions use collected product, profile and complaint facts.
- Demonstrate successful complaint registration, not warranty rejection, document
  analysis, terms-backed challenge or negotiation. Those are future capabilities.
- No upfront time preference in the complaint form (user decision, 16 October).
  Latest ordering requirement: selecting the appointment date and time is the last
  user step of complaint registration, after all agent questions are complete.
  Only booking confirmation follows; repair confirmation/closure is a separate
  later lifecycle action. Scheduling occurs only in the final dialog.
  Latest decision supersedes automatic booking: user selects the appointment time
  through a dialog, not chat text, before the simulated appointment is finalized.
  Proposed dialog shows available dated slots and a Confirm
  appointment action. Dismissing it leaves the case awaiting time selection, with
  a way to reopen it. No appointment is finalized without a confirmed selection.
- Closure always requires user confirmation; registration/booking is not resolution.
- Missing-information pause/resume is the final optional increment only if core
  work is stable before cutoff; otherwise future scope. No timeout decision needed.
- If missing-information collection is added, save reusable facts for later use.
  Product facts belong with the product; case-specific facts remain on that case.
- Preserve product General info/Complaints tabs, global Complaints view, static
  searchable product-type/brand lists and case persistence from earlier requirements.
- Standalone contact history placement delegated to assistant: recommendation is
  future scope. Clicking a contact link must not be recorded as a completed call.

## Proposed basic fields and happy flows

Proposed four-field complaint form: selected saved product (brand/model reused),
issue summary, issue description, saved service address dropdown. Name, phone and
email come from the saved profile. Product and issue-field wording remain proposed;
saved-address selection
and removal of repeated contact-name entry are user decisions.
No serial number, warranty proof or document upload needed to register demo complaint.

Entry: sign in with the demo credentials → complete/review basic profile → see
pre-added dummy address → save profile → open Vault. Returning visits reuse saved
details. This is one shared demo identity, not private accounts for each reviewer;
use fictional profile data and documents during the demo.

Vault: enter basic product details → save → view product and optional stored
invoice/warranty → view clearly labeled mock nearby-service listings and mock support
information. Any warranty expiry displayed comes from user-entered values, not extraction.
Document storage/viewing is retained from earlier scope; documents are not analyzed.
No actual calls/messages are sent to mock contacts.

Agent: choose product → select saved address or add one in a popup → complete
basic form → start case →
watch business questions and consumer answers using saved facts → receive simulated
complaint reference → select/confirm a time in appointment dialog → receive
simulated appointment confirmation → case stays open → user
confirms repair → close. Refresh preserves the case; retry must not duplicate it.
Unsupported scenarios show an explanation, not fabricated success. Mock availability
offers future dated slots in the final dialog; future real scheduling needs availability handling.

Automated-conversation UI requirement: this must look like Custra working on the
user's behalf, not a live chat waiting for user messages. Proposed presentation:
Consumer/Business Agent labels, an Automated conversation banner, sequential message
arrival, restrained typing/thinking indicators while work is actually pending,
and progress labels such as Contacting support / Answering questions / Registered.
No user message composer in core V1. Stop indicators on completion or failure;
show a clear result/reference card and retry on failure. Respect reduced-motion
preferences. Specific visual effects remain proposed; simulation stays labeled.

Optional last increment: ask for missing text → pause → persist → user supplies
information → save reusable facts in the appropriate place → resume. This is not
part of the required V1 acceptance test.

## Demo login and cost protection

Approved simplification: one fixed demo username/password, no Google sign-in or
account registration. Multi-user ownership checks and per-user/global usage quotas
are deferred. All authorized demo sessions share the same demo workspace.

Recommended implementation boundary: validate the fixed credentials on the server,
store the credential secret outside frontend code and source control, and use a
server-validated session for protected API/document access. A frontend-only password
check would not protect model endpoints. Exact session implementation remains open.

Remaining recommended safeguards (not reintroducing deferred usage quotas): bounded
agent turns/tokens/retries, duplicate-run prevention, server-side model credentials,
small Cloud Run scaling limits, request/upload size limits, billing alerts and an
agent disable switch. Login-attempt throttling is a separate recommendation, not a
per-user LLM allowance. Exact settings remain open. Fixed credentials and alerts
do not cap spending; repeated authenticated runs and public traffic can still cost.
App Check is a future option alongside real sign-in, not required for this demo.
Official references:
- https://firebase.google.com/docs/app-check
- https://docs.cloud.google.com/billing/docs/how-to/budgets
- https://docs.cloud.google.com/run/docs/configuring/max-instances-limits

## Proposed versions

- V1 core by deadline: minimal Vault, manual basic entry, mock service-center cards,
  single demo login, saved basic profile/dummy address, short complaint form with
  address dropdown, visibly automated bounded agent exchange, simulated registration and
  user-selected appointment via dialog, persisted history, user-confirmed closure.
  Include add-address popup and Account settings → Addresses persistence.
- V1 optional final increment: missing-information pause/resume and reusable facts,
  only after core verification; otherwise move to V1.1. No deadline extension.
- V1.1 after submission: extraction with user review, missing-information handling
  if deferred, official locator links alongside labeled mock data, self-reported
  contact history. Before a multi-user pilot, add Google sign-in, per-user ownership
  checks, per-user/global usage quotas and private account/document management.
- V1.2: one real authorized support channel, follow-ups, real availability handling,
  manual takeover/hand-back, warranty-grounded challenge when justified.
- V2: validated per-case pricing, payments and clear service/refund terms; expand
  supported cases only after measuring real outcomes and cost.
- V3: broader categories/regions, maintained service directory, integrations,
  family Vault and additional languages/channels as demand warrants.

## Deadline and acceptance

15 October: settle remaining form choices and persistent foundation.
16 October: single demo login/profile, minimal Vault and first agent exchange.
17 October: complete simulated registration, appointment and user-confirmed closure;
verify persistence and deploy full flow. Freeze core features that evening.
18 October morning–2 pm: hosted mobile testing, session enforcement, failure/retry,
no duplicate cases/appointments and demo rehearsal. Optional increment only if
already stable with enough time to validate; otherwise defer it.
18 October 2–4 pm: blocker fixes, final verification and code freeze.
After 4 pm: submission documentation and presentation only.

Core acceptance: manually saved product survives refresh; mock listings are labeled;
Business Agent asks only supported basic questions and Consumer Agent uses saved
facts; simulated complaint reference appears; appointment is finalized only after
user selection in the dialog; case stays
open until user confirms resolution. Demo login must gate protected endpoints before
model invocation; profile and saved address survive refresh and populate complaints.
New addresses saved from the popup also appear under Account settings → Addresses.
Conversation is visibly automated, with no active chat composer and no endless
typing indicator after failure/completion. Multi-user isolation and usage quotas
are not V1 acceptance criteria.
No claim of real manufacturer registration, actual repair, or proven resolution
capability follows from the simulated demo.

## Open decisions

Exact remaining basic fields, appointment-slot options, location/brands for mock data,
demo credential delivery/session details, model choice and remaining recommended
safeguard settings. No application code authorized.
