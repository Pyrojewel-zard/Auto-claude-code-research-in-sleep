# ARIS Zotero-First Research Profile Implementation Plan

> **Superseded:** The original three-entry design in this execution record was
> corrected on 2026-09-12. The active implementation plan is
> [`2026-09-12-four-entry-aris-simplification.md`](2026-09-12-four-entry-aris-simplification.md),
> which restores four independent public entries: `autoresearch-topic`,
> `autoresearch-proposal`, `research-write`, and `research-audit`.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (- [ ]) syntax for tracking.

**Goal:** Build a Codex-first ARIS profile with research, write, and audit entries, Zotero-first retrieval, branch promotion gates, and an ARIS-owned Anti-Autoresearch audit engine.

**Architecture:** Rewrite the canonical research path around one dual-mode orchestrator and keep legacy entry names as non-default compatibility wrappers. Deterministic tools manage state, coverage, promotion, provenance, and obligations; a reviewed Anti-Autoresearch snapshot is vendored inside ARIS and supplies evidence and full-artifact adjudication without a separate runtime repository.

**Tech Stack:** Markdown Codex skills, Python 3 standard library, Bash installers, JSON, pytest/unittest-compatible tests.

**Spec:** ../specs/2026-09-08-zotero-first-autoresearch-anti-audit-design.md

## Global Constraints

- Work in /home/DataTransfer/Pyrojewel/code/02_claudeSkill/Auto-claude-code-research-in-sleep.
- Import the tested Anti release into ARIS first; do not require a separate Anti repository push or submodule.
- Zotero semantic search is the only automatic literature-discovery operation.
- WebSearch/WebFetch may run only after ask or pre-authorized allow.
- Never silently fall back when Zotero MCP or its index fails.
- A branch finishes autoresearch before lightweight evidence audit runs.
- Unresolved hard findings block only branch promotion and final writing.
- The active authoring context never issues its own audit verdict.
- Codex is canonical; Claude compatibility is thin and not the design source.
- Do not add the untracked skills/anti-autoresearch-bundle to Git.
- Do not physically delete the legacy catalog in this implementation.
- Every task ends with focused tests and a reviewable commit.

## Execution Status — 2026-09-12

- [x] Tasks 1–5: vendored Anti snapshot, deterministic research gates, the
  canonical Zotero-first research/write/audit entries, and fresh-review
  provenance are implemented in ARIS.
- [x] Task 6: `pyrojewel-research` installs only `research`, `write`, and
  `audit`; Bash, Codex, and PowerShell installer contracts are aligned.
- [x] Task 7: deterministic topic/proposal fixtures, replay harness, README,
  Zotero integration, and Codex review documentation are updated.
- [x] Standalone Anti delivery is intentionally absent: only
  `vendor/anti-autoresearch/` is staged for ARIS; the pre-existing
  `skills/anti-autoresearch-bundle/` remains untracked and untouched.
- [x] Verification: full ARIS suite `825 passed, 20 skipped, 28 subtests`
  plus isolated vendored Anti `144 passed` and `9/9` eval recall.

---

## File Structure

- Create vendor/anti-autoresearch/: a clean, tracked snapshot of the tested Anti implementation without its .git metadata or generated caches.
- Create tools/anti-autoresearch.lock.json: provenance for the vendored source URL, commit, and contract version.
- Create tools/update_anti_lock.py: safely write the lock from a real upstream checkout.
- Create tools/resolve_anti_autoresearch.py: resolve the ARIS-vendored release, with an explicit local override only for development/testing.
- Create tools/research_state.py: validate branch/query transitions and expansion policy.
- Create tools/research_gate.py: map Anti reports to branch promotion and shared obligations.
- Create skills/skills-codex/research/SKILL.md: canonical dual-mode research workflow.
- Create skills/skills-codex/write/SKILL.md: canonical evidence-gated writing workflow.
- Create skills/skills-codex/audit/SKILL.md: canonical full Anti adapter.
- Create skills/research/SKILL.md, skills/write/SKILL.md, skills/audit/SKILL.md: thin Claude-compatible entries.
- Rewrite research-lit, grant-proposal, paper-writing, and integrity-forensics skill files as compatibility wrappers or non-default legacy routes.
- Create tools/skill-profiles.tsv and add --profile support to Codex and generic installers.
- Add focused contract, policy, resolver, installer, and end-to-end tests.
- Update README and Zotero/Codex documentation.

