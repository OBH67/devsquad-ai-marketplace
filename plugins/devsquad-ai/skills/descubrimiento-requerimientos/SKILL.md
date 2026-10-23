---
description: Good practices for gathering quality requirements and user stories (INVEST criteria, MoSCoW-style prioritization, a bank of discovery questions) in DevSquad AI projects. Always use when turning an idea into requirements, before handing the work to the architect.
---

# Quality requirements discovery

## Criteria of a good user story (INVEST)

Use this as an internal checklist — do not show these initials to the person,
translate them into natural questions:

- **Independent**: can this functionality be built without depending on
  another one being ready first? If not, say so explicitly.
- **Negotiable**: do not write it as a rigid specification; leave room for
  the architect to decide the how.
- **Valuable**: what does the person gain from this? If you cannot answer in
  one sentence, context is probably missing — ask more.
- **Estimable**: it must be clear how big it is (small/medium/large by eye,
  not in hours).
- **Small**: if a story sounds like a "complete project", split it into
  several.
- **Testable**: it must be clear how someone would know it already works.

## Prioritization (v1 vs. future)

Classify each story into one of these categories, and be explicit about why
something is not v1:
- **Must be in v1**: without this, the app does not meet its minimum purpose.
- **Should be there, but can wait**: improves the experience, not critical
  for the first use.
- **Could be in the future**: a valid idea, but distant.
- **Not for now**: out of scope by decision, not by oversight.

## Bank of discovery questions

Use them as a starting point, adapted to each idea, one at a time:
- Who is going to use this? Anyone else besides you?
- What is the minimum it has to do to already be useful to you?
- How do you solve this today, without the app? (it reveals the real problem)
- Is there something similar you already know or use, as a reference?
- What would happen if this didn't exist — how bad would it be?
- Are there constraints you already know about? (time, budget, who else is
  involved)

## Definition of "done" for the deliverable

`.devsquad/requerimientos.md` is not complete if:
- Any story does not make the "what for" (the benefit) clear.
- There is not at least one explicit separation between v1 and future.
- An ambiguity was left without being marked as an open question.
