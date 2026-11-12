# Third-party code

One folder here is a trimmed copy of an open-source project, kept with its MIT license.

| Folder | Upstream | Commit | What is kept |
| --- | --- | --- | --- |
| `hallmark/` | https://github.com/nutlope/hallmark (`skills/hallmark`) | `04977e1` | only `scripts/sloplint.mjs` (the mechanical checker, zero dependencies) and the license. It is **not a skill** any more: there is no `SKILL.md` and the designer is not told to use it |

How DevSquad uses it: the Factory, not an agent, runs `hallmark/scripts/sloplint.mjs <mock-up> --json` (static, no `--render`,
nothing written) on every mock-up before the person approves the design, and refuses the approval while a Floor rule fails.
The rules it checks are written into the designer's instructions (`agents/disenador.md`, "Design direction").

Removed in 0.10.0 (2026-11-12), with the evidence in the changelog:
- `ui-ux-pro-max` (https://github.com/nextlevelbuilder/ui-ux-pro-max-skill): a lookup by product type that recommended a
  landing-page pattern with testimonials, sky blue and Poppins for a physiotherapy booking app, and web fonts the mock-ups cannot load.
- hallmark's `SKILL.md`, themes, genres and references: written for marketing sites (hero, six to nine sections), not for app screens.