### Task 1: Vendor and Resolve the Anti Audit Engine

**Files:**
- Create: vendor/anti-autoresearch/ (clean snapshot from the tested Anti checkout; no nested .git)
- Create: tools/anti-autoresearch.lock.json
- Create: tools/update_anti_lock.py
- Create: tools/resolve_anti_autoresearch.py
- Create: tests/test_anti_autoresearch_resolver.py
- Create: tests/test_anti_autoresearch_vendor.py

**Interfaces:**
- Consumes: the tested Anti checkout at the exact reviewed commit and its exact git rev-parse HEAD.
- Produces: a vendored source tree, provenance lock, update_lock(lock_path: Path, repo_url: str, commit: str, contract_version: str), and resolve_anti(lock_path: Path, local_repo: Path | None, cache_root: Path) -> Resolution.
- Resolution fields: repo_path, commit, source_kind, contract_version; the default source_kind is `vendored`.

- [ ] **Step 1: Write failing lock and resolver tests**

~~~python
from pathlib import Path
import pytest
from update_anti_lock import update_lock
from resolve_anti_autoresearch import resolve_anti

REPO_URL = "git@github.com:wanshuiyin/Anti-Autoresearch.git"
LOCKED_SHA = "0123456789abcdef0123456789abcdef01234567"

def test_update_lock_rejects_short_sha(tmp_path):
    with pytest.raises(ValueError):
        update_lock(tmp_path / "lock.json", REPO_URL, "abc123", "0.1")

def test_local_checkout_must_match_contract(tmp_path):
    result = resolve_anti(lock_path, local_repo, tmp_path / "cache")
    assert result.source_kind == "local"
    assert result.contract_version == "0.1"

def test_distribution_resolution_is_commit_pinned(tmp_path):
    result = resolve_anti(lock_path, None, tmp_path / "cache")
    assert result.commit == LOCKED_SHA
~~~

- [ ] **Step 2: Run tests and verify import failure**

~~~bash
python3 -m pytest tests/test_anti_autoresearch_resolver.py -q
~~~

Expected: FAIL because both tools are absent.

- [ ] **Step 3: Import the clean Anti snapshot and implement the vendored resolver**

The updater CLI is:

~~~text
python3 tools/update_anti_lock.py
  --repo-url git@github.com:wanshuiyin/Anti-Autoresearch.git
  --checkout /home/DataTransfer/Pyrojewel/code/02_claudeSkill/Anti-Autoresearch
  --contract-version 0.1
  --out tools/anti-autoresearch.lock.json
~~~

It reads git rev-parse HEAD from the checkout and refuses a dirty checkout,
non-40-character SHA, missing workflow, or failing upstream eval.

Export the tracked files from the tested Anti checkout into
`vendor/anti-autoresearch/` without copying `.git`, ignored caches, generated
eval output, or a second nested repository. Record the original repository URL,
exact commit, and contract version in the ARIS lock. The resolver uses this
vendored tree by default, verifies the contract and exact source provenance,
and returns structured JSON with `source_kind: vendored`. An explicit local
checkout may be used only for development/testing and must still match the
contract; normal resolution must never clone or fetch a separate Anti repo.

- [ ] **Step 4: Verify the vendored release and run tests**

~~~bash
python3 tools/update_anti_lock.py --repo-url git@github.com:wanshuiyin/Anti-Autoresearch.git --checkout /home/DataTransfer/Pyrojewel/code/02_claudeSkill/Anti-Autoresearch --contract-version 0.1 --out tools/anti-autoresearch.lock.json
python3 -m pytest tests/test_anti_autoresearch_resolver.py tests/test_anti_autoresearch_vendor.py -q
python3 /home/DataTransfer/Pyrojewel/code/02_claudeSkill/Anti-Autoresearch/eval/run_eval.py
~~~

