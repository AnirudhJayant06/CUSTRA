# Custra mobile pastel UI implementation plan

> Execute inline with superpowers:executing-plans. User explicitly authorized all discussed implementation changes; no subagents, deployment or push.

**Goal:** Implement the approved mobile pastel UI and low-effort complaint flow.
**Architecture:** Preserve React/Vite + FastAPI + A2A and shared persistence. Add optional backward-compatible product/preference fields and a shared deterministic demo schedule. Reuse durable case operations and explicit booking/closure.
**Spec:** `docs/superpowers/specs/2026-10-17-custra-mobile-ui-design.md` and approved preview boards.

## Constraints and rulings

- Home / Products / Complaints; Next technician visit; four product columns at normal phone widths, fewer at narrow/enlarged layouts.
- No cloud calls/mutations, migrations, new dependencies, deployment, commit or push required for this task. Work on local `feat/mobile-pastel-ui`; preserve untracked design/session files.
- User's explicit implement-all instruction authorizes inline execution of this plan. No repeated plan approval or subagent dispatch.
- Keep exact source logo geometry using the supplied raster through SVG viewboxes and CSS recoloring; no generated logo approximation in production.
- New nickname optional; displayName remains a compatible alias. Warranty duration is months; derive expiry by calendar addition clamped to month-end, status valid through expiry day in Asia/Kolkata. Unknown dates are unknown, not expired. Preserve legacy explicit warrantyExpiry.
- Description alone derives the legacy required issueSummary from its first 120 characters. Name/email remain profile facts; complaint form displays phone only unless missing details require inline completion.
- Demo schedule: next seven days, 09:00–18:00 IST hourly, deterministic unavailable hours (10,14,16); shared server source and registration offers. Preferences contain ISO date and slot ID; they do not reserve/book. Validate and persist them in the immutable case input; explicit booking uses only business-offered slots.
- Profile/address changes never change existing facts snapshots. No deleting records or weakening session/origin/access rules.
- Review focus: legacy products; leap/month-end warranties; expired/unavailable preferences; upload partial failures without duplicate products; keyboard/modal/320px layout and expired sessions.

## Tasks

### 1. Backward-compatible product/profile/preference contracts
Files: backend models/product.py, models/complaint.py, services/vault.py, services/cases.py, api/account.py, api/complaints.py; mirrored demo schedule modules and simulator executor.
- [x] Add tests for blank nickname fallback, nickname editing, warranty month-end arithmetic, invalid periods and legacy fields, default address validation, single description and preferred-slot validation/persistence/idempotency.
- [x] Run targeted tests, confirm failures before implementing.
- [x] Implement product normalization/enriched read responses; default-address endpoint; authenticated pre-registration schedule endpoint backed by shared fixture; preference input and validation.
- [x] Use same schedule in simulator future_slots; preserve replay and booked slots. Run backend/simulator suite.

### 2. Mobile shell, theme and product/account flows
Files: frontend App/styles, components Icon/Brand/Modal/ProductForm/AddressDialog, pages Home/Vault/ProductDetail/Account/Addresses/ProductEditor; frontend/public logo asset.
- [x] Write browser requirements for Home/nav, four-column search/product grid, nickname/warranty creation, default addresses and no duplicate case CTA. Observe pre-change failures.
- [x] Implement palette tokens, safe-area bottom nav, profile menu/logout, exact original logo rendering; semantic SVG category icons.
- [x] Implement Home active cases/next visit, searchable grid + resume card, product detail, add/edit including sequential upload recovery, Profile and Addresses/default selection.
- [x] Verify frontend build and targeted browser flows.

### 3. Lean intake, pickers and chat
Files: frontend components SchedulePicker/AppointmentDialog/ConversationTimeline, pages NewComplaint/CaseDetail/Complaints, utilities/format.
- [x] Test selecting/cancelling/changing preferred date/time, unavailable slots, preserved draft, new complaint retry/dedup, preferred-slot booking and lifecycle views.
- [x] Implement slim address/phone/date/time rows with modal calendar and three-column time grid; inline missing profile and address entry; one description field.
- [x] Implement readable agent bubbles, saved progress, preferred slot preselection/revalidation, explicit booking and closure; Active/Past lists.
- [x] Run browser suite mobile/desktop and frontend unit tests/build.

### 4. Verification and handoff
- [x] Update fixture browser tests for the new user-visible flow while preserving upload/retry/expiry/recovery/closure assertions.
- [x] Run full backend/simulator, frontend unit/build/browser checks, pip check, whitespace checks.
- [x] Inspect screenshots at 390px, 320px and desktop; fix substantive layout/contrast/focus issues in batches. Run relevant regressions.
- [x] Document schema/UX changes, test evidence and remaining hosted/live acceptance. Update SESSION_STATE. Leave code locally reviewable; no deployment/push.

## Execution ledger

- Started: tracked baseline clean at bd261cb; local designs/session notes preserved. Native worktree not used because approved artifacts are untracked in this checkout; isolated feature branch protects develop's pointer. No commits planned without request.

- Complete: backend/simulator 81 passed, 8 skipped; browser 12 passed; frontend unit/build, pip consistency and whitespace passed. Source snapshots reviewed at mobile/desktop/320px. See docs/MOBILE_UI_IMPLEMENTATION.md.
- Ruling: schedule code is mirrored into the two independent Docker build contexts and parity-tested rather than adding a cross-container package dependency.
- Review fixes: native dialog backward Tab trap; legacy idempotency digest compatibility; date-row opens calendar with saved preference; sequential upload/default failures retain record IDs; exact logo viewboxes/filter corrected.
- Current services restarted locally: API session 23203, simulator 9300; existing Vite remains on 5173. Health/proxy/card 200. No new live cloud/model requests, commits, pushes or deployment.
