# Product form refinements

Execute inline; user finalized optional Model and delegated layout/attachment
choices after explicitly requesting discussion first. This resumes the existing
authorization to implement agreed refinements. No deployment, push or subagents.

- [x] Research official India model examples across 12 categories; keep sources
  and checked dates, manual fallback for unsupported combinations, no exhaustiveness claim.
- [x] RED/GREEN backend tests for optional model persistence, source coverage,
  type/brand association and real model in agent snapshots.
- [x] RED/GREEN browser test for searchable dependent models/manual fallback,
  cleared selection on brand changes and Years-to-Months conversion.
- [x] Compact shared Add/Edit form with paired identity inputs, collapsed
  purchase/warranty, unit selector and accessible save action.
- [x] Reusable camera/photo/file attachment sheet and preview/removal, preserving
  retry-safe product creation and existing file picker capability.
- [x] Verify basic form viewport fit, keyboard/modal behavior, all backend and
  browser regressions, build and screenshot review. Refresh only local API.

Rulings: modelNumber accepts a manufacturer model name when an exact regional
code is not verified. Existing nickname fallback remains Brand + Type. No model
choice is automatically selected. Warranty unit is presentation-only; canonical
warrantyMonths stays integer 1–120. Camera input requests rear camera, may fall
back on unsupported browsers. JPEG/PNG/PDF <=5,000,000 bytes remain the file scope;
unsupported HEIC/large captures receive an actionable error. No photo/OCR API.
