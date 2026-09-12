---
name: audit
description: Use when a frozen ARIS research, proposal, paper, code, or results package needs an independent Anti-Autoresearch forensic audit before delivery.
argument-hint: "[frozen-artifact-directory]"
allowed-tools: Bash(*), Read, Write, Edit, Grep, Glob, Skill
---

# Full Anti-Autoresearch audit

Audit the frozen artifact directory: **$ARGUMENTS**.

This entry is the ARIS integration boundary for Anti-Autoresearch. The engine
is tracked inside ARIS at `vendor/anti-autoresearch/`; the standalone Anti
checkout is provenance only and is not a runtime dependency. The audit context
reads the frozen package and writes reports beside it; it does not revise the
author's draft to make a detector quiet.

## Preconditions

- The target is a completed `submission-freeze/` or an explicitly frozen
  research branch. If source, PDF, figures, results, or claims are still
  changing, stop and ask the author to freeze them first.
- Resolve the engine with `tools/resolve_anti_autoresearch.py`. Normal
  resolution is offline and must report `source_kind: vendored`, the exact
  `commit` from `tools/anti-autoresearch.lock.json`, and the ARIS vendor path.
- Run the vendored `eval/run_eval.py` and require its contract gate before a
  verdict. A missing, malformed, or failed lock/eval is `REVIEW_UNAVAILABLE`.

## Audit steps

1. Record the freeze manifest and all input hashes. Build Anti's artifact and
   claims ledgers from the frozen directory.
2. Run the vendored Anti workflow, including deterministic checks,
   evidence-coverage accounting, independent semantic dimensions, and the
   deterministic adjudicator. Preserve `report.json`, `REPORT.md`, coverage,
   and traces verbatim.
3. Use a **fresh isolated Codex reviewer** context for semantic review. The
   reviewer is read-only with respect to the frozen artifact and must not
   inherit the active author conversation. Never use an in-context follow-up
   as if it were independent; `same-context` is fail closed.
4. Fold the report through `tools/forensics_gate.py` in one atomic call:

   ```bash
   python3 tools/forensics_gate.py evaluate \
     --report FROZEN/report.json --paper-dir FROZEN \
     --anti-ar-commit LOCKED_SHA --executor-model codex \
     --reviewer-model codex
   ```

   The gate preserves Anti's verdict tokens. `HARD_FLAGS` and
   `REVIEW_UNAVAILABLE` map to `BLOCK`; `SOFT_FLAGS` maps to `WARN`;
   `CLEAN_GIVEN_EVIDENCE` maps only to `NO_NEW_BLOCKER`. Findings are
   append-only obligations in `OBLIGATIONS.md`/the ARIS ledger.
5. If the result is `BLOCK` or `WARN`, report each obligation with its exact
   span and disposition. Close only through typed, hashed evidence and a
   verifier, or record a human waiver. Do not run an edit–re-audit loop whose
   only objective is to remove flags.

## Completion contract

The audit is complete only when the vendored source and lock are recorded,
the frozen-input hashes match, the upstream report and ARIS gate exist, the
review provenance says `cross-family`, `same-family-isolated`, or an explicit
blocked state, and open obligations are visible. An unavailable reviewer is
an honest blocked result, never a clean result.

