# Zotero-First Autoresearch with Anti-Autoresearch Audit

## Status

Design approved in principle. Implementation planning begins only after the
user approves this written specification.

## Problem

ARIS currently exposes 82 primary skills, 82 Codex variants, and reviewer
overlays. Broad orchestrators can pull unused retrieval and research
capabilities back into a small installation. The target user mainly searches a
sufficiently rich Zotero library through semantic search. The reduced product
must preserve autoresearch while using Anti-Autoresearch to stop the authoring
loop from certifying its own evidence and conclusions.

## Goals

1. Expose only research, write, and audit by default.
2. Support topic-driven research and proposal-draft decomposition through one
   research orchestrator.
3. Make Zotero semantic search the only automatic literature-discovery path.
4. Ask once before targeted external expansion unless the run was explicitly
   configured to allow or forbid it.
5. Audit completed branches without interrupting their internal iterations.
6. Keep unresolved hard findings out of synthesis and writing.
7. Run full Anti-Autoresearch on frozen paper, code, result, or submission
   artifacts.
8. Make Codex canonical and isolate reviewer context from authoring context.
9. Integrate the reviewed Anti-Autoresearch implementation into ARIS as an
   ARIS-owned vendored audit engine, behind a tested adapter and provenance
   record.
10. Defer physical catalog deletion until the reduced flow is validated.

## Non-Goals

- Preserve every existing search source in the reduced profile.
- Run full forensics after every query or branch iteration.
- Interpret a Zotero no-hit as proof that no prior work exists.
- Let an LLM issue the final integrity verdict.
- Push or maintain a separate Anti-Autoresearch repository as a runtime
  dependency; ARIS owns the integrated snapshot used by its profile.
- Preserve first-release parity with all Claude, Copilot, and reviewer overlays.
- Delete the legacy catalog before real-use validation.

## Product Surface

The default profile exposes:

- research: topic or proposal input to branch research and synthesis;
- write: promoted evidence to proposal or paper;
- audit: frozen artifacts to full Anti-Autoresearch forensics.

Topic and proposal inputs are two modes of one research entry.

Topic mode turns a theme and constraints into a research brief and independent
branches. Proposal mode extracts claims and gaps from a draft before generating
branches. Write consumes only promoted evidence. Audit handles frozen PDFs,
source directories, code, results, or combined artifact directories.

## State and Workspace

The research state progression is:

~~~
INPUT
  -> BRANCH_PLANNED
  -> ZOTERO_RESEARCHING
  -> BRANCH_RESEARCHED
  -> EVIDENCE_AUDITED
  -> PROMOTABLE | NEEDS_WORK
  -> SYNTHESIZED
  -> WRITE_READY
~~~

A branch may run multiple Zotero queries before becoming BRANCH_RESEARCHED.
Lightweight audit runs once on that completed branch snapshot. Soft findings
become append-only obligations. Hard findings affect only that branch; other
branches continue.

Each run uses:

~~~
research/
  RESEARCH_BRIEF.md
  BRANCH_PLAN.md
  RESEARCH_STATE.json
  branches/
    <branch-id>/
      QUERY_PACK.md
      EVIDENCE_MATRIX.md
      COVERAGE_REPORT.md
      EVIDENCE_AUDIT.md
      EVIDENCE_AUDIT.json
  OBLIGATIONS.md
  SYNTHESIS.md
~~~

RESEARCH_STATE.json records mode, branch states, retrieval policy, expansion
authorization, audit status, and artifact hashes. It is the compact-recovery
source of truth.

## Zotero-First Retrieval

Research automatically uses Zotero semantic search. Keyword search cannot
replace semantic search for convenience. Zotero MCP failure is reported and
never causes silent Web fallback.

Every branch query pack covers:

1. the central mechanism or research question;
2. aliases, related methods, and predecessor work;
3. counter-evidence, novelty conflicts, and close alternatives;
4. boundaries, failure cases, and limitations.

Each independent query receives one primary semantic-search call with reranking
and matched chunks. Item details, relevant content, and annotations are fetched
for the strongest deduplicated hits.

Every query ends in exactly one state:

- SEARCHED: verifiable evidence was collected;
- NO_HIT: the query and one alias retry returned no useful hit;
- UNVERIFIED: an item was found but the material claim could not be checked;
- UNSEARCHABLE: the query lacks enough semantic content;
- ERROR: the Zotero service or index failed.

No-hit and unverified rows remain in the evidence matrix. Relevance is never
treated as claim support.

## Coverage and External Expansion

Coverage is judged by claim and evidence direction, not paper count. The report
records direct support, attempted counter-evidence, limitations, full-text or
annotation verification, hypotheses, and explicit gaps.

The expansion policy is:

- ask: default; ask once after the completed coverage report;
- never: remain Zotero-only and preserve gaps as obligations;
- allow: use pre-authorized targeted expansion without pausing.

Authorized expansion targets only listed gaps through one internal
external-academic-search adapter backed by the host WebSearch/WebFetch
capability. It does not activate source-specific MCPs or helper skills. The old
source family is not installed as separate default skills. Every external
result enters the same evidence matrix with explicit source and verification
provenance.

## Lightweight Evidence Audit

Post-retrieval audit is distinct from full paper forensics. It consumes a
frozen query pack, evidence matrix, and coverage report and checks:

1. every material claim maps to evidence or an explicit hypothesis;
2. cited passages support, contradict, or limit the stated claim;
3. relevance scores were not converted into evidence;
4. novelty claims include an attempted close-work or counter-query;
5. no-hit and unverified results remain visible;
6. synthesis wording respects evidence strength;
7. item and source identifiers remain traceable.

