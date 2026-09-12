---
name: write
description: Use when writing from an ARIS research workspace and the user wants proposal or paper prose constrained by promoted evidence.
argument-hint: "[research-workspace] — mode: proposal|paper"
---

# Write

This Claude-compatible entry points to the Codex canonical contract at
`skills/skills-codex/write/SKILL.md`. Follow that file for proposal mode,
paper mode, promoted-only evidence, `OBLIGATIONS.md`, `UNVERIFIED` handling,
freeze, and the final `/audit` handoff.

Use `/write <research-workspace> — mode: proposal` for an application and
`/write <research-workspace> — mode: paper` for an article. If the workspace
has no promotion-terminal branch, return to `/research` rather than drafting
load-bearing claims.
