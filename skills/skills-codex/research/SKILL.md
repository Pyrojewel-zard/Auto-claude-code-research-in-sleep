---
name: research
description: Use when researching a topic or proposal draft with Zotero semantic search and ARIS branch gates.
---

# Canonical Codex Research Entry

Research request: `$ARGUMENTS`

This is the single canonical research workflow for the reduced ARIS profile.
It supports exactly two modes: **topic mode** and **proposal mode**. Zotero
semantic retrieval is the only automatic scholarly discovery path. This
document is the source of truth for the public `/research` entry and for the
legacy `research-lit` and `grant-proposal` compatibility wrappers.

## Outputs and recovery state

Write outputs under the research workspace, normally `research/`:

```text
research/
  RESEARCH_BRIEF.md
  BRANCH_PLAN.md
  RESEARCH_STATE.json
  DRAFT_ANALYSIS.md                 # proposal mode
  branches/<branch-id>/
    QUERY_PACK.md
    EVIDENCE_MATRIX.md
    COVERAGE_REPORT.md
    EVIDENCE_AUDIT.md
    EVIDENCE_AUDIT.json
  OBLIGATIONS.md
  SYNTHESIS.md
```

`RESEARCH_STATE.json` is the recovery source of truth. Record the selected
mode, input path, branch states, query statuses, external-expansion policy,
artifact hashes, audit state, promotion state, and excluded branches. Do not
write `SYNTHESIS.md` until branch gates have passed.

## Canonical flow

Execute this order for both modes:

```text
classify input mode
  -> write RESEARCH_BRIEF.md
  -> create independent branches
  -> write one QUERY_PACK.md per branch
  -> run Zotero semantic retrieval per query
  -> fetch item details/content/annotations
  -> write EVIDENCE_MATRIX.md and COVERAGE_REPORT.md
  -> decide explicit external expansion for listed gaps
  -> finish branch autoresearch and mark BRANCH_RESEARCHED
  -> freeze the branch package
  -> run the fresh-context lightweight evidence audit
  -> run research_state.py and research_gate.py
  -> synthesize promoted branches into SYNTHESIS.md
```

The order is a safety contract. In particular, a branch may run a complete
autoresearch loop before gating, but it is not audited or promoted during an
unfinished loop. A failed branch remains `NEEDS_WORK` and is excluded from
`SYNTHESIS.md`; other independent branches may continue.

## 1. Classify the input

### Topic mode

Use topic mode when the request is a research topic, question, or method and
does not point to an existing application draft. Extract the object, central
question, scope, constraints, and desired evidence into
`RESEARCH_BRIEF.md`. Do not invent proposal claims or read a nonexistent
draft.

### Proposal mode

Use proposal mode when the request supplies a path to an existing grant or
application draft. Read that draft before planning research. Write
`DRAFT_ANALYSIS.md` with:

- research object and context;
- central problem and hypotheses;
- draft claims, aims, variables, data, and evaluation;
- claimed novelty and competing-work assertions; and
- unsupported, citation-sensitive, or counter-evidence-sensitive claims.

Then write `RESEARCH_BRIEF.md` for the proposal's evidence objective and
`BRANCH_PLAN.md` with genuinely independent branches. Typical branches split
the phenomenon/mechanism, closest methods and predecessors, counter-evidence
and novelty, and boundaries or failure cases. Each branch must have a clear
question, non-overlapping scope, and an accountable output package.

If the draft path is missing or unreadable, stop proposal retrieval, record the
input error in `RESEARCH_STATE.json`, and do not silently treat the request as
topic mode.

## 2. Independent branches and query packs

Branches are independent research units. Give each branch its own directory
and query pack. A branch can perform its full autoresearch loop—planning,
retrieval, reading, analysis, and internal iteration—without an audit on every
iteration. The audit starts only after the branch has completed its declared
research work.

Every branch query pack covers four query families:

1. **Central mechanism** — the phenomenon, mechanism, or core research
   question the branch must explain.
