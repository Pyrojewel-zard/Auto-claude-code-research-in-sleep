---
name: research-lit
description: "Compatibility entry for topic-mode literature research."
---

# Legacy `research-lit` compatibility wrapper

`/research-lit` is preserved as a topic-mode compatibility wrapper. Forward
the request to the canonical Codex research entry at
`skills/skills-codex/research/SKILL.md` using topic mode. The canonical entry
is the only owner of the Zotero-first workflow; this wrapper must not restore
the former broad-source defaults.

When a legacy caller supplies `QUERY_PACK.md` or `EVIDENCE_MATRIX.md`, pass
those paths through as the branch handoff. The handoff still requires one
`mcp__zotero_mcp__semantic_search` call **for each query**, plus at most one
alias retry, item details/content/annotations, and one coverage row for every Query ID. Keep `DRAFT_ANALYSIS.md` only when the caller already supplied it;
proposal decomposition belongs to proposal mode.

The query contract retains terminal statuses `SEARCHED`, `NO_HIT`,
`UNVERIFIED`, `UNSEARCHABLE`, and `ERROR`. Keep no-hit rows and an evidence
matrix with `Draft claim`, `Query ID`, `Query status`, `itemKey`, `Matched chunk`, `supports/contradicts/limits`, and `Verification status`. If Zotero is
explicitly requested but not configured, record `ERROR` (or
`UNSEARCHABLE` where appropriate), report that it is not configured, and do
not silently substitute another discovery source.

Use the canonical entry's explicit post-coverage external-expansion decision
if a gap needs broader search. This wrapper does not invoke any other source
by default.
