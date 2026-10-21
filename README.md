# DevSquad AI

A team of SDLC agents for Claude Code.

It includes 5 agents:

- **Orchestrator** (Sonnet · medium effort) — project director, the single entry point.
- **BSA** (Sonnet · xhigh effort) — turns your idea into clear requirements.
- **Architect** (Opus · high effort) — defines the architecture, always explaining the cost and
  impact of each decision. On the stack it follows a hierarchy: if you already
  declared one when setting up your profile, that stack rules and the Architect
  designs on top of it without questioning it; if you did not declare one, the
  Architect proposes it and justifies it against your requirements.
- **Designer** (Sonnet · high effort) — defines palette, typography, layout, accessibility and
  responsiveness before any code is written, so that nobody improvises
  the visual design while programming.
- **Coder** (Sonnet · high effort) — implements the code following what is already defined, and
  stops to ask before touching any file you marked as protected.

The agents work in English: every file they write (`.devsquad/`, documents,
decisions, commit messages) is in English. They can chat with you in another
language, but the project's records stay in English.

> The names of the agents (`orquestador`, `bsa`, `arquitecto`, `disenador`,
> `coder`), the commands (`/devsquad-ai:aprobar`, `/devsquad-ai:cancelar`,
> `devsquad-estado`), the track states (`borrador`, `listo`, `en_progreso`…) and
> the file names under `.devsquad/` are identifiers: they stay as they are so
> that existing projects and the Factory keep working.

## Installation

You need the Claude Code desktop app or CLI installed.

### From GitHub

```
/plugin marketplace add <your-user>/devsquad-ai-marketplace
/plugin install devsquad-ai@devsquad-ai-marketplace
/reload-plugins
```

### From a local copy

```
/plugin marketplace add /full/path/to/devsquad-ai-marketplace
/plugin install devsquad-ai@devsquad-ai-marketplace
/reload-plugins
```

Restart Claude Code once. When you reopen the project, the Orchestrator
activates automatically as the main agent.

## First use

The first time you talk to Claude Code in a new project, the Orchestrator
will ask you for a few basics (how you like to be addressed, your technical
level, your preferred language). This is so that all the agents adapt to how
you like to work — you don't need to know anything technical to answer these
questions.

It will also ask you two things about the project, regardless of your technical
level:

- **Whether the stack is already decided** or you prefer the Architect to
  propose it. If you already have it, describe it in your own words (language,
  frameworks, where it runs, and hard constraints such as "all local" or "no
  paid APIs") and the team adjusts to that.
- **Whether there is code or files that are already finished** and must not be
  regenerated (for example, a runtime you already debugged or a configuration
  file that already works). They are marked as protected and no agent touches
  them without asking you first.

After that, just tell it your project idea the way you would tell a person.
The Orchestrator takes care of coordinating the rest of the team.

## How to start a new project, separate from the previous one (important)

A Claude Code session stays anchored to the folder where you opened it — it
does not switch projects just because you tell it "let's start something new"
in the chat, because it cannot move folders on its own.

If you want a completely separate project from the one you already have in
progress:

1. Create (or locate) the new folder in your file explorer.
2. Open a terminal **inside that new folder** (do not reuse the window where
   you were working on the other project).
3. Run `claude` there to start a new session.

If instead you keep writing in the same conversation as before, the
Orchestrator will keep seeing your previous project's state — and, if it
detects that what you describe does not match that project, it will tell you
explicitly which folder it is standing in so you can correct it, instead of
mixing the two projects.

## What to expect in this version

This version covers: requirements discovery (BSA), architecture design with
cost transparency (Architect), the design system (Designer), and
implementation with backend and frontend technical standards (Coder). It does
**not** yet include (see `CHANGELOG.md`):

- Reviewer, Cybersecurity, QA and Deployment as separate agents.
- A more robust session hand-off system.
- A step-by-step guide to safely extracting API keys/tokens.

Report to Omar any point where the Orchestrator did not know what to do or
where an explanation was not clear — that is exactly what this testing phase
is meant to find out.

## File structure the project generates

DevSquad AI creates a `.devsquad/` folder inside your project. **It is
versioned in Git**: it is the project's memory (do not add it to
`.gitignore`). It contains:

- `perfil.md` — your profile (technical level, language, preferences, declared
  stack and protected files).
- `requerimientos.md` — what the BSA defined.
- `arquitectura.md` — what the Architect defined.
- `diseno.md` — what the Designer defined.
- `estado.md` — the previous format; 0.6.0 replaced it with `estado.json` and
  `tracks/` (see below) and it is no longer written.
- `estado.json` — machine-readable state, with `schema_version`.
- `tracks/NNN-name/` — a unit of work: `track.json` (state), `spec.md` (what and
  the acceptance criteria) and `plan.md` (tasks `[ ]` `[~]` `[x]`, each one done
  with the commit that implements it). Only one track is open at a time: no
  other is opened until the current one is closed.

### Gates (the plugin's hooks)

What is mandatory is enforced by code, not by the model's memory
(`hooks/hooks.json` + `scripts/devsquad_hook.py`). They only act on this
plugin's agents; they block with a message that says the missing step:

