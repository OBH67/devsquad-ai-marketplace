---
description: "Human approval of the architecture, the design, the verification commands or the closing of a track. Only the person invokes it (for example /devsquad-ai:aprobar arquitectura); the model cannot."
disable-model-invocation: true
argument-hint: "arquitectura | diseno | comandos | cierre"
---

# Approve (the person's decision)

The person typed this command. **You do not record the approval**: a
DevSquad AI hook processed it with code before this message reached you, and
its result is in the context as "HOOK RESULT".

Arguments received: $ARGUMENTS

- If the context carries the hook's result, tell the person in your own words
  (what was approved and where the track ended up) and carry on with the next
  step from the startup pointer.
- If the result says it **was not recorded**, explain the reason as it is and
  what is missing (for example "`arquitectura.md` is missing").
- If there is no hook result, tell the person that it **was not recorded** and
  that they can run, themselves, in their terminal,
  `devsquad-estado aprobar <object> --fuente terminal`. Never say it was
  approved if you did not see the hook's result.

Objects: `arquitectura` and `diseno` (the documents as they are now; if they
change afterwards, they must be approved again), `comandos` (the profile's
verification commands), `cierre` (the track's closing, tied to the exact
commit).
