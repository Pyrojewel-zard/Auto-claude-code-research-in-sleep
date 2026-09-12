# Codex review guide

The reduced ARIS workflow is Codex-primary:

```text
/research -> /write -> /audit
```

The active Codex context owns orchestration and writing. Review is a separate,
fresh isolated Codex context with read-only access to frozen artifacts. The
authoring context never supplies its own Anti-Autoresearch verdict.

## Install the minimal surface

```bash
bash tools/install_aris_codex.sh /path/to/project --profile pyrojewel-research
```

This installs `research`, `write`, and `audit`; it does not select broad search,
experiment, or legacy paper-pipeline skills. The old catalog and optional
Claude/Gemini overlays remain available for unrelated workflows, but are not
part of the profile.

## Review boundary

`/research` uses Zotero semantic search as its automatic literature source and
runs a lightweight branch audit after a complete branch. `/write` accepts only
`PROMOTABLE` or `PROMOTABLE_WITH_OBLIGATIONS` evidence. `/audit` freezes the
final source/results package, resolves the Anti engine from
`vendor/anti-autoresearch/` and `tools/anti-autoresearch.lock.json`, runs the
vendored eval, and folds the report through `tools/forensics_gate.py`.

The gate preserves `CLEAN_GIVEN_EVIDENCE`, `SOFT_FLAGS`, `HARD_FLAGS`, and
`REVIEW_UNAVAILABLE` verbatim. A same-family isolated reviewer is labeled
`same-family-isolated`; a same-context reviewer is `same-context` and blocks.

## Optional cross-family review

If a separate Claude reviewer is required by a venue or local policy, use the
existing `skills-codex-claude-review` overlay as an explicit add-on and record
its provenance. It is not needed for the default ARIS profile and must not be
used to bypass the frozen-artifact gate.