Expected: PASS; the lock records the exact tested Anti HEAD, the vendored
tree has no nested repository metadata, and no network access is needed for
normal ARIS resolution. A separate Anti push is not part of this task.

- [ ] **Step 5: Commit the resolver**

~~~bash
git add vendor/anti-autoresearch tools/anti-autoresearch.lock.json tools/update_anti_lock.py tools/resolve_anti_autoresearch.py tests/test_anti_autoresearch_resolver.py tests/test_anti_autoresearch_vendor.py
git commit -m "feat: vendor Anti-Autoresearch audit engine"
~~~

### Task 2: Add Deterministic Research State and Promotion Policy

**Files:**
- Create: tools/research_state.py
- Create: tools/research_gate.py
- Create: tests/test_research_state.py
- Create: tests/test_research_gate.py

**Interfaces:**
- Consumes: RESEARCH_STATE.json, query terminal statuses, Anti report.json, and branch artifact hashes.
- Produces: transition(state: dict, event: str, branch_id: str | None = None) -> dict; coverage_decision(branch: dict) -> list[dict]; evaluate_branch(report: dict, state: dict, branch_id: str) -> str; append_obligations(path: Path, findings: list[dict], branch_id: str) -> None.

- [ ] **Step 1: Write failing state-machine tests**

~~~python
def new_state(mode="topic", expansion_policy="ask"):
    return {"mode": mode, "external_expansion": expansion_policy,
            "branches": {"b1": {"status": "BRANCH_PLANNED"}}}

def state_with_branches(*ids):
    return {"branches": {branch_id: {"status": "BRANCH_RESEARCHED"}
                         for branch_id in ids}}

def ready_state():
    return state_with_branches("b1")

def hard_report():
    return {"overall_verdict": "HARD_FLAGS", "findings": []}

def soft_report():
    return {"overall_verdict": "SOFT_FLAGS", "findings": []}

def test_branch_audit_runs_only_after_research_completion():
    state = new_state(mode="topic", expansion_policy="ask")
    with pytest.raises(InvalidTransition):
        transition(state, "AUDIT_COMPLETE", branch_id="b1")

def test_hard_flags_block_only_one_branch():
    state = state_with_branches("b1", "b2")
    assert evaluate_branch(hard_report(), state, "b1") == "NEEDS_WORK"
    assert state["branches"]["b2"]["status"] == "BRANCH_RESEARCHED"

def test_soft_flags_promote_with_obligations():
    assert evaluate_branch(soft_report(), ready_state(), "b1") == "PROMOTABLE_WITH_OBLIGATIONS"
~~~

Also test terminal query status validation, ask/never/allow policies, one prompt
per completed coverage report, stale audit hashes, and append-only obligations.

- [ ] **Step 2: Run tests and verify failure**

~~~bash
python3 -m pytest tests/test_research_state.py tests/test_research_gate.py -q
~~~

Expected: import failures.

- [ ] **Step 3: Implement state and gate functions**

Use these constants:

~~~python
QUERY_TERMINAL = {"SEARCHED", "NO_HIT", "UNVERIFIED", "UNSEARCHABLE", "ERROR"}
EXPANSION_POLICIES = {"ask", "never", "allow"}
PROMOTION_STATES = {"PROMOTABLE", "PROMOTABLE_WITH_OBLIGATIONS", "NEEDS_WORK"}
~~~

Map HARD_FLAGS to NEEDS_WORK, SOFT_FLAGS to
PROMOTABLE_WITH_OBLIGATIONS, and CLEAN_GIVEN_EVIDENCE to PROMOTABLE. Reject
unknown verdicts and artifact-hash mismatches. Preserve each obligation by a
stable fingerprint of branch, skill, pattern, claim, and span.

