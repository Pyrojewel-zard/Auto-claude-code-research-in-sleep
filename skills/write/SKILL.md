---
name: write
description: Use when writing from an ARIS research workspace and the user wants proposal or paper prose constrained by promoted evidence.
argument-hint: "[research-workspace] — mode: proposal|paper"
---

# `/write` compatibility entry

This legacy Claude-compatible entry points to the compatibility router at
`skills/skills-codex/write/SKILL.md`. The default public writing entry is
`/research-write`; follow its canonical contract for proposal mode,
paper mode, promoted-only evidence, `OBLIGATIONS.md`, `UNVERIFIED` handling,
freeze, and the final `/research-audit` handoff.

Use `/research-write <research-workspace> — mode: proposal` for an application
and `/research-write <research-workspace> — mode: paper` for an article. If the workspace
has no promotion-terminal branch, return to `/autoresearch-topic` or
`/autoresearch-proposal` rather than drafting
load-bearing claims.