A fresh isolated Codex reviewer receives only the frozen evidence package and
rubric. It proposes span-anchored findings. Deterministic adjudication validates
anchors, observability, false-positive risk, and severity.

Outcomes are PROMOTABLE, NEEDS_WORK, or PROMOTABLE_WITH_OBLIGATIONS. The audit
must not be rerun as an optimization target until warnings disappear.
Remediation points to changed evidence, a corrected claim, or a human waiver.

## Anti-Autoresearch Ownership

The Anti-Autoresearch project remains the provenance source and upstream
reference. ARIS vendors the reviewed implementation under
`vendor/anti-autoresearch/` and owns the integrated runtime copy. The Anti
implementation owns:

- evidence-ledger schemas and extraction;
- observability and finding contracts;
- deterministic consistency checks and adjudication;
- full frozen-artifact workflow and regression eval;
- the lightweight evidence-audit contract shared with ARIS.

ARIS owns:

- topic and proposal branch planning;
- Zotero retrieval, matrices, and coverage policy;
- external-expansion authorization;
- evidence freezing and the Anti adapter;
- branch promotion, obligations, and writing gates.

The ARIS lock records the original repository URL, exact tested commit, and
contract version as provenance. Normal runtime resolution reads the vendored
tree, runs its local eval, and invokes that snapshot without cloning or fetching
another repository. A local external checkout is permitted only as an explicit
development source for updating the vendor and must pass the same contract and
eval checks; it is never a distribution dependency.

The pre-existing untracked `skills/anti-autoresearch-bundle` is not the runtime
copy and must remain outside commits unless separately reviewed. The tracked
`vendor/anti-autoresearch/` tree is the single ARIS-integrated snapshot; its
provenance lock and import test prevent silent drift. Updating it requires
re-running the vendored eval and ARIS adapter tests.

## Codex-Primary Review

Existing Claude-to-Codex review patterns become:

1. Codex authoring freezes an evidence package;
2. a fresh Codex reviewer receives only the package and rubric;
3. reviewer output follows the finding schema;
4. deterministic code validates and adjudicates findings;
5. ARIS converts accepted findings into append-only obligations.

The active authoring conversation never issues its own final verdict. Claude
compatibility may remain thin, but reviewer overlays are absent from the
reduced default profile.

## Writing and Final Audit

Write consumes the research brief, promoted evidence matrices, synthesis, and
obligations. Proposal mode preserves future-work language. Paper mode separates
observed results from proposed or inferred claims.

Before finalization:

- citations resolve to evidence rows;
- unverified evidence is qualified or removed from load-bearing claims;
- hard obligations block finalization;
- soft obligations remain explicit but may proceed;
- a frozen submission artifact invokes full audit once.

## Packaging and Deferred Deletion

The minimal profile installs the three public entries and internal
tools/contracts. It does not install broad search skills, autonomous experiment
loops, patents, presentation flows, reviewer overlays, or the legacy
paper-writing assurance closure.

The full catalog remains available during validation and cannot be a dependency
of the reduced profile. Physical deletion requires passing end-to-end fixtures,
stable audit obligations, real-use confirmation, and a separate path-level
deletion proposal.

## Error Handling

- Missing Zotero MCP: mark queries ERROR and stop retrieval.
- Empty result: retry once with aliases, then mark NO_HIT.
- Missing content: mark the hit UNVERIFIED.
- Expansion declined: preserve gaps and qualify synthesis.
- Anti contract mismatch: stop audit and report required and detected versions.
- Reviewer failure: preserve frozen input and do not promote the branch.
- Adjudicator failure: semantic findings cannot bypass adjudication.
- One branch failure: other branches continue and synthesis records exclusion.

## Tests

Contract tests verify the profile closure, Zotero default, terminal query
states, provenance, expansion authorization, and writing gate.

Deterministic tests cover gap classification, promotion, append-only
obligations and waivers, vendored Anti resolution/provenance, and finding
validation.

Integration fixtures cover complete and incomplete Zotero searches, declined
and authorized expansion, proposal decomposition, partial branch failure,
vendored Anti resolution, and frozen-artifact full audit.

Existing selective-install tests remain green. Anti upstream eval must pass
before accepting a pin. Live Web access is never required by default.

## Delivery Sequence

1. Add the lightweight evidence-audit contract and fixtures to the Anti source.
2. Import the tested Anti release into the ARIS vendor tree and record
   provenance; no separate Anti push is required.
3. Refactor research around topic and proposal modes.
4. Replace broad retrieval with Zotero-first query and coverage contracts.
5. Add branch audit, promotion, and obligations.
6. Refactor writing to consume promoted evidence.
7. Add the full vendored Anti adapter and frozen-artifact checkpoint.
8. Add the minimal Codex-first profile and installer tests.
9. Update documentation and run end-to-end fixtures.
10. Validate real use before proposing physical deletion.

## Acceptance Criteria

- A topic reaches synthesis using only Zotero.
- A proposal becomes multiple independently auditable branches.
- Zotero gaps cause one explicit decision, never silent fallback.
- Branch autoresearch finishes before audit gating.
- Hard findings cannot silently enter writing.
- Soft findings remain visible without freezing the whole project.
- Full audit uses the tested ARIS-vendored Anti snapshot with recorded upstream
  provenance.
- Reviewer context is isolated from authoring context.
- The default installation exposes three public entries.
- Legacy workflows are outside the minimal dependency closure.
- No separate Anti repository is required at runtime or for ARIS delivery.
