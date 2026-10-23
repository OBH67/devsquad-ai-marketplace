---
description: "Cancel the open track, with a reason. Only the person invokes it (for example /devsquad-ai:cancelar the scope changed); the model cannot."
disable-model-invocation: true
argument-hint: "reason for the cancellation"
---

# Cancel the track (the person's decision)

The person typed this command. **You do not record the cancellation**: a
DevSquad AI hook processed it with code before this message reached you, and
its result is in the context as "HOOK RESULT".

Arguments received (the reason): $ARGUMENTS

- If the result says the track was cancelled, confirm it to the person: the
  history is kept, the single slot is free and a new track can be opened.
- If it says it was not cancelled (for example, the reason is missing), tell
  them why.
- If there is no hook result, tell them that it was **not cancelled** and
  that they can run, themselves,
  `devsquad-estado cancelar --motivo "..." --fuente terminal`.