- **Profile first**: without `.devsquad/perfil.md` nothing is delegated, written or run.
- **Human approval** (see below): the track does not move to `listo` without the
  person's approval of the architecture and the design; the profile's
  verification commands are only run if they approved them; and the closing is
  governed by the track's closing policy.
- `estado.json` and `track.json` (where the approvals live) are not edited by
  the model, and `devsquad-estado aprobar|cancelar` is not run by the agents.
- **Phase order**: BSA → Architect → Designer → Coder (according to the
  deliverables in `.devsquad/`). Delegating to the coder moves the track from
  `listo` to `en_progreso`.
- **Track**: project code is only written with a track in `en_progreso` or
  `correcciones`.
- **Protected files** (those in the profile) and **secrets** (`.env*`, keys).
- **The coder does not finish in red**: it runs the profile's "Verification
  commands"; after 3 blocks in a row it escalates to the person.
- **Review of the coder's result**: since the coder has `Bash` (`echo X > .env`,
  `sed -i`), when it finishes what changed in Git is reviewed against what was
  already changed when it was delegated to: a real `.env*` (even if it is in
  `.gitignore`), secret patterns or modified protected files. It blocks with
  the same cap of 3 blocks.
- When each planning agent or the coder finishes, the hook advances the track
  with `devsquad-estado`. **`Stop` only informs** (for example "waiting for the
  closing approval"): it never closes or blocks.

They require `python3`; if it is missing, the hooks fail without blocking (a
known limit).

> **Scope of the gates.** They are **guardrails against model mistakes, not a
> security boundary**. With `Bash` an agent (or someone instructing it) can get
> around them: the result review catches the usual but not the deliberate (a
> file outside the project, a secret in an unknown format, a command that
> rewrites Git history, etc.). To truly isolate the agent you need
> operating-system isolation (an unprivileged user, no credentials within
> reach), not hooks.

### Human approvals, closing policy and cancel

What the person decides is only recorded by **code** (the hooks or the
Factory), never by the model:

| What | How the person gives it (terminal) | In the Factory |
|---|---|---|
| Architecture | `/devsquad-ai:aprobar arquitectura` | `ask_human` with `kind: "approval"`, `subject: "arquitectura"` |
| Design | `/devsquad-ai:aprobar diseno` | `subject: "diseno"` |
| The profile's verification commands | `/devsquad-ai:aprobar comandos` | `subject: "comandos"` |
| Closing the track | `/devsquad-ai:aprobar cierre` | `subject: "cierre"` |
| Cancel a track | `/devsquad-ai:cancelar <reason>` | `ask_human` with `kind: "cancel"` |

In the terminal a `UserPromptSubmit` hook sees the text the person types (the
model cannot produce it; the `aprobar` and `cancelar` skills cannot be invoked
by the model). In the Factory, the Factory runs
`devsquad-estado aprobar <object> --fuente factory --por <user>` when it
receives the answer (the `ask_human` contract is implemented in the Factory).

- The architecture and design approvals carry the document's **SHA-256
  hash**: if it changes, the approval becomes **stale**. The commands approval
  carries the hash of the command list. The closing approval carries the
  **exact commit** (`HEAD`): new commits make it stale.
- **Closing policy** of each track (`track.json`, `politica_cierre`): proposed by
  the Architect in `arquitectura.md` (`**Closing policy**: humano`), approved by
  the person together with the architecture, and it stays inside the approved
  hash; the model cannot change it. (The older `**Política de cierre**` label is
  still understood.)
  - `humano` (default): objective criteria (tasks with a commit and, if
    `revision.json`/`verificacion.json` exist, state `verificado` and approved)
    **plus** the closing approval. When it is approved, the code closes.
  - `automatico`: the code closes by itself with the objective criteria.
    **It is rejected while the reviewer agent does not exist** (phase C).
- `devsquad-estado cancelar --motivo ...` (or `/devsquad-ai:cancelar`): the
  track moves to `cancelado`, the single slot is freed and the history is kept
  (`cancelacion` with reason, previous state, who and when).

### Atomic startup and memory

- When you start, resume, clear (`/clear`) or compact the conversation, the
  `SessionStart` hook injects a **pointer** of a few script-generated lines
  (`scripts/devsquad_puntero.py`, hard cap of 10,000 characters): active track
  and its state, next task, last commit, blockers, available memory and the
  suggested next step. "Where did I leave off?" is an exact query on the state,
  not a search. (`PreCompact` cannot inject context; after compacting,
  `SessionStart` restores it.)
- **Memory, level 1**: one file per decision or learning in
  `.devsquad/memoria/{decisiones,aprendizajes}/`, and a generated index
  (`.devsquad/memoria/indice.md`) that the agent reads with Read; the
  `buscar-memoria` skill explains how. The Orchestrator has no `Bash`. Levels 2
  (full text) and 3 (meaning) are left for later.

### The `devsquad-estado` script

It changes and validates that state: `devsquad-estado init | crear | transicion |
tarea | aprobar | cancelar | cerrar | estado | validar | migrar` (`--help` for
the detail). It is a Python 3.8+ script with no dependencies; the plugin puts it
on the Bash tool's `PATH`. **Known limit:** it needs `python3` (and `sh`);
without them, for example on Windows without Python, it fails with a clear
message.

You do not need to touch these files by hand; the team of agents reads and
updates them for you.
