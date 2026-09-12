---
name: write
description: Use when turning an ARIS research workspace into a grant proposal or paper, or when a draft must be constrained by promoted evidence and auditable obligations.
argument-hint: "[research-workspace] — mode: proposal|paper"
allowed-tools: Bash(*), Read, Write, Edit, Grep, Glob, Skill
---

# Evidence-gated writing

Write from an ARIS research workspace: **$ARGUMENTS**.

This is the authoring stage after `/research`. It is allowed to compose prose,
but it is not allowed to turn an unresolved search result, an unverified
citation, or an audit warning into a load-bearing fact. The active Codex
context drafts; `/audit` is the independent final check.

## Contract

Required inputs:

- `RESEARCH_STATE.json` and its event/history record;
- `SYNTHESIS.md` (or a branch bundle explicitly marked for writing);
- promoted branch states: `PROMOTABLE` or
  `PROMOTABLE_WITH_OBLIGATIONS`; `NEEDS_WORK` is excluded;
- `OBLIGATIONS.md` and each obligation's current disposition;
- `EVIDENCE_MATRIX.md`, query status, and source provenance for every cited
  literature claim.

Required outputs:

- `PROPOSAL.md` for proposal mode or `PAPER.md` for paper mode;
- `WRITING_CLAIMS.md`, mapping every load-bearing sentence to a promoted
  branch and evidence span;
- `WRITING_LIMITATIONS.md`, including open soft obligations and preserved gaps;
- `submission-freeze/`, a read-only copy of the exact source, evidence,
  figures, results, and generated draft sent to `/audit`.

The authoritative state machine is `tools/research_state.py`; the branch
adapter is `tools/research_gate.py`. Use their public functions instead of
inventing a second promotion rule. Before drafting and again before finalizing,
run the gate against the current state. A failed gate is a writing stop, not a
permission to rewrite the report.

## Steps

### 1. Resolve mode and preflight evidence

Classify the request as **proposal mode** or **paper mode**. Reject an
ambiguous mode and ask once. Load state without editing it. Confirm that the
run is `SYNTHESIZED` or that an explicitly selected branch is promotion
terminal. Confirm at least one `PROMOTABLE` or
`PROMOTABLE_WITH_OBLIGATIONS` branch and exclude every `NEEDS_WORK` branch
from the synthesis input.

Run the pre-draft gate through `research_gate.py`. Fail closed when a query is
`PENDING`, `SEARCHING`, `RUNNING`, `IN_PROGRESS`, `ERROR`, or otherwise lacks a
terminal evidence status. A `NO_HIT`, `UNSEARCHABLE`, or `UNVERIFIED` result is
not evidence of support: qualify or remove the claim, or preserve it as a gap.
Never silently upgrade `UNVERIFIED` to observed evidence.

### 2. Build the claim map

Read the promoted branches and write `WRITING_CLAIMS.md` before prose. Each
row contains claim ID, exact source span/item key, branch ID, promotion state,
and the allowed language. Keep these distinctions visible:

| Evidence state | Permitted prose |
|---|---|
| promoted result or retrieved passage | state the supported observation and cite it |
| `PROMOTABLE_WITH_OBLIGATIONS` | state only the supported part and quote the open obligation in limitations |
| `NO_HIT`, `UNSEARCHABLE`, `UNVERIFIED`, or preserved gap | qualify as unknown, motivate future work, or omit |
| failed/`NEEDS_WORK` branch | do not use as load-bearing support |

Do not create citations, numbers, methods, participants, or outcomes that are
absent from the evidence matrix. A citation is usable only with an item key or
stable bibliographic identity and a recoverable passage/annotation.

### 3. Draft the selected genre

In **proposal mode**, write a case for future work: problem, gap, hypothesis,
aims, approach, feasibility, risks, milestones, and expected contribution.
Use future-work language (`will test`, `will determine`, `is proposed`) for
unobserved results. Do not present planned experiments as completed findings.

In **paper mode**, separate `observed` results from `inferred` interpretation.
Results paragraphs contain only measured or directly retrieved observations;
the Discussion may infer mechanisms, but labels the inference and carries its
assumptions. Keep unsupported novelty, causality, superiority, and generality
claims out of the title, abstract, and conclusions.

Write the draft and `WRITING_LIMITATIONS.md` together. For every
`PROMOTABLE_WITH_OBLIGATIONS` branch, state the obligation, its evidence, and
the exact prose it constrains. For preserved coverage gaps, state what was not
searched and why; do not turn a Zotero no-hit into a field-wide absence claim.

### 4. Freeze and final-gate

Run the pre-final gate again. If state, evidence, or obligations changed,
rebuild the claim map and draft. Freeze exact inputs and hashes into
`submission-freeze/` only after the gate succeeds; make the directory
read-only for the audit handoff and record `freeze_manifest.json`.

Invoke `/audit` on that frozen directory with a **fresh isolated Codex
reviewer**. The writing context never supplies the Anti verdict for its own
draft. Save the upstream report, ARIS gate result, and obligations ledger next
to the freeze. A `BLOCK` or `REVIEW_UNAVAILABLE` outcome leaves the draft
deliverable but not submission-ready; resolve or explicitly human-waive each
obligation before claiming readiness.

Completion means the genre-specific draft, claim map, limitations, freeze
manifest, and final audit handoff all exist and agree with the final state.

## Compact invocation

```text
/write research/ — mode: proposal
/write research/ — mode: paper
```

The legacy `/paper-writing` entry remains available for its historical,
multi-stage pipeline. The minimal Codex profile selects `/write`, not that
legacy route.
