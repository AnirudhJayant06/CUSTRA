# Submission requirements supplied by the user

Recorded: 16 October 2026. Source: user-pasted competition page excerpts; original
URL/challenge identity has not yet been supplied or independently confirmed.

## Required deliverables and operation

- Pitch deck using the prescribed template, submitted as PDF.
- Publicly accessible deployed working prototype link, functional throughout
  evaluation. The excerpt offers no retry allowance for unavailable integrations.
- Accessible GitHub repository containing relevant source/supporting materials;
  the general instruction says all submission links must be public.
- Public YouTube/Vimeo/Google Drive demonstration. One section specifies 3–4
  minutes and another specifies 3 minutes: plan for exactly 3 minutes to satisfy
  both supplied statements, subject to any more specific organizer instruction.
- Brief description explaining use of Firebase, Firestore, Cloud Run and Gemini.
  Treat all four technologies as mandatory based on the supplied wording.
- English code, documentation and presentation materials.
- Clear problem statement, social/community benefit, working functionality,
  usability/accessibility and scalability explanation.

## Eligibility confirmed by user

The quoted category list includes Healthcare, Education, Sustainability,
Accessibility and Social Good. The user subsequently explicitly confirmed that
Retail & Commerce is also eligible for the same challenge. Preserve Custra's
approved Retail & Commerce problem statement; no category change is needed.

## Team access implications

The excerpts do not require a separate Google Cloud project/account per teammate,
sharing a personal Google login, or handing the Cloud console to judges. Proposed
collaboration remains Anshum's own Google identity with scoped IAM in the existing
`custra-mvp-2026` project. Project APIs/resources can be reused; her deployer
permissions and runtime service-account permissions require separate configuration.
No IAM change or deployment is authorized by the pasted rules.

The earlier dummy echo application does not demonstrate Gemini or persistent
Firestore use, so it cannot by itself establish all listed technology requirements.
The current MVP has passed local/live-model checks but its complete hosted path
still needs deployment and acceptance verification.

The supplied rules do not expressly resolve whether a shared demo login is
acceptable for the publicly accessible prototype. Confirm reviewer access before
submission; do not expose Google credentials as an access mechanism.

The current owner/teammate deployment steps are in
`ANSHUM_DUMMY_DEPLOYMENT_GUIDE.md`; any cloud/IAM/resource changes still need
the owner's review and approval. Development cutoff remains the user's 18 October 2026, 16:00 IST; the
excerpt does not establish the actual competition submission deadline.
