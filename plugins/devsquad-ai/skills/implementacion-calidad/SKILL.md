---
description: General quality, security and code good-practice standards for the implementation phase in DevSquad AI projects — small increments, error handling, input validation, secret management, and environment verification before starting. For the specific technical detail of backend or frontend, see the `estandares-backend` and `estandares-frontend` skills. Always use when implementing code.
---

# Implementation quality

## Before writing the first line of code

Use the `preparar-entorno` skill — verify that the necessary tools are
installed before starting. Never skip it, even if it seems obvious that they
should already be installed.

## Code standards

- **Small, verifiable increments.** Build and show one piece at a time, not
  the whole project in one go.
- **Handle errors explicitly.** Never leave an error silenced or ignored — at
  least log it or show it clearly.
- **Validate all user input** in forms or inputs, both on the client side (for
  experience) and on the server side (for real security — client validation
  is never enough on its own).
- **Readability over "cleverness".** Prioritize code that any other developer
  (or you yourself in six months) can understand quickly.

## Technical standards per layer

This skill covers the general and cross-cutting. For the specific technical
detail of the layer you are touching, also use:
- `estandares-backend`: SOLID, Clean Architecture, API design,
  authentication, automated tests, CI/CD, performance, and the quantifiable
  code-quality rubric.
- `estandares-frontend`: accessibility (WCAG), responsive design, Atomic
  Design, and UX laws.

## Secret safety (non-negotiable)

- Never hardcode credentials, API keys or tokens in the source code.
- Use environment variables, following exactly what was already documented in
  `.devsquad/arquitectura.md`.
- Never write a real secret (password, PIN, key) into a file yourself — the
  person does that manually, always.
- Never attach or show the full content of an `.env*` file to the person.

## Visual design

Follow `.devsquad/diseno.md` to the letter for colors, typography and layout
— do not improvise. Use the `diseno-ui` skill as a quick reference for the
minimum contrast (4.5:1). Remove any style inherited from the base template
that is not aligned with the defined design (this already caused a real bug
of illegible contrast).

## Definition of "done" for an increment

An increment is not ready to be shown to the person if:
- It does not compile or has type/lint errors.
- It was not visually checked (if a tool is available) that the text is
  legible.
- It contains something hardcoded that should be an environment variable.
- It was not explained, in one simple sentence, what the person should try.
- It is backend work and does not reach 80/100 on the quality rubric of
  `estandares-backend`, or its security line is not complete.
