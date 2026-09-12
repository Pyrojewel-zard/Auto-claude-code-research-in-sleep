---
name: integrity-forensics
description: Use when a historical Codex integrity-forensics request must be migrated to the full independent Anti-Autoresearch audit.
argument-hint: "[frozen-artifact-directory]"
allowed-tools: Bash(*), Read, Write, Edit, Grep, Glob, Skill
---

# Integrity-forensics compatibility entry

New work uses `/audit`, whose canonical contract is
`skills/skills-codex/audit/SKILL.md`. It runs the ARIS-vendored
Anti-Autoresearch engine through `tools/resolve_anti_autoresearch.py`, sends
the frozen package to a fresh isolated Codex reviewer, and folds the report
through `tools/forensics_gate.py`.

This legacy name no longer owns a separate clone, commit, or deterministic-only
shortcut. Migrate the target to a frozen artifact directory and invoke
`/audit`; preserve `REVIEW_UNAVAILABLE`, `HARD_FLAGS`, `SOFT_FLAGS`, and
`CLEAN_GIVEN_EVIDENCE` verbatim.