- [ ] **Step 4: Run focused and existing gate tests**

~~~bash
python3 -m pytest tests/test_research_state.py tests/test_research_gate.py tests/test_forensics_gate.py -q
~~~

Expected: PASS.

- [ ] **Step 5: Commit policy tools**

~~~bash
git add tools/research_state.py tools/research_gate.py tests/test_research_state.py tests/test_research_gate.py
git commit -m "feat: gate research branch promotion"
~~~

### Task 3: Build the Canonical Codex Research Entry

**Files:**
- Create: skills/skills-codex/research/SKILL.md
- Create: skills/research/SKILL.md
- Modify: skills/skills-codex/research-lit/SKILL.md
- Modify: skills/research-lit/SKILL.md
- Modify: skills/skills-codex/grant-proposal/SKILL.md
- Modify: skills/grant-proposal/SKILL.md
- Create: tests/test_research_skill_contract.py

**Interfaces:**
- Consumes: topic text or draft path; Zotero semantic_search, item details, content, and annotations; tools/research_state.py; Anti evidence-audit workflow.
- Produces: RESEARCH_BRIEF.md, BRANCH_PLAN.md, RESEARCH_STATE.json, per-branch QUERY_PACK.md, EVIDENCE_MATRIX.md, COVERAGE_REPORT.md, EVIDENCE_AUDIT files, OBLIGATIONS.md, and SYNTHESIS.md.

- [ ] **Step 1: Write failing skill contract tests**

~~~python
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def read(relative):
    return (ROOT / relative).read_text(encoding="utf-8")

def test_research_has_two_modes_and_zotero_is_automatic():
    text = read("skills/skills-codex/research/SKILL.md")
    for token in ["topic mode", "proposal mode", "semantic_search", "QUERY_PACK.md", "COVERAGE_REPORT.md"]:
        assert token.lower() in text.lower()
    assert "sources: all" not in text.lower()

def test_external_search_is_never_silent():
    text = read("skills/skills-codex/research/SKILL.md")
    assert "external_expansion: ask" in text
    assert "WebSearch" in text
    assert "only after" in text
~~~

Also assert one semantic call per query, alias retry once, all five query
statuses, four query families, branch audit after BRANCH_RESEARCHED, and fresh
reviewer context.

- [ ] **Step 2: Run tests and verify failure**

~~~bash
python3 -m pytest tests/test_research_skill_contract.py -q
~~~

Expected: FAIL because the public research entries are absent.

- [ ] **Step 3: Write the Codex canonical workflow and compatibility wrappers**

The canonical workflow order is:

~~~text
classify input mode
-> write research brief
-> create independent branches
-> write each query pack
-> semantic_search once per query
-> fetch details/content/annotations
-> write evidence matrix and coverage report
-> ask once when policy is ask and gaps exist
-> freeze branch package
-> invoke upstream evidence audit in a fresh reviewer context
-> run research_gate.py
-> synthesize promoted branches
~~~

The top-level research skill is a thin Claude-compatible adaptation. Legacy
research-lit points users to research topic mode. Legacy grant-proposal points
users to research proposal mode followed by write proposal mode. Neither legacy
entry belongs to the minimal profile.

- [ ] **Step 4: Run contract and previous proposal tests**

~~~bash
python3 -m pytest tests/test_research_skill_contract.py tests/test_grant_proposal_query_pack_contract.py -q
~~~

Expected: PASS after updating the older test to accept explicit compatibility
wrappers while preserving query-pack and evidence-matrix guarantees.

- [ ] **Step 5: Commit the research entry**

~~~bash
git add skills/research skills/skills-codex/research skills/research-lit skills/skills-codex/research-lit skills/grant-proposal skills/skills-codex/grant-proposal tests/test_research_skill_contract.py tests/test_grant_proposal_query_pack_contract.py
git commit -m "feat: add Zotero-first research workflow"
~~~

### Task 4: Build Evidence-Gated Writing

