# Third-party skills

Two skills in this folder are copies of open-source skills, kept with their MIT licenses. They are pinned to the commit
below and trimmed to what a DevSquad agent can use without Bash and without network: nothing here calls a paid service.

| Skill | Upstream | Commit | What was removed |
| --- | --- | --- | --- |
| `hallmark/` | https://github.com/nutlope/hallmark (`skills/hallmark`) | `04977e1` | the theme preview images, and every script except `sloplint.mjs` (image generation with Together AI, screenshot capture, installers, hooks, tests) |
| `ui-ux-pro-max/` | https://github.com/nextlevelbuilder/ui-ux-pro-max-skill (`.claude/skills/ui-ux-pro-max`) | `6ae86f6` | the script tests and data validator, and three large provenance/licence JSON files the search does not read |

How DevSquad uses them:
- The designer reads both skills. It has no Bash: it picks hallmark's theme from its notes and searches ui-ux-pro-max's
  catalog (`data/*.csv`) with Grep.
- The Factory, not the agent, runs `hallmark/scripts/sloplint.mjs <mock-up> --json` (static, no `--render`, nothing written)
  on every mock-up before the person approves the design, and refuses the approval while any rule fails.
- The coder may run `ui-ux-pro-max/scripts/search.py` inside its sandbox (offline; it only reads `data/`).

To update one: copy the new upstream folder, remove the same parts, update the commit above and run the tests.
