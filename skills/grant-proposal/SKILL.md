---
name: grant-proposal
description: "Compatibility entry: research a proposal draft, then write the proposal."
---

# Legacy `grant-proposal` compatibility wrapper

Keep `/grant-proposal` as a stable compatibility entry. Read the user's
existing application draft and delegate proposal evidence work to
`skills/skills-codex/research/SKILL.md` in proposal mode, then delegate
proposal prose to `/write`:

```text
draft path -> proposal research -> promoted evidence -> /write
```

Proposal research writes `DRAFT_ANALYSIS.md`, `BRANCH_PLAN.md`, and, for each
independent branch, `QUERY_PACK.md`, `EVIDENCE_MATRIX.md`, and
`COVERAGE_REPORT.md`. The draft is not treated as one undifferentiated topic.

## Preserved query-pack/evidence-matrix contract

Before retrieval, ensure **all three artifacts exist**:
`DRAFT_ANALYSIS.md`, `QUERY_PACK.md`, and `EVIDENCE_MATRIX.md`. Initialize the
matrix with one row per Query ID and `Query status = PENDING`; use `unclear`
when no evidence direction is justified. The `query pack:` handoff is passed
to `/research`, which makes one `mcp__zotero_mcp__semantic_search` call for
each query and allows only one alias retry. Each query must end as `SEARCHED`,
`NO_HIT`, `UNVERIFIED`, `UNSEARCHABLE`, or `ERROR`.

The **Phase 1 completion gate** requires all query statuses to be terminal and
the evidence matrix to exist before novelty analysis or proposal prose. Keep
no-hit, unverified, limits, and contradictory evidence rows visible.

Only promoted research branches and their obligations may reach `/write`.
External expansion is decided explicitly by the canonical entry after Zotero
coverage; this wrapper does not silently invoke another scholarly source.
