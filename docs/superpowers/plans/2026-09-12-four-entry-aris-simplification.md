# Four-Entry ARIS Simplification Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Restore four independent public ARIS entries for topic autoresearch, proposal autoresearch, evidence-gated writing, and Anti-Autoresearch review while keeping the default surface small and upstream adoption reviewable.

**Architecture:** Keep the existing state, Zotero, evidence, promotion, and vendored Anti helpers as shared internals. Split the public contracts into `autoresearch-topic`, `autoresearch-proposal`, `research-write`, and `research-audit`; retain `research`, `write`, and `audit` only as compatibility wrappers. Add a deterministic upstream-flow review report that prevents new upstream behavior from silently entering the default profile.

**Tech Stack:** Markdown agent skills, POSIX shell/PowerShell installers, Python 3 standard library, JSON, pytest/unittest-compatible tests.

**Spec:** `docs/superpowers/specs/2026-09-08-zotero-first-autoresearch-anti-audit-design.md`

## Global Constraints

- The default profile installs exactly `autoresearch-topic`, `autoresearch-proposal`, `research-write`, and `research-audit`.
- Topic and proposal autoresearch are separate public contracts even though they share internal tools.
- Automatic scholarly discovery uses Zotero semantic search; external expansion remains explicit and gap-scoped.
- A branch completes its autoresearch loop before the branch evidence audit and promotion gate.
- The active authoring context never issues its own audit verdict.
- Anti-Autoresearch runs from the ARIS-owned `vendor/anti-autoresearch/` snapshot; the standalone checkout is not a runtime dependency.
- Existing legacy catalog entries remain available but are outside the default profile and are not physically deleted in this change.
- Upstream flow changes are reviewed before adoption and cannot silently enlarge the default profile.
- Preserve untracked `task_plan.md`, `findings.md`, `progress.md`, and `skills/anti-autoresearch-bundle/` outside implementation commits.

### Task 1: Add Four Canonical Entry Contracts

**Files:**
- Create: `skills/skills-codex/autoresearch-topic/SKILL.md`
- Create: `skills/skills-codex/autoresearch-proposal/SKILL.md`
- Create: `skills/skills-codex/research-write/SKILL.md`
- Create: `skills/skills-codex/research-audit/SKILL.md`
- Create: `skills/autoresearch-topic/SKILL.md`
- Create: `skills/autoresearch-proposal/SKILL.md`
- Create: `skills/research-write/SKILL.md`
- Create: `skills/research-audit/SKILL.md`
- Modify: `skills/skills-codex/research/SKILL.md`, `skills/skills-codex/write/SKILL.md`, `skills/skills-codex/audit/SKILL.md`
- Modify: `skills/research/SKILL.md`, `skills/write/SKILL.md`, `skills/audit/SKILL.md`
- Test: `tests/test_four_entry_skill_contract.py`

**Interfaces:**
- `autoresearch-topic` consumes a topic/question/method and produces a topic research workspace plus `SYNTHESIS.md`.
- `autoresearch-proposal` consumes a readable application draft and produces `DRAFT_ANALYSIS.md`, branch packages, and promoted synthesis.
- `research-write` consumes promoted synthesis and obligations and produces a proposal/paper plus `submission-freeze/`.
- `research-audit` consumes a frozen branch or submission package and produces the Anti report and ARIS gate result.
- Compatibility entries delegate to the matching four-entry contract and do not define an alternate retrieval path.

- [x] **Step 1: Write failing contract tests**

Assert that all four canonical files and four primary wrappers exist, that the
topic file rejects proposal-mode inference, that the proposal file requires a
draft path and `DRAFT_ANALYSIS.md`, and that the write/audit files preserve the
promotion, freeze, provenance, and isolated-review contracts.

- [x] **Step 2: Run the focused tests and verify the missing-entry failure**

Run `python3 -m pytest tests/test_four_entry_skill_contract.py -q`.
Expected: FAIL because the four new entry files do not exist.

- [x] **Step 3: Write the four canonical contracts and compatibility wrappers**

Move the current topic/proposal requirements into separate canonical files;
make `research-write` and `research-audit` the canonical names for the current
write/audit contracts; turn the old `research`, `write`, and `audit` files into
explicit compatibility wrappers. Keep all query terminal states, Zotero call
shape, branch freeze, promotion outcomes, Anti provenance, and final freeze
rules in the canonical entries.

- [x] **Step 4: Run the focused tests and existing skill contracts**

Run `python3 -m pytest tests/test_four_entry_skill_contract.py tests/test_research_skill_contract.py tests/test_write_skill_contract.py tests/test_audit_skill_contract.py -q`.
Expected: PASS after updating old tests to treat the three names as wrappers.

- [x] **Step 5: Fold the entry split into the final ARIS correction commit**

```bash
git add skills tests/test_four_entry_skill_contract.py tests/test_research_skill_contract.py tests/test_write_skill_contract.py tests/test_audit_skill_contract.py
git commit -m "feat: split ARIS research into four public entries"
```

### Task 2: Make the Four-Entry Profile and Catalog Authoritative

**Files:**
- Modify: `tools/skill-profiles.tsv`
- Modify: `tools/skill-groups.tsv`
- Modify: `tests/test_skill_groups.py`
- Modify: `tests/test_install_aris_selective.py`
- Modify: `tests/test_install_aris_ps1.py`
- Modify: `tests/test_research_profile_e2e.py`

**Interfaces:**
- Profile `pyrojewel-research` selects the exact ordered list
  `autoresearch-topic,autoresearch-proposal,research-write,research-audit`.
- Each new entry has no catalog-level hard dependency; shared references and
  helper tools remain installer support content.
- `--exclude` continues to remove one selected entry without expanding legacy
  entries.

- [x] **Step 1: Change tests to require four entries**