**Files:**
- Create: skills/skills-codex/write/SKILL.md
- Create: skills/write/SKILL.md
- Modify: skills/skills-codex/paper-writing/SKILL.md
- Modify: skills/paper-writing/SKILL.md
- Create: tests/test_write_skill_contract.py

**Interfaces:**
- Consumes: research workspace, promoted branch states, SYNTHESIS.md, and OBLIGATIONS.md.
- Produces: proposal or paper draft plus a frozen submission directory for audit.

- [ ] **Step 1: Write failing writing-gate tests**

~~~python
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def read(relative):
    return (ROOT / relative).read_text(encoding="utf-8")

def test_write_consumes_only_promoted_evidence():
    text = read("skills/skills-codex/write/SKILL.md")
    for token in ["PROMOTABLE", "PROMOTABLE_WITH_OBLIGATIONS", "NEEDS_WORK", "OBLIGATIONS.md"]:
        assert token in text

def test_unverified_evidence_cannot_be_load_bearing():
    text = read("skills/skills-codex/write/SKILL.md")
    assert "UNVERIFIED" in text
    assert "qualify or remove" in text.lower()
~~~

Also assert proposal/paper modes, future-work language for proposals, observed
versus inferred claims for papers, and final audit invocation.

- [ ] **Step 2: Run and observe failure**

~~~bash
python3 -m pytest tests/test_write_skill_contract.py -q
~~~

Expected: FAIL because write does not exist.

- [ ] **Step 3: Write canonical write and legacy wrapper skills**

The skill must call research_gate.py before drafting and again before
finalization. It may continue with soft obligations but must quote them in a
limitations/checklist section. It freezes exact inputs and hashes before
invoking audit. Legacy paper-writing becomes a compatibility entry outside the
minimal profile.

- [ ] **Step 4: Run writing and gate tests**

~~~bash
python3 -m pytest tests/test_write_skill_contract.py tests/test_research_gate.py tests/test_forensics_gate.py -q
~~~

Expected: PASS.

- [ ] **Step 5: Commit writing**

~~~bash
git add skills/write skills/skills-codex/write skills/paper-writing skills/skills-codex/paper-writing tests/test_write_skill_contract.py
git commit -m "feat: add evidence-gated research writing"
~~~

### Task 5: Build the Full Audit Entry and Codex-Isolated Adapter

**Files:**
- Create: skills/skills-codex/audit/SKILL.md
- Create: skills/audit/SKILL.md
- Modify: skills/skills-codex/integrity-forensics/SKILL.md
- Modify: skills/integrity-forensics/SKILL.md
- Modify: tools/forensics_gate.py
- Modify: tests/test_forensics_gate.py
- Create: tests/test_audit_skill_contract.py

**Interfaces:**
- Consumes: frozen PDF/source/code/results directory and tools/resolve_anti_autoresearch.py output for the ARIS-vendored Anti engine.
- Produces: upstream report.json and REPORT.md plus ARIS gate and append-only obligations.
- Produces: classify_review_provenance(executor: str, reviewer: str, isolated: bool) -> str in tools/forensics_gate.py.

- [ ] **Step 1: Write failing audit adapter tests**

~~~python
from pathlib import Path
from forensics_gate import classify_review_provenance

ROOT = Path(__file__).resolve().parents[1]

def read(relative):
    return (ROOT / relative).read_text(encoding="utf-8")

def test_codex_audit_uses_isolated_reviewer_and_locked_upstream():
    text = read("skills/skills-codex/audit/SKILL.md")
    for token in ["resolve_anti_autoresearch.py", "fresh isolated Codex reviewer", "read-only", "forensics_gate.py"]:
        assert token in text
    assert "mcp__codex__codex-reply" not in text

def test_same_family_is_not_same_context():
    gate = classify_review_provenance(executor="codex", reviewer="codex", isolated=True)
    assert gate == "same-family-isolated"
~~~

- [ ] **Step 2: Run tests and verify failure**

~~~bash
python3 -m pytest tests/test_audit_skill_contract.py tests/test_forensics_gate.py -q
~~~

