---
name: research-audit
description: Use when a completed research branch or frozen writing package needs an independent evidence and Anti-Autoresearch audit.
argument-hint: "[branch-or-frozen-package] — mode: branch-evidence|frozen-artifact"
allowed-tools: Bash(*), Read, Write, Edit, Grep, Glob, Skill
---

# Research audit

Audit **$ARGUMENTS** as the independent ARIS review boundary. Branch packages
must preserve their Zotero evidence provenance. A frozen artifact
means the exact immutable package sent for review. This entry has
two explicit modes:

- `branch-evidence`: a completed `BRANCH_RESEARCHED` package containing
  `QUERY_PACK.md`, `EVIDENCE_MATRIX.md`, and `COVERAGE_REPORT.md`;
- `frozen-artifact`: a read-only `submission-freeze/` containing the final
  proposal/paper and its source, results, figures, and evidence.

Never audit a mutable author package. The authoring context cannot issue its
own verdict.

## Branch evidence mode

Confirm the branch is complete, freeze query/evidence/coverage files and their
hashes, and use a fresh isolated Codex reviewer that receives only this package
and the rubric. Check claim-to-span mapping, evidence direction, verification,
counter-evidence, limitations, no-hit visibility, and item provenance. Record
findings in `EVIDENCE_AUDIT.md` and `EVIDENCE_AUDIT.json`, then pass them to
`tools/research_gate.py`:

```text
PROMOTABLE
PROMOTABLE_WITH_OBLIGATIONS
NEEDS_WORK
```

Hard findings block only the affected branch. Soft findings become visible,
append-only obligations. Do not repeatedly edit and audit solely to make flags
disappear.

## Frozen-artifact mode

Resolve the Anti engine only from `vendor/anti-autoresearch/` and
`tools/anti-autoresearch.lock.json` using
`tools/resolve_anti_autoresearch.py`. Run the vendored eval and fail closed as
`REVIEW_UNAVAILABLE` if lock, provenance, eval, or reviewer evidence is absent.
Run deterministic checks, the Anti evidence ledger/adjudicator, and the fresh
isolated Codex semantic review. Fold the result through
`tools/forensics_gate.py` while preserving `CLEAN_GIVEN_EVIDENCE`, `SOFT_FLAGS`,
`HARD_FLAGS`, and `REVIEW_UNAVAILABLE`.

`same-context` review is always blocked; `same-family-isolated` is recorded as
such. Preserve report, coverage, traces, hashes, and obligations beside the
freeze. A clean result means only `NO_NEW_BLOCKER`, never an unconditional
scientific acceptance. The writing entry is `/research-write`.
