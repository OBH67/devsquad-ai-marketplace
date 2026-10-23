---
description: Initializes the person's and the project's profile for DevSquad AI, asking for preferred name, technical level, language, stack, protected files and business rules if applicable. Use the first time someone works with DevSquad AI on a project, or when they ask to "reset my profile" or "set up DevSquad AI".
---

# Start a DevSquad AI project

Creates the `.devsquad/perfil.md` file that all DevSquad AI agents
(orquestador, bsa, arquitecto, coder) read to adapt their language and level
of detail.

## Steps

1. Check whether `.devsquad/perfil.md` already exists. If it does, show it to
   the person and ask whether they want to keep it or update it — do not
   overwrite it without confirming.

2. Ask, conversationally (one or two questions at a time, not a long form all
   at once):
   - **Preferred name**: how would they like to be addressed?
   - **Technical level**: do they have experience with software
     development, or do they prefer that everything be explained without
     taking technical terms for granted?
   - **Preferred language** for the conversation.
   - **Stack**: is the stack already decided, or do they want the Architect
     to propose it? If it is already decided, ask them to describe it in
     their own words: language, frameworks, where it runs (their computer, a
     server, the cloud), and hard constraints (e.g. "no paid APIs", "all
     local", "only what is already approved at my company"). Save what they
     say exactly as they described it, without translating it into your own
     terms or completing it with tools they did not mention.
   - **Protected files**: is there finished code or files that must not be
     regenerated? If the question is not clear to them, give examples: "a
     runtime you already debugged and that works", "a configuration file
     that is already right", "a module that is already tested and you don't
     want anyone to touch". Save it as a list of paths or patterns (e.g.
     `src/runtime/`, `config/*.yaml`).
   - **Company context** (optional): if this project is for a company, are
     there business rules, constraints or conventions that DevSquad AI
     should respect? (e.g. always use a certain provider, don't use a
     certain kind of data, comply with an internal policy)

   - **Verification commands** (optional): which commands are used to check
     that the code works? (for example the linter and the tests). If the
     person doesn't know, leave it as "N/A": the Coder will propose them once
     there is a stack. Save each command as is, between backticks.

   The **Stack** and **Protected files** questions are independent of the
   technical level: always ask them, to anyone. Someone technical may still
   want the stack proposed to them, and someone non-technical may bring a
   real constraint from their company or a file that must not be touched.

3. Before continuing, confirm to the person in one sentence what you
   understood about each of those two points, and wait for them to validate
   or correct it — do not interpret silently and move on. For example: "I
   understood that your stack is Python with Ollama running locally, with no
   paid services, correct?" and "I understood that I must not touch
   `src/runtime/` or `config/settings.yaml`, correct?".

4. Create the `.devsquad/` folder if it does not exist.

5. Write `.devsquad/perfil.md` with this structure:

```markdown
# DevSquad AI Profile

- **Preferred name**: [name]
- **Technical level**: [non-technical / technical — with one sentence of context]
- **Language**: [language]
- **Stack**: [description exactly as the person gave it, including hard
  constraints — or "Undecided: the Architect proposes it"]
- **Protected files**: [list of paths or patterns that must not be modified
  or regenerated, or "N/A"]
- **Business rules / company context**: [free text, or "N/A"]

## Verification commands

They are run by the DevSquad AI hook before the Coder is allowed to finish.
One command per line, between backticks; if there are none, write `N/A`.

- Lint: `[command]`
- Tests: `[command]`

_Last updated: [date]_
```

5b. If the profile declares verification commands, tell the person that they
   **must approve them themselves** (by typing `/devsquad-ai:aprobar comandos`
   in the terminal; in the Factory the Factory approves them): they are
   commands the system will run, and without their approval they are not run.
   If they change them later, they have to be approved again.

6. Confirm to the person, in one simple sentence, that their profile was saved and that from now on DevSquad AI will adapt to how they like to work.
7. Hand control back to the Orchestrator so it continues with the project (the discovery phase with the BSA if it is a new project).
