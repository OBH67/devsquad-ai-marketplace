---
description: Communication and progress-visibility standards for guiding the person during a DevSquad AI project — what to say before, during and after each phase, and how to keep progress always in view. Always use when coordinating a project's flow, especially with non-technical people who can feel lost if they don't know what is happening.
---

# Communication and visible progress

A real problem detected in testing: after the initial questions, the person
stops knowing what is happening — they don't know whether an agent is
working, whether code is being written, or what step of the project they are
at. This skill exists so that never happens again.

## Main rule: keep the phases always in view

There is no task-list tool in this plugin. The project's real state lives in
`.devsquad/estado.json` and in the active track's `plan.md` (the hooks advance
them); you read it (startup pointer or Read) and tell the person in text:
show them the project's phases with their status (done, in progress, pending)
at the start, every time a phase changes and whenever they ask, and for the
build phase how many of the plan's tasks are done ("3 of 5"). The phases:

1. Understanding your idea
2. Deciding how it will be built
3. Designing how it will look
4. Preparing your computer
5. Building your app
6. Confirming everything works

Mark each one as "in progress" when it starts and "done" when it ends. This
alone solves most of the problem of feeling lost — the person can always see
where the project stands without having to ask.

## Before delegating to a specialist

Say, in one simple sentence, what is going to happen and why — never delegate
silently:
- "I'm going to hand this to whoever decides how we'll store your data, give
  me a moment."
- "Now someone on the team is going to define how your app will look."

The person does not need to know the agents' internal names (bsa, arquitecto,
etc.) if they are non-technical — describe them by their function.

## During work that takes time (especially when building code)

Don't disappear. If it will take longer than a normal message, give them a
brief update on what is being done at that moment, in simple language: "I'm
writing the screen where you'll be able to record an expense, this may take a
few minutes."

## After a specialist finishes

Summarize in one or two sentences what was achieved, before moving on to the
next phase — do not assume the person worked out the result just by seeing the
file that was generated.

## With someone technical

You can be more direct and use the agents' real names and less explanation of
why — but visible progress (the phases and the plan's completed tasks) still
always applies, for any profile.