Expected: FAIL because audit and isolated provenance do not exist.

- [ ] **Step 3: Implement audit and provenance**

Audit resolves the ARIS-vendored Anti snapshot, runs its eval, invokes the
frozen artifact workflow, and folds the report into forensics_gate.py. Extend
provenance labels to cross-family, same-family-isolated, and same-context.
Same-context must fail closed.

Legacy integrity-forensics becomes a wrapper to audit and no longer hard-codes
the external repository URL or commit; provenance comes from the ARIS lock.

- [ ] **Step 4: Run audit and resolver tests**

~~~bash
python3 -m pytest tests/test_audit_skill_contract.py tests/test_forensics_gate.py tests/test_anti_autoresearch_resolver.py -q
~~~

Expected: PASS.

- [ ] **Step 5: Commit audit integration**

~~~bash
git add skills/audit skills/skills-codex/audit skills/integrity-forensics skills/skills-codex/integrity-forensics tools/forensics_gate.py tests/test_audit_skill_contract.py tests/test_forensics_gate.py
git commit -m "feat: integrate isolated Anti-Autoresearch audit"
~~~

### Task 6: Add the Minimal Codex-First Profile

**Files:**
- Create: tools/skill-profiles.tsv
- Modify: tools/install_aris_codex.sh
- Modify: tools/install_aris.sh
- Modify: tools/install_aris.ps1
- Modify: tools/skill-groups.tsv
- Modify: tests/test_install_aris_selective.py
- Modify: tests/test_install_aris_ps1.py
- Modify: tests/test_skill_groups.py

**Interfaces:**
- Consumes: profile name pyrojewel-research.
- Produces: --profile pyrojewel-research selection equivalent to --skills research,write,audit plus declared internal dependencies; profile conflicts with --all and --groups.

- [ ] **Step 1: Add failing profile-selection tests**

~~~python
def test_pyrojewel_profile_selects_only_three_public_entries(self):
    self._run("--profile", "pyrojewel-research")
    installed = {p.name for p in self.skills_dir.iterdir()}
    assert installed == {"research", "write", "audit"}

def test_profile_rejects_all_and_groups(self):
    assert self._run("--profile", "pyrojewel-research", "--all",
                     check=False).returncode == 2
    assert self._run("--profile", "pyrojewel-research", "--groups",
                     "lit-search", check=False).returncode == 2
~~~

Also test unknown profiles, list-profiles output, transitive internal
dependencies, update reconciliation, and PowerShell parity.

- [ ] **Step 2: Run selective installer tests**

~~~bash
python3 -m pytest tests/test_install_aris_selective.py tests/test_install_aris_ps1.py tests/test_skill_groups.py -q
~~~

Expected: FAIL because --profile is unknown.

- [ ] **Step 3: Implement the profile catalog and installer flag**

Use this tab-separated record:

~~~text
pyrojewel-research	research,write,audit	Codex-first Zotero research, writing, and Anti audit
~~~

Parse the profile before catalog dependency expansion. Reject combinations with
--all and --groups; allow --exclude only when it does not remove a required
dependency. List profiles without requiring an install.

Add research, write, and audit catalog records with exact requires fields.
Legacy broad skills remain catalogued but are not selected.

- [ ] **Step 4: Run all installer tests**

~~~bash
python3 -m pytest tests/test_install_aris_selective.py tests/test_install_aris_ps1.py tests/test_skill_groups.py tests/test_codex_install_update.py -q
~~~

Expected: PASS.

- [ ] **Step 5: Commit the profile**

~~~bash
git add tools/skill-profiles.tsv tools/skill-groups.tsv tools/install_aris_codex.sh tools/install_aris.sh tools/install_aris.ps1 tests/test_install_aris_selective.py tests/test_install_aris_ps1.py tests/test_skill_groups.py
git commit -m "feat: add Pyrojewel research profile"
~~~

### Task 7: Add End-to-End Fixtures and Documentation