2. **Aliases and predecessors** — naming variants, related methods, and
   predecessor work that could be missed by one formulation.
3. **Counter-evidence and novelty conflicts** — close alternatives,
   contradictory findings, competing work, and evidence that would weaken the
   draft claim.
4. **Boundaries and limitations** — failure cases, scope conditions,
   negative evidence, and known limitations.

Each query record contains at least:

```text
QID
Draft claim (or branch claim)
Research question
Query
Aliases
Evidence sought
Counter-evidence target
Source scope: Zotero semantic index
Query status: PENDING
```

Do not merge independent claims merely to reduce the number of searches. A
query with no semantic content is `UNSEARCHABLE`, not a broad topic query.

## 3. Zotero-first retrieval contract

Zotero is automatic. Keyword search, local file scanning, broader web search,
and other scholarly databases cannot replace the semantic-search call. If the
Zotero MCP is unavailable or its index fails, record `ERROR` for affected
queries, preserve the query rows, and report the configuration/index failure;
do not claim a fallback search occurred.

For **each query**, make exactly one primary call to
`mcp__zotero_mcp__semantic_search` with the natural-language query, reranking,
and matched chunks enabled. The call shape is:

```json
mcp__zotero_mcp__semantic_search({
  "query": "<QUERY record query>",
  "topK": 10,
  "candidateK": 50,
  "includeChunks": true,
  "useRerank": true,
  "language": "all"
})
```

An empty or unusable primary result permits **one alias retry once** using the
declared aliases. There is no second alias round and no silent keyword
substitution. If that retry is empty, retain the query and record `NO_HIT`.

For the strongest deduplicated hits, retrieve:

- `get_item_details` for bibliographic identity and item key;
- `get_content` for the matched passage or full text; and
- `search_annotations` for user highlights, notes, and annotations.

Record the exact `itemKey`, paper metadata, matched chunk or annotation,
evidence direction, and verification state. A relevance score is not evidence
support. If content cannot verify a material claim, keep the hit as
`UNVERIFIED` rather than upgrading it from relevance.

Every query ends in exactly one terminal status:

| Status | Meaning |
|---|---|
| `SEARCHED` | Verifiable evidence was collected and recorded. |
| `NO_HIT` | The primary query and its one alias retry found no useful hit. |
| `UNVERIFIED` | An item was found, but the material passage could not be checked. |
| `UNSEARCHABLE` | The query lacks enough semantic content to run responsibly. |
| `ERROR` | Zotero service, MCP, or semantic index failed. |

Keep `NO_HIT`, `UNVERIFIED`, `UNSEARCHABLE`, and `ERROR` rows in the evidence
matrix. They are auditable coverage results, not successes and not proof that
the literature is empty.

## 4. Evidence matrix and coverage

Write each branch's `EVIDENCE_MATRIX.md` before any synthesis, novelty
positioning, or proposal prose. It has one coverage row for every Query ID,
plus evidence rows when passages are retrieved:

```markdown
| Query ID | Draft claim | Query status | itemKey | Paper | Matched chunk | Evidence direction | Verification status | Proposal use |
|---|---|---|---|---|---|---|---|---|
```

`Evidence direction` must remain one of `supports`, `contradicts`, `limits`,
or `unclear`. Keep `UNVERIFIED` and `VERIFY_PENDING` visible and explain what
is still missing. The matrix must distinguish a direct passage, a limitation,
an attempted counter-query, a hypothesis, and an unresolved gap.

After the matrix, write `COVERAGE_REPORT.md`. Judge coverage by claim and
evidence direction, not paper count. For every branch, list:

- covered claims and their item/chunk or annotation anchors;
- attempted counter-evidence and close-work queries;
- limitations and scope conditions;
- unresolved or unsearchable queries; and
- explicit gaps that may need external expansion.

The coverage report is the decision boundary for any external search. No
external search is considered before this report exists.

## 5. External expansion policy (after Zotero coverage only)

