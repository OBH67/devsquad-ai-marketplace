---
description: Frontend technical standards for DevSquad AI — accessibility (WCAG), responsive design, design systems and Atomic Design, visual hierarchy, interaction feedback, performance, and UX laws (Hick, Fitts). Always use when the Designer defines the design system or the Coder implements interfaces.
---

# Frontend standards (DevSquad AI)

## Before implementing or designing an interface

Consult (with WebSearch if needed) the current official documentation of the
chosen frontend framework (React, Next.js, Angular, or another) and of any UI
library in use — conventions and APIs change between major versions; do not
assume that what you know from memory is still current.

## Accessibility (WCAG) — non-negotiable

- **Semantic HTML**: use the tags that match their function (`button` for
  actions, `nav` for navigation, headings in hierarchical order), not generic
  `div`s with JavaScript on top.
- **ARIA roles and attributes** where semantic HTML is not enough (e.g.
  custom components such as modal, tabs, dropdown).
- **Full keyboard navigation**: every clickable element must be reachable and
  operable with Tab/Enter/Space, with visible focus at all times.
- **Minimum contrast 4.5:1** — already defined in the `diseno-ui` skill; this
  skill inherits it, it does not repeat it.

## Responsive design

- Define standard breakpoints (mobile, tablet, desktop) and verify that the
  layout does not break at any of them — not only that it looks good on the
  screen where it was designed or implemented.

## Design systems and Atomic Design

- Organize the UI components in reusable levels (atoms: button, input;
  molecules: a field with label and error; organisms: a complete form)
  instead of duplicating styles and structure screen by screen. This reduces
  inconsistency and makes it easy to keep the palette and typography the
  Designer defined in a single place.

## Visual hierarchy and feedback

- Guide attention with contrast, size and spacing (padding/margins) — not
  everything on the screen can weigh the same.
- Give immediate feedback to any interaction: visible loading, success and
  error states, never a button that "does nothing" while it processes.

## Frontend performance

- Avoid loading unnecessary resources (unoptimized images, entire libraries
  when only one function is used); use the optimization tools the chosen
  framework already brings (lazy loading, code splitting) when the project
  justifies it.

## UX laws applied

- **Hick's Law**: fewer options visible at once reduce cognitive load — if a
  screen has many possible actions, prioritize and hide the secondary ones
  instead of showing them all with the same weight.
- **Fitts's Law**: important interactive elements (a screen's main button)
  should be large and close to where the user already has their attention or
  cursor — not small or far from the natural flow of the task.

## With someone non-technical

Do not use these names (WCAG, Atomic Design, Hick's Law) when talking to the
person — they are internal quality criteria, not something they should
decide. If any of this affects a decision that is theirs (e.g. "this screen
has too many options, which are the 3 most important ones?"), translate it
into a simple question.