Update synthetic profile fixtures and assertions so Codex, Claude, and
PowerShell installations expect exactly the four names. Add a regression that
adding an upstream legacy skill during reconcile does not alter the profile
manifest.

- [x] **Step 2: Run profile and catalog tests to verify RED**

Run `python3 -m pytest tests/test_skill_groups.py tests/test_install_aris_selective.py tests/test_install_aris_ps1.py -q`.
Expected: FAIL because the repository profile and synthetic fixtures still
select the three old names.

- [x] **Step 3: Update the catalog and profile**

Add the four entries to the appropriate research/review groups, keep their
`requires` field as `-`, and replace the profile row with the four ordered
names and a description that identifies the topic/proposal split.

- [x] **Step 4: Run installer smoke tests on all supported script paths**

Run the focused Python tests plus `bash -n tools/install_aris.sh tools/install_aris_codex.sh`.
Expected: PASS; no installer code change is required because profile selection
already consumes the catalog.

- [x] **Step 5: Fold the profile change into the final ARIS correction commit**

```bash
git add tools/skill-profiles.tsv tools/skill-groups.tsv tests/test_skill_groups.py tests/test_install_aris_selective.py tests/test_install_aris_ps1.py tests/test_research_profile_e2e.py
git commit -m "feat: expose four-entry research profile"
```

### Task 3: Add Upstream Flow Review Before Adoption

**Files:**
- Create: `tools/upstream_flow_review.py`
- Create: `tests/test_upstream_flow_review.py`
- Create: `docs/UPSTREAM_FLOW_REVIEW.md`
- Modify: `README.md`
- Modify: `README_CN.md`

**Interfaces:**
- `classify_candidate(candidate: dict, canonical_entries: set[str]) -> dict` returns a deterministic decision and reasons.
- CLI `python3 tools/upstream_flow_review.py --candidate candidate.json --out review.json` validates a candidate manifest without network access.
- Candidate decisions are `MERGE`, `ADAPT`, `OPTIONAL`, or `REJECT`.
- The review checks overlap, source policy, Codex compatibility, Anti/reviewer
  independence, dependency fan-out, and test evidence; it never performs a
  merge or changes the default profile.

- [x] **Step 1: Write failing classifier tests**

Cover a Zotero/Codex candidate that is `MERGE`, a useful but multi-source
candidate that is `ADAPT`, an unrelated optional flow, a duplicate canonical
entry, and a candidate with a forbidden silent Web/arXiv fallback that is
`REJECT`. Assert the CLI emits JSON and fails on malformed candidate input.

- [x] **Step 2: Run the focused tests and verify RED**

Run `python3 -m pytest tests/test_upstream_flow_review.py -q`.
Expected: FAIL because the classifier and CLI do not exist.

- [x] **Step 3: Implement the deterministic review tool**

Validate the candidate schema, inspect declared triggers/sources/host/
dependencies/tests, classify against the four-entry set, and emit a stable
JSON report containing candidate identity, decision, checks, reasons, and
reviewed commit. Keep semantic quality judgment as a human review field rather
than pretending the script can decide it automatically.

- [x] **Step 4: Document the fetch-review-adapt-test-adopt procedure**

Document isolated upstream fetch, candidate enumeration, the four decisions,
Zotero/Codex/Anti gates, provenance, and the rule that adoption requires an
explicit profile/catalog change and regression tests.

- [x] **Step 5: Fold the upstream review gate into the final ARIS correction commit**

```bash
git add tools/upstream_flow_review.py tests/test_upstream_flow_review.py docs/UPSTREAM_FLOW_REVIEW.md README.md README_CN.md
git commit -m "feat: review upstream flows before adoption"
```

### Task 4: Align Documentation and End-to-End Verification

**Files:**
- Modify: `docs/CODEX_CLAUDE_REVIEW_GUIDE.md`
- Modify: `docs/CODEX_CLAUDE_REVIEW_GUIDE_CN.md`
- Modify: `docs/ARIS_INTRO.md`
- Modify: `tests/test_research_skill_contract.py`
- Modify: `tests/test_write_skill_contract.py`
- Modify: `tests/test_audit_skill_contract.py`
- Modify: `task_plan.md`, `findings.md`, `progress.md`

**Interfaces:**
- Documentation names the four entries and distinguishes entry boundaries from
  shared internal helpers.
- Legacy names are explicitly marked compatibility-only.
- End-to-end fixtures verify topic and proposal entry selection separately,
  branch audit timing, writing promotion, and final audit handoff.

- [x] **Step 1: Update static contracts and documentation assertions**

Replace three-entry assertions with four-entry assertions while retaining tests
that old names contain no independent multi-source flow.

- [x] **Step 2: Run focused end-to-end tests**

Run `python3 -m pytest tests/test_four_entry_skill_contract.py tests/test_research_profile_e2e.py tests/test_skill_groups.py -q`.
Expected: PASS with separate topic/proposal entry coverage.

- [x] **Step 3: Update user-facing documentation and planning status**

Document the four commands, the two complete autoresearch paths, the two audit
checkpoints, the minimal profile, and the upstream review process. Mark Phase 6
complete only after full verification.

- [x] **Step 4: Run the full verification suite**

Run the full ARIS suite with the four environment-dependent `httpx` test
modules excluded because this environment does not provide `httpx`, then run
`git diff --check`, the isolated vendored Anti tests, and its deterministic eval.
Expected: all runnable ARIS tests pass, vendored Anti remains clean after
post-eval cleanup, and the preserved untracked files are not staged.

- [x] **Step 5: Commit and push the ARIS-only correction**

Review `git diff --cached --name-status`, confirm no standalone Anti checkout
or untracked planning scratch is staged, then commit and push to the configured
ARIS `origin` remote.
