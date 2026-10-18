# Future development

Recorded 2026-10-18 during the A2A/retrieval design discussion. These are deferred ideas, not implemented features or implementation authorization.

- Evaluate specialized OCR, document-layout and entity-extraction models against the MVP multimodal LLM extraction baseline. Replace components only when measured accuracy, latency or cost justifies it.
- Troubleshooting recommendations, diagnosis, repair guidance and broader warranty interpretation; current proposed MVP remains focused on technician-visit registration.
- Service-center selection and appointment booking, including business-side capability, center identity/location, availability and confirmation contracts.
- Thumbs-up/down feedback linked to the relevant conversation turn and internal resolver/retrieval artifacts; investigate and support controlled step retry without duplicating external actions.
- Conditional automatic retry for classified transient extraction, embedding, retrieval or generation failures. No new automatic retry mechanism is requested for the proposed MVP; preserve the distinction from user-initiated complaint resume and existing operation deduplication.

Deferred beyond the implemented MVP: general semantic retrieval across prior complaints and autonomous background conversation processing. Product Documents indexing and direct inspection of chat-only attachments are now the selected implementation, rather than unresolved alternatives.
