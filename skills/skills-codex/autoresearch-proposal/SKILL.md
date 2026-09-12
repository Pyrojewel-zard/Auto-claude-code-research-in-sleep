---
name: autoresearch-proposal
description: Use when an existing grant or project application draft must be decomposed into independently researched and audited evidence branches.
argument-hint: "[application-draft] — grant: NSFC|NSF|generic"
allowed-tools: Bash(*), Read, Write, Edit, Grep, Glob, Skill
---

# Proposal autoresearch

Run ARIS autoresearch from an existing application draft: **$ARGUMENTS**. This
is a separate proposal entry, not a topic alias. It must read the supplied
draft before creating research queries. If the draft path is missing or
unreadable, record the input error in `RESEARCH_STATE.json` and stop; do not
silently switch to topic mode.

## Draft decomposition

First create:

```text
research/
  DRAFT_ANALYSIS.md
  RESEARCH_BRIEF.md
  BRANCH_PLAN.md
  RESEARCH_STATE.json
```

`DRAFT_ANALYSIS.md` extracts the research object, central problem, hypotheses,
aims, variables, methods, evaluation, claimed novelty, closest-work claims,
and every unsupported or citation-sensitive assertion. `RESEARCH_BRIEF.md`
turns those claims and gaps into evidence objectives. `BRANCH_PLAN.md` creates
non-overlapping, independently auditable branches; normally one each for the
central mechanism, aliases/predecessors, counter-evidence and novelty
conflicts, and boundaries/limitations.

## Per-branch autoresearch

Each branch contains `QUERY_PACK.md`, `EVIDENCE_MATRIX.md`, and
`COVERAGE_REPORT.md`. Every query records a claim, research question, natural
language query, aliases, evidence sought, counter-evidence target, and status.
Call `mcp__zotero_mcp__semantic_search` once per query with reranking and
matched chunks enabled; permit only one alias retry. Retrieve item details,
content, and annotations for strong hits. Preserve terminal status
`SEARCHED`, `NO_HIT`, `UNVERIFIED`, `UNSEARCHABLE`, or `ERROR`; no-hit and
unverified results are gaps, never support.

Complete the full autoresearch loop for a branch before auditing it. After
`BRANCH_RESEARCHED`, freeze the query/evidence/coverage package and invoke
`/research-audit` in branch-evidence mode using a fresh isolated Codex
reviewer. Hard findings keep that branch out of synthesis; soft findings become
append-only obligations. Other branches continue. Only promoted branches may
produce `SYNTHESIS.md`.

External retrieval is not an automatic fallback. The default policy is
`external_expansion: ask`, asked once after the completed Zotero coverage
report, and limited to its named gaps. `never` preserves gaps; `allow` requires
pre-authorization and records provenance.

## Handoff

The proposal research package contains `DRAFT_ANALYSIS.md`, the branch
artifacts, `OBLIGATIONS.md`, and promoted `SYNTHESIS.md`. Invoke
`/research-write` only after promotion. The writing entry must preserve future
work language for unobserved proposal outcomes and cannot treat a planned
result as completed evidence.