The default is `external_expansion: ask`. It is a single explicit decision
after the completed Zotero evidence matrix and `COVERAGE_REPORT.md`, and it may
refer only to gaps named in that report:

- `ask` — ask the user once whether to expand the listed gaps. A decline keeps
  the run Zotero-only and records the gaps as obligations.
- `never` — never invoke an external search; preserve every gap and continue
  with qualified coverage.
- `allow` — use pre-authorized, targeted external search only for the listed
  gaps, recording source and verification provenance in the same matrix.

Only after the coverage report and an explicit `ask` approval, or an explicit
`allow` policy, may the workflow call `WebSearch`. It must never silently
invoke WebSearch, broaden a query, or turn external results into support
without passage-level verification. External expansion is an exception for
declared gaps; Zotero remains the only automatic scholarly discovery source.

## 6. Finish, freeze, audit, and promote each branch

When a branch's autoresearch loop is complete, write all query terminal
statuses and final `EVIDENCE_MATRIX.md`/`COVERAGE_REPORT.md`, then use
`tools/research_state.py` to transition the branch to `BRANCH_RESEARCHED`.
That transition is allowed only when the branch package is complete and every
query has one of the five terminal statuses above.

Immediately after `BRANCH_RESEARCHED`, freeze the query pack, evidence matrix,
coverage report, and their artifact hashes. The branch audit is therefore
**after `BRANCH_RESEARCHED`**, never before it and never during autoresearch.

Run a lightweight evidence audit over that frozen package in a fresh isolated Codex
reviewer context. Use an isolated `spawn_agent`/reviewer invocation with
only the frozen branch files and the audit rubric; do not pass the active
author's transcript, hidden notes, or mutable workspace. The active author
cannot self-audit or issue its own audit verdict. The reviewer checks claim
anchors, evidence direction, verification, counter-evidence, and provenance.

After the lightweight audit package is frozen, invoke the Anti full audit
through `/audit` in that fresh reviewer context. Preserve `EVIDENCE_AUDIT.md`
and `EVIDENCE_AUDIT.json`, including failure information; a reviewer failure
does not become a clean result.

Use `tools/research_gate.py` on the completed audit report after the
`research_state.py` transition and before synthesis. The gate maps the audit
to `PROMOTABLE`, `PROMOTABLE_WITH_OBLIGATIONS`, or `NEEDS_WORK`. Write
branch-local `OBLIGATIONS.md` entries for soft findings. A hard finding,
missing audit, stale artifact hash, or gate error leaves the branch
`NEEDS_WORK` and excludes it from `SYNTHESIS.md`; it must not be silently
repaired by synthesis.

## 7. Synthesis

Only after every included branch has passed `research_state.py` and
`research_gate.py` may the orchestrator write `SYNTHESIS.md`. Include only
`PROMOTABLE` and `PROMOTABLE_WITH_OBLIGATIONS` branches, cite their matrix
rows, qualify unverified evidence, and list obligations and excluded
`NEEDS_WORK` branches. Do not turn a relevance score, `NO_HIT`, or an
unverified item into a load-bearing claim.

For proposal mode, `/write` consumes this promoted synthesis and obligations;
the research entry does not bypass the writing gate. For topic mode, return
the same evidence-backed synthesis and preserve the branch packages for later
writing or review.

## Failure and recovery rules

- Missing proposal draft: stop proposal mode and record the error.
- Missing Zotero MCP/index: mark queries `ERROR` and stop retrieval.
- Empty semantic result: perform one alias retry, then `NO_HIT`.
- Missing content or annotation: retain the item as `UNVERIFIED`.
- Declined or forbidden expansion: preserve gaps and obligations.
- Incomplete branch: do not mark `BRANCH_RESEARCHED`.
- Audit/reviewer/gate failure: preserve frozen artifacts and leave
  `NEEDS_WORK`.
- One branch failure: continue independent branches, but exclude the failed
  branch from synthesis and report it.
