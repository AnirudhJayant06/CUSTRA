# Custra working instructions

- Run commands needed for the user's authorized Custra task without repeated
  confirmation. Handle local services and verification directly. Ask when scope
  is uncertain, required information is missing, or a user decision is needed.
- Command execution permission does not authorize unrelated tasks, application
  edits, deployment, publishing, IAM/billing changes or destructive actions beyond
  the user's requested scope. Reuse authorization already given in the session.
- Use only dedicated Custra Google credentials/configuration and explicit project
  `custra-mvp-2026`. Never access legacy Sony credentials, configurations or cloud
  resources. Ask if identity, project or resource scope is uncertain.
- Provide step-by-step code for the user to implement. Do not edit application
  code unless explicitly asked.
- Keep Superpowers enabled and use its relevant workflows. Reuse approved
  decisions and plans; avoid repeating completed planning.
- Read only relevant files and skill references; keep tool output concise.
- Apply Vercel React Best Practices when working on React or Next.js.
- Do not spawn subagents unless the user explicitly requests them.
- Use Token Optimizer coaching when work becomes repetitive or context grows
  unwieldy. Do not run a full audit on every prompt or every skill invocation.
- At the start of continuing project work, read docs/SESSION_STATE.md. Treat it
  as historical context and verify any state needed for the current task.
- Automatically update docs/SESSION_STATE.md after meaningful milestones or
  changed decisions, blockers, or next steps. This documentation-only update is
  authorized without another request; it does not authorize application edits.
- Keep the handoff short: approved decisions, completed work and verification,
  open issues, and the exact next step. Distinguish proposed from completed work.
- Token Optimizer lifecycle hooks belong in the global Codex configuration;
  do not duplicate them in this project's .codex/hooks.json.
