# UI Design System

Version 1.1

---

# Philosophy

Simple.

Modern.

Minimal.

Sports-first.

Fast.

---

# Typography

Headings

Bold

Body

Regular

Small Labels

Medium

---

# Spacing

4

8

12

16

24

32

48

64

Use an 8-point spacing system.

---

# Buttons

Primary

Filled

Secondary

Outlined

Danger

Red

Disabled

Gray

Loading

Spinner

---

# Cards

Rounded Corners

Subtle Shadow

16px Padding

Hover State

---

# Tables

Alternating Row Colors

Sticky Headers

Sortable Columns

Responsive

---

# Forms

Large Inputs

Clear Labels

Validation Below Input

Required Fields Marked

---

# Animations

Maximum 200ms

No bouncing

No flashy effects

Fade

Slide

Only where appropriate

---

# Mobile

Touch Targets

Minimum 44px

Sticky Bottom Save Button

Single Column Layout

The picks save action is sticky on mobile and returns to the normal action row at the tablet breakpoint. Game cards must not overflow at a 390px viewport width.

---

# Implemented Visual Tokens

Primary: deep navy `#0b1f3a`

Accent: field green `#1f8f63`

Sky: interactive blue `#2f9fd0`

Gold: confidence highlight `#d99a2b`

Danger: red `#c83c4a`

Background: light gray `#eef2f3`

Team abbreviations render as deterministic team-colored badges through the shared `TeamLogo` component. The component accepts an optional image source for approved final artwork; image URLs must not be scattered through page components.

All interactive controls use a minimum 44px height. Selected choices use both color and state styling (`aria-pressed` or `aria-selected`) so color is never the only signal. Reduced-motion users receive minimal transitions.
