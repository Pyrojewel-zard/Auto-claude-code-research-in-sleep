---
name: research
description: "Public compatibility entry for the canonical Codex research workflow."
---

# `/research` public entry

This is the thin Claude-compatible public entry for the canonical Codex
workflow at `skills/skills-codex/research/SKILL.md`. Forward `$ARGUMENTS`
unchanged and follow that file; it supports both **topic mode** and **proposal
mode**. Proposal mode reads an existing application draft and produces
`DRAFT_ANALYSIS.md`, `BRANCH_PLAN.md`, and per-branch
`QUERY_PACK.md`/`EVIDENCE_MATRIX.md`/`COVERAGE_REPORT.md`.

Do not implement a second search flow here. The canonical entry owns the
Zotero semantic-search contract, terminal query statuses, coverage policy,
branch audit, promotion gate, and synthesis handoff.
