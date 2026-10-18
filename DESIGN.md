# Custra interface design

Implemented locally on `feat/mobile-pastel-ui`, 17 October 2026, following the
user-approved mobile layouts. See the full
[UI specification](docs/superpowers/specs/2026-10-17-custra-mobile-ui-design.md).

## Visual tokens

Source: `frontend/src/styles.css`.

| Role | Token/value |
| --- | --- |
| Page ground | `#f7f7f2` |
| Content surface | `--surface: #fffefa` |
| Main text | `--ink: #243b45` |
| Secondary text | `--muted: #526870` |
| Links/icons/focus family | `--accent: #30666b` |
| Primary action/selection | `--sage: #c9dcd0`, dark text `#233f40` |
| Dividers | `--line: #dce3dd` |
| Errors | `--error: #8e3430` |

Typography uses the platform sans-serif stack. Controls use familiar shapes,
44–48px primary targets, readable labels, keyboard focus outlines, restrained
motion and reduced-motion support. No external font, icon or UI dependency added.

## Brand asset

`frontend/public/custra-identity.png` is the actual user-supplied brand image.
`Brand.jsx` displays its symbol and wordmark through SVG viewboxes; CSS filters
mute the symbol into the approved sage/teal family. Geometry and lettering are
preserved rather than recreated from a generated mockup. The full original image
is preserved, including its unused tagline; only the brand lockup is displayed.

## Layout and interactions

- Bottom navigation: Home, Products, Complaints. Header menu: Profile,
  Addresses, Past complaints and Log out. No location dropdown.
- Four product tiles per row above 350px, three on smaller viewports. The Add
  product tile is first and remains discoverable during search.
- Home leads with Register a complaint, active cases and Next technician visit.
- Product detail has one Current complaint section, never a duplicate top CTA.
- Products includes Continue where you left off for the latest active case.
- Minimal complaint form: one description, slim address/phone/date/time rows.
- Calendar and three-column time selection appear only during complaint intake.
  The A2A visit popup shows the preferred time and one Confirm visit action,
  with ×, Escape and outside-tap dismissal. No Choose later or time reselection
  appears during A2A. Booking still requires explicit confirmation.
- Compact spacing applies throughout headers, forms, lists, chat and dialogs;
  readable text and 44–48px standard control targets are preserved.
- Delete product requires confirmation and closes linked active complaints.
  History remains under Past, labeled Closed — product deleted, never Resolved.
- Agent messages are identity-labeled left/right bubbles. Routine answers remain automated; contextual reply fields appear only for missing facts/clarification or Pause and correct. Internal resolver rewrites are never displayed.
- Modal focus is contained and returned to the initiating control. Escape closes
  only when a save/confirmation is not pending.

Static mockups are visual references, not claims that all demo timestamps,
phrasing or sample records are literal production data. The written UI spec and
later user corrections take precedence over earlier rendered labels.

## Shared attachments and closed chats

AttachmentPicker is the single camera/photo/file selection surface for product
creation/editing and existing product/case uploads. DocumentUpload wraps it for
records that already exist, with preview/replace/remove and an upload action
visible only after selection. All contexts accept JPG, PNG and PDF up to 5 MB.

Resolution uses a compact native 20px teal checkbox within a 44px label target.
Closed chats show subdued bubbles with readable text; history stays selectable.
No attachment section or action controls appear after closure. A small readable
footer says This chat is closed and links to Start a new complaint. Deleted
products use the generic intake link; other cases preselect the original product.

## Product knowledge and customer handoff

New natural-language complaints show Your input needed or Paused using existing
status tokens. Pause and correct provides an explicitly labeled correction form;
booking and original-file sharing retain explicit confirmation. Phone changes in
both intake and chat belong to the complaint and do not edit Profile.

Product Documents show stored/preparing/searchable/failed distinctions in plain
language. Chat attachments can answer a pending question without indexing; invoice
and warranty uploads offer Save to product / Not now after inspection. Original
file sharing previews a relevant saved candidate with Share this / Choose another;
multiple equally plausible candidates require selection. These controls use the
existing compact pastel theme, standard focus states and mobile layout.
