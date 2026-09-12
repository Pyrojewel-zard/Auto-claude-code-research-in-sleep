---
name: research-write
description: Use when promoted ARIS research evidence must become an application or paper without exceeding its evidence or audit obligations.
argument-hint: "[research-workspace] — mode: proposal|paper"
allowed-tools: Bash(*), Read, Write, Edit, Grep, Glob, Skill
---

# Research writing

Write from a promoted ARIS research workspace: **$ARGUMENTS**. Its literature
evidence remains traceable to the Zotero semantic-search records. This entry is
downstream of `/autoresearch-topic` or `/autoresearch-proposal`; it never
performs a new literature search to fill a prose gap.

## Preconditions and outputs

Require `RESEARCH_STATE.json`, promoted `SYNTHESIS.md` or an explicitly
promoted branch, `OBLIGATIONS.md`, query statuses, evidence matrices, and
provenance. At least one branch must be `PROMOTABLE` or
`PROMOTABLE_WITH_OBLIGATIONS`; `NEEDS_WORK` branches are excluded.

Run `tools/research_gate.py` before drafting and again before finalization.
Pending, running, error, stale, or missing evidence blocks writing. `NO_HIT`,
`UNSEARCHABLE`, and `UNVERIFIED` entries may motivate a qualified gap but are
not load-bearing support.

Before prose, write `WRITING_CLAIMS.md`, mapping every material sentence to a
promoted branch, item key or exact evidence span, and permitted language. Write
`PROPOSAL.md` in proposal mode or `PAPER.md` in paper mode, together with
`WRITING_LIMITATIONS.md`.

Proposal mode uses future-work language (`will test`, `will determine`, `is
proposed`) for unobserved outcomes. Paper mode separates observed results from
inferred mechanisms and labels inference. Do not invent citations, numbers,
causality, superiority, or generalization.

## Freeze and audit handoff

After the pre-final gate succeeds, freeze the exact source, evidence, figures,
results, and draft into read-only `submission-freeze/` and record
`freeze_manifest.json`. Invoke `/research-audit` in frozen-artifact mode with a
fresh isolated Codex reviewer. A `BLOCK` or `REVIEW_UNAVAILABLE` result means
the document is not submission-ready; keep all obligations visible and resolve
them with typed evidence or an explicit human waiver.

```text
/research-write research/ — mode: proposal
/research-write research/ — mode: paper
```
