---
description: Standards for making architecture decisions in DevSquad AI projects — stack selection protocol (never assume Supabase/Vercel by default), cost/impact framework, non-functional attributes and quality trade-offs (ATAM style), architecture patterns and modular decomposition, reference quality standards (ISO/IEC 25010, ISO/IEC 5055, CMMI, IEEE 730), security by default, and environment variable handling. Always use when defining a project's architecture, before writing arquitectura.md.
---

# Technical architecture with standards

## Stack selection protocol — never assume

A real error detected: the architect assumed Next.js + Supabase + Vercel
without asking. That does not happen again. Before proposing any stack:

- **If the person's profile is non-technical** (check
  `.devsquad/perfil.md`): offer the "basic kit to deploy your application"
  as a recommendation, not as a silent default. Say it like this:
  > "I recommend a free starter toolkit (Next.js + Supabase + Vercel) that
  > lets you have your app running on the internet at no initial cost. Do
  > you want me to use it, or would you rather we explore other options?"
  If they say yes, proceed. If they hesitate or say no, ask what worries
  them and adjust — never impose it.

- **If the profile is technical**: ask directly and without over-explaining,
  something like "do you have a stack in mind, or do you prefer that I
  recommend one based on the requirements?". Do not assume Supabase/Vercel
  just because it is DevSquad AI's historical default.

- **If the profile already declares a stack**, this question protocol does
  not apply — see the decision hierarchy in the Architect agent's prompt.

## Cost/impact framework (mandatory, already defined in your agent prompt)

For each non-obvious decision: estimated cost, impact, and future impact.
This skill does not repeat that rule — it lives in the agent prompt because
it is non-negotiable — but remember to apply it also to the choice of the
stack itself, not only to decisions within an already chosen stack, and to
any process standard (CMMI, IEEE 730) you consider adopting below.

## Non-functional attributes (NFAs)

Before settling the architecture, identify target metrics, even if
approximate: expected response time, availability, expected concurrency (how
many people will use it at once?). With someone non-technical, do not ask for
these terms — ask in their language ("will only you use this, or several
people at the same time?", "how bad would it be if it took a few seconds to
respond?") and translate the answer into an NFA yourself. Document what comes
out, even if it is one sentence per attribute — a formal process is not needed
for a small project.

## Trade-off analysis (ATAM style)

For non-trivial architecture decisions, explicitly name which quality
attribute they favor and which one they sacrifice (e.g. "caching this makes
it faster, but the data may take a few seconds to reflect changes"; "more
security validations add an extra step to the user's flow"). This is the
essence of an Architecture Tradeoff Analysis Method (ATAM) applied in
proportion: it is not a full formal process with stakeholders and documented
scenarios unless the person explicitly asks for it — it is the habit of
saying the trade-off out loud instead of leaving it implicit.

## Architecture patterns and modular decomposition

- Choose the pattern (modular monolith, layers, events, microservices)
  according to the project's real complexity, not by fashion. For most
  DevSquad AI projects (see "Scope limit" in the agent prompt), a well
  separated modular monolith is more appropriate than microservices — only
  justify something more complex if the requirements genuinely ask for it,
  and put that decision through the cost/impact framework.
- Within that pattern, divide the system into components/layers with high
  cohesion and low coupling (e.g. presentation, business logic, data access
  — see the `estandares-backend` skill for the detail on layer separation)
  to ease testing and maintenance. Document this division in the folder
  structure of the deliverable.

## Reference quality standards

Use them as a frame of reference, not as a mandatory checklist to impose on
every project — their application also goes through the cost/impact
framework:

- **ISO/IEC 25010**: defines product quality characteristics (reliability,
  performance efficiency, security, maintainability, usability,
  compatibility, portability). Use it as a mental checklist when verifying
  that the architecture did not neglect any quality dimension, even in small
  projects.
- **ISO/IEC 5055**: measures the internal structure of the code (not just
  that it "works") to ensure security and reliability. Pass this expectation
  on to the Coder — it connects with the quality rubric of the
  `estandares-backend` skill.
- **CMMI** and **IEEE 730**: are process and quality-assurance standards more
  typical of large organizations with compliance requirements. Mention them
  as a reference if the person belongs to a company that demands them, but do
  not impose them as a mandatory process in small projects or POCs — it would
  be a disproportionate cost for what is being built.

## Security by default

- Enable row-level security (RLS) or the equivalent by default on any
  database with client access — not as something optional to add later.
- No key with elevated privileges (e.g. service role) should be planned to
  live in code that runs in the browser.
- Apply the principle of least privilege: each piece of the system must have
  access only to what it needs, no more.

## Environment variables — anticipate, don't improvise

Explicitly list in `.devsquad/arquitectura.md` which environment variables
the project will need (names, what each one is for, and whether it is secret
or not) — this gives the coder and the Orchestrator what they need to warn in
advance, instead of the person finding out halfway through.

## Connection with environment preparation

Explicitly mention in your deliverable which local tools the chosen stack
will need (e.g. "Node.js and npm" for a JavaScript stack). This allows the
person to be warned in advance, before the coder starts — not after something
fails.
