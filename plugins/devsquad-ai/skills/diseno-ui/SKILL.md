---
description: Checklist and principles of visual design with real value (color, typography, layout, contrast) to use when creating the design system of a DevSquad AI project, or when implementing/reviewing code that must follow that design. For accessibility (WCAG), responsiveness, Atomic Design and UX laws, see the `estandares-frontend` skill. Always use when generating diseno.md, and when verifying contrast/legibility before delivering an app to the user.
---

# UI design with real value (DevSquad AI)

A generic design (default gray/blue, system typography, no personality) does
not meet DevSquad AI's goal. The goal is for each project to feel designed on
purpose for what it is, not like a template made without thought.

This skill covers palette, typography, contrast and states. For technical
accessibility (WCAG, ARIA, keyboard), responsive design, Atomic Design and UX
laws (Hick, Fitts), use the `estandares-frontend` skill together with this one.

## Non-negotiable principles

1. **A palette with purpose, not a default.** Define 4–6 colors with their
   exact hexadecimal value: primary, secondary, one or two accents, and the
   semantic ones (success/error/warning). Each color must have a reason tied
   to the project, not be "the usual blue".
2. **Typography with personality.** Choose one font for headings/display and
   another (or the same family with a different weight) for body text. Avoid
   the framework's default font without having decided it on purpose.
3. **Contrast verified, not assumed.** Every text/background pair must meet a
   minimum of **4.5:1** contrast (WCAG AA) for normal text, 3:1 for large
   text. Calculate or estimate this number explicitly for each combination
   you define — do not take it for granted "because it looks good on the
   screen where you designed it".
4. **A single color mode, on purpose.** Decide explicitly whether the project
   has light mode, dark mode, or both. If the base framework/template brings
   dark-mode styles by default (this already caused a real bug in a DevSquad
   AI project: dark-mode CSS inherited from the Next.js starter template,
   applied inconsistently), say so explicitly in the deliverable and ask for
   that inherited CSS to be removed or declared consistently — it cannot be
   left "half done".
5. **States, not only the happy screen.** Define how each key screen looks
   empty, loading, and with an error — not only with perfect sample data.
6. **One memorable element, the rest disciplined.** Choose one thing (an
   accent color, a shape, a micro-interaction) that gives the project
   personality, and keep everything else quiet around that element.

## Verification checklist before handing off to the Coder

- [ ] Palette with exact hex values and their purpose, not only names
      ("terracotta" without the hex is useless for implementing).
- [ ] Contrast of each text/background combination verified ≥ 4.5:1.
- [ ] Typefaces named explicitly (the real name, not "a modern font").
- [ ] Light/dark mode decided explicitly, not left to the base template.
- [ ] Each screen of the project has its empty/error state described.
- [ ] See also the accessibility and responsiveness checklist of
      `estandares-frontend`.

## Verification checklist before delivering to the user (for Orchestrator/Coder)

This section is used AFTER implementing, before telling the person "you can
try it now":

- [ ] If a browser/screenshot tool is available, take one and visually check
      that the text is legible against its background on every screen — do
      not assume that compiling without errors means it looks good.
- [ ] Confirm that no style from the base template was left unused or
      contradicting the palette defined in `diseno.md`.
