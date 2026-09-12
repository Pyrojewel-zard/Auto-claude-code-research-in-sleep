---
name: autoresearch-topic
description: Use when a topic, question, or method should be investigated through an autonomous but evidence-gated research loop.
argument-hint: "[topic or research question]"
allowed-tools: Bash(*), Read, Write, Edit, Grep, Glob, Skill
---

# Topic autoresearch

Run a complete ARIS autoresearch loop for a topic: **$ARGUMENTS**. This is the
topic-only entry. It must not infer an application draft from a vague request;
if the input points to an existing application, stop and route the user to the
proposal entry.

## Contract

Create a research workspace containing:

```text
research/
  RESEARCH_BRIEF.md
  BRANCH_PLAN.md
  RESEARCH_STATE.json
  branches/<branch-id>/
    QUERY_PACK.md
    EVIDENCE_MATRIX.md
    COVERAGE_REPORT.md
  OBLIGATIONS.md
  SYNTHESIS.md
```

The brief records the object, central question, scope, constraints, and
evidence objective. The branch plan creates independent branches, normally:
central mechanism, aliases/predecessors, counter-evidence/novelty conflicts,
and boundaries/limitations. Each branch owns its own query pack and evidence
artifacts.

## Retrieval and loop

For every query, call
`mcp__zotero_mcp__semantic_search` once with `topK: 10`, `candidateK: 50`,
`includeChunks: true`, `useRerank: true`, and `language: "all"`. An empty or
unusable result permits one declared-alias retry once. Fetch
`get_item_details`, `get_content`, and `search_annotations` for the strongest
deduplicated hits. Relevance scores are never evidence.

Every query ends as exactly one of `SEARCHED`, `NO_HIT`, `UNVERIFIED`,
`UNSEARCHABLE`, or `ERROR`; preserve every status in `EVIDENCE_MATRIX.md`.
Write the matrix and `COVERAGE_REPORT.md` before synthesis. External expansion
is `ask` by default and may occur only once after the coverage report, for named
gaps; `never` and pre-authorized `allow` remain supported. Zotero failure never
silently falls back to another scholarly source.

The branch may complete its full planning, retrieval, reading, analysis, and
internal iteration before review. After `BRANCH_RESEARCHED`, freeze the branch
inputs and hashes, then invoke `/research-audit` in branch-evidence mode with a
fresh isolated Codex reviewer. Use `tools/research_gate.py` to promote only `PROMOTABLE` or
`PROMOTABLE_WITH_OBLIGATIONS` branches. Synthesize only promoted branches.

## Handoff

Return `SYNTHESIS.md` and the complete branch packages. If prose is requested,
invoke `/research-write`; if a frozen artifact needs scrutiny, invoke
`/research-audit`. A failed branch remains visible as `NEEDS_WORK` while
independent branches continue.
