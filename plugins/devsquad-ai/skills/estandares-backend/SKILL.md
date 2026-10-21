---
description: Backend technical standards for DevSquad AI — SOLID, Clean Architecture, layer separation, API design (HTTP codes, OpenAPI/Swagger), security (OAuth2/JWT, input validation, access control), automated tests, CI/CD, performance (indexes, rate limiting) and observability, plus a quantifiable code-quality rubric. Always use when the Coder implements server/backend logic.
---

# Backend standards (DevSquad AI)

## Before writing backend code

Consult (with WebSearch if needed) the current official documentation of the
language, framework and libraries the Architect defined in
`.devsquad/arquitectura.md` — best practices change from version to version;
do not assume that what you know from memory is still the recommended way
today.

## Architecture and code design

- **SOLID principles**: each class/module with one responsibility, open for
  extension and closed for modification, small and specific interfaces, and
  dependence on abstractions instead of concrete implementations.
- **Clean Architecture / layer separation**: separate controllers (HTTP
  input), services (business logic) and repositories (data access). Business
  logic must not depend on framework details or on the specific database.
- **Design patterns with judgment**: use the right pattern (Factory,
  Strategy, Repository, etc.) when it solves a real problem in your code —
  do not force them where a simple function is enough. Over-engineering is
  also a quality defect, not only the lack of structure.
- **Standardized APIs**: use the correct HTTP status codes (200, 201, 400,
  401, 403, 404, 409, 422, 500 — not everything is 200 or 500), define clear
  contracts (OpenAPI/Swagger when the project justifies it), and keep
  route/resource names consistent.

## Security (non-negotiable)

- **Robust authentication**: OAuth2 or JWT with correct expiration and
  renewal — never sessions without expiration or eternal tokens.
- **Validation and sanitization of all input**: prevent SQL injection, XSS
  and similar attacks. Client validation never replaces the server's.
- **Access control**: every endpoint restricted according to the role/permission
  of the authenticated user — never trust that the client "won't send" an
  unauthorized request.
- This adds to (does not replace) the secret-safety rules already defined in
  the `implementacion-calidad` skill.

## Tests and code quality

- **Automated tests**: unit tests for business logic, integration tests for
  the interaction between layers, and end-to-end tests for the critical flows
  — before considering an important increment done.
- **Code review with a quantifiable grade**: before marking an increment as
  ready, evaluate it (yourself, or ask the Orchestrator to review it) against
  this 100-point rubric:

  | Criterion | Points |
  |---|---|
  | Functional correctness (meets the story, no compile/lint errors) | 30 |
  | Security (no hardcoded secrets, server-side validation, no obvious OWASP Top 10 vulnerabilities) | 20 |
  | Adherence to SOLID / Clean Architecture (separated responsibilities, low coupling) | 20 |
  | Automated tests (cover the happy path and at least one error case) | 20 |
  | Readability and documentation (clear names, comments where the logic is not obvious) | 10 |

  An increment is not "done" if it scores below 80/100, or if the Security line
  is not at its maximum score. If it does not reach it, report explicitly what
  is missing instead of declaring it ready.
- **Continuous integration (CI/CD)**: if the project already has a repository
  configured, automate tests and deployment (e.g. GitHub Actions) — but apply
  the Architect's cost/impact framework before adding this infrastructure to
  a small POC; for a single-use prototype it can be over-engineering.

## Performance and monitoring

- **Database indexes**: on the columns that are queried or filtered often —
  without waiting for a slow query to become a reported problem.
- **Rate limiting**: protect public endpoints against abuse, especially the
  authentication ones and those that trigger costly operations.
- **Observability**: log errors in a structured way and, if the project
  justifies it, expose basic metrics (response time, error rate) —
  proportional to the project's size, not by default on everything.

## With someone non-technical

Do not show them this rubric or this jargon. Translate it into one sentence:
"before calling this done, I checked it against an internal quality list
(security, tests, whether the code is maintainable) and it passed" — or, if it
did not pass, explain in one sentence what it lacks and what you are going to
do about it.
