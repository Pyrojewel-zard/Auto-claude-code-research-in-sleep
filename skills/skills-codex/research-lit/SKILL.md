---
name: research-lit
description: "Compatibility entry for topic-mode literature research."
---

# Legacy `research-lit` compatibility wrapper

This entry is retained for callers that still invoke `/research-lit`. It is a
topic-mode compatibility wrapper around the canonical Codex workflow in
`skills/skills-codex/research/SKILL.md`; it does not own a second retrieval
pipeline. Forward the topic and any supported output paths to `/research` in
topic mode and let the canonical entry own classification, Zotero retrieval,
coverage, audit, and synthesis.

## Compatibility handoff

For a legacy caller that supplies a `QUERY_PACK.md` or an
`EVIDENCE_MATRIX.md`, preserve those paths as the branch handoff. The
canonical entry must still:

1. consume `QUERY_PACK.md` and write `EVIDENCE_MATRIX.md`;
2. make one `mcp__zotero_mcp__semantic_search` call for each query, with at
   most one retry using the declared aliases;
3. retrieve item details, content, and annotations when available; and
4. keep one coverage row for every Query ID, including a `NO_HIT` row.

Every query retains a terminal status of `SEARCHED`, `NO_HIT`, `UNVERIFIED`,
`UNSEARCHABLE`, or `ERROR`. If Zotero is explicitly requested but not
configured, record `ERROR` (or `UNSEARCHABLE` for an invalid query) and report
that it is not configured; do not silently substitute another discovery
source. The evidence matrix keeps `Draft claim`, `Query ID`, `Query status`,
`itemKey`, `Matched chunk`, `supports/contradicts/limits`, and `Verification
status` fields.

Do not add a source selector or revive the former broad-source workflow here.
External expansion is controlled only by the canonical entry's explicit
post-coverage policy.