**Files:**
- Create: tests/fixtures/research/topic_complete/
- Create: tests/fixtures/research/topic_gap/
- Create: tests/fixtures/research/proposal_branches/
- Create: tools/replay_research_fixture.py
- Create: tests/test_research_profile_e2e.py
- Modify: README.md
- Modify: README_CN.md
- Modify: docs/integrations/ZOTERO.md
- Modify: docs/integrations/ZOTERO_CN.md
- Modify: docs/CODEX_CLAUDE_REVIEW_GUIDE.md
- Modify: docs/CODEX_CLAUDE_REVIEW_GUIDE_CN.md

**Interfaces:**
- Consumes: all prior ARIS tasks and the ARIS-vendored Anti release.
- Produces: fixture-backed proof of both research modes, gap policy, partial branch failure, writing gates, full audit resolution, and install surface.
- Produces: run_fixture(fixture_dir: Path, expansion_policy: str) -> dict in tools/replay_research_fixture.py.

- [ ] **Step 1: Write failing end-to-end tests**

~~~python
from pathlib import Path
from replay_research_fixture import run_fixture

FIXTURES = Path(__file__).parent / "fixtures" / "research"

def test_topic_fixture_reaches_synthesis_with_zotero_only():
    run = run_fixture(FIXTURES / "topic_complete", "ask")
    assert run["status"] == "WRITE_READY"
    assert run["external_calls"] == []

def test_proposal_fixture_excludes_only_failed_branch():
    run = run_fixture(FIXTURES / "proposal_branches", "ask")
    assert run["branches"]["unsupported"]["status"] == "NEEDS_WORK"
    assert run["branches"]["supported"]["status"] == "PROMOTABLE"
    assert "unsupported" not in run["synthesis_load_bearing_claims"]

def test_gap_fixture_asks_once():
    run = run_fixture(FIXTURES / "topic_gap", "ask")
    assert run["expansion_prompt_count"] == 1
~~~

Implement run_fixture by reading state.json, events.json, and reports/*.json
from the fixture directory, then calling research_state.transition and
research_gate.evaluate_branch in event order. Return the final JSON-compatible
state. Do not call live Zotero, Web, or a live reviewer.

- [ ] **Step 2: Run the end-to-end test and verify failure**

~~~bash
python3 -m pytest tests/test_research_profile_e2e.py -q
~~~

Expected: FAIL until fixture adapters and expected outputs are complete.

- [ ] **Step 3: Complete fixtures and update documentation**

README start-here must lead with:

~~~text
/research -> /write -> /audit
~~~

Document topic and proposal modes, Zotero semantic index requirements,
ask/never/allow policy, isolated Codex review, the vendored Anti provenance
lock, and the fact that the legacy catalog remains available but outside the
minimal profile.

- [ ] **Step 4: Run the full ARIS verification suite**

~~~bash
python3 -m pytest tests -q
bash tools/install_aris_codex.sh --list-profiles
bash tools/install_aris_codex.sh --profile pyrojewel-research --dry-run
git diff --check
git status --short
~~~

Expected: all tests PASS; list-profiles includes pyrojewel-research; dry-run
contains research, write, audit and no broad search skill; the ARIS-vendored
Anti tree is tracked while the pre-existing untracked
anti-autoresearch-bundle remains untouched and unstaged.

- [ ] **Step 5: Commit and push ARIS**

~~~bash
git add README.md README_CN.md docs/integrations/ZOTERO.md docs/integrations/ZOTERO_CN.md docs/CODEX_CLAUDE_REVIEW_GUIDE.md docs/CODEX_CLAUDE_REVIEW_GUIDE_CN.md tools/replay_research_fixture.py tests/fixtures/research tests/test_research_profile_e2e.py
git commit -m "docs: make audited Zotero research the default flow"
git push origin main
git status --short
~~~

Expected: push succeeds; only planning files and the pre-existing untracked
anti-autoresearch-bundle may remain outside the implementation commits. No
separate Anti repository push is required.
