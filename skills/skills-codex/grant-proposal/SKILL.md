---
name: grant-proposal
description: "Compatibility entry: research a proposal draft, then write the proposal."
---

# Legacy `grant-proposal` compatibility wrapper

This entry keeps the proposal-writing command stable while moving proposal
research to the canonical Codex entry:

```text
existing application draft
  -> /research proposal mode
  -> promoted branch evidence
  -> /write proposal mode
```

Proposal mode reads the existing application draft. It writes
`DRAFT_ANALYSIS.md` and `BRANCH_PLAN.md`, then gives every independent branch
its own `QUERY_PACK.md`, `EVIDENCE_MATRIX.md`, and `COVERAGE_REPORT.md` before
the `/write` handoff. Do not collapse the draft into one topic query.

## Preserved query-pack/evidence-matrix contract

Before retrieval, ensure **all three artifacts exist**:
`DRAFT_ANALYSIS.md`, `QUERY_PACK.md`, and `EVIDENCE_MATRIX.md`. Initialize the
matrix with one row per Query ID and `Query status = PENDING`; retain
`unclear` evidence direction until evidence is actually verified. The
`query pack:` handoff is consumed by `/research`, which performs one
`mcp__zotero_mcp__semantic_search` call for each query and permits only one
alias retry. Every query ends in `SEARCHED`, `NO_HIT`, `UNVERIFIED`,
`UNSEARCHABLE`, or `ERROR`.

The **Phase 1 completion gate** requires a completed evidence matrix and
terminal query statuses before any proposal positioning, novelty claim, or
prose drafting. No-hit, unverified, and contradictory rows remain visible.

After branch research, audit, and promotion, invoke `/write` with only
promoted branches and explicit obligations. This wrapper has no automatic
external scholarly source policy; any expansion decision is made explicitly
by the canonical research workflow after Zotero coverage.
