# Anti-Autoresearch Evidence Audit Upstream Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (- [ ]) syntax for tracking.

**Goal:** Add a deterministic, span-anchored lightweight evidence-audit contract to Anti-Autoresearch for completed ARIS research branches.

**Architecture:** Extend the existing claims, finding, report, adjudicator, and eval spine instead of creating a second verdict system. A branch package contains claims plus query coverage; deterministic checks propose findings, an isolated semantic reviewer may add findings, and the existing adjudicator alone computes the verdict.

**Tech Stack:** Python 3.12 standard library, JSON Schema draft-07, Markdown skills, unittest/pytest-compatible tests.

**Spec:** ../specs/2026-09-08-zotero-first-autoresearch-anti-audit-design.md

## Global Constraints

- Work in /home/DataTransfer/Pyrojewel/code/02_claudeSkill/Anti-Autoresearch.
- Preserve detect-only behavior; no audit step edits the researched artifact.
- The reviewer proposes findings; tools/adjudicate_findings.py alone computes verdicts.
- Above-info findings require a real claim_id and verbatim span.
- External-check findings never raise the deterministic verdict.
- Codex-primary independence means a fresh isolated reviewer context, not necessarily a different model family.
- Use only Python standard library in required paths; scipy remains optional.
- Do not add Zotero or Web retrieval to Anti; ARIS supplies the frozen evidence package.
- Run upstream eval before creating the release commit.

---

## File Structure

- Modify schemas/claims.schema.json: admit research-branch claims and traceability fields.
- Create schemas/query_coverage.schema.json: define query statuses, directions, and source provenance.
- Modify schemas/finding.schema.json: admit evidence-audit findings.
- Modify schemas/report.schema.json: add the research-evidence dimension.
- Create references/research-evidence-audit-contract.md: freeze the ARIS-to-Anti interface.
- Modify references/reviewer-independence.md: generalize independence for Codex-primary execution.
- Create tools/check_evidence_coverage.py: deterministic branch-evidence checks.
- Modify tools/adjudicate_findings.py: roll up the new dimension through existing rules.
- Create workflows/evidence-audit/SKILL.md: orchestrate deterministic and isolated semantic review.
- Create tests/test_evidence_audit_contract.py: schema and workflow contract tests.
- Create tests/test_evidence_coverage.py: deterministic checker tests.
- Modify tests/test_adjudicator.py: prove evidence findings use existing verdict rules.
- Add eval/fixtures/evidence_branch/ files and modify eval/run_eval.py: regression gate.

### Task 1: Define the Research Evidence Contract

**Files:**
- Create: schemas/query_coverage.schema.json
- Create: references/research-evidence-audit-contract.md
- Modify: schemas/claims.schema.json
- Modify: schemas/finding.schema.json
- Modify: schemas/report.schema.json
- Test: tests/test_evidence_audit_contract.py

**Interfaces:**
- Consumes: existing claims.json, finding objects, and report.json conventions.
- Produces: query_coverage.json schema version 0.1; claim types research_claim, evidence_statement, and hypothesis; finding skill evidence-audit; report dimension research_evidence.

- [ ] **Step 1: Write failing schema contract tests**

~~~python
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def load_json(relative):
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))

def test_research_contract_enums():
    claims = load_json("schemas/claims.schema.json")
    claim_types = claims["properties"]["claims"]["items"]["properties"]["type"]["enum"]
    assert {"research_claim", "evidence_statement", "hypothesis"} <= set(claim_types)

    finding = load_json("schemas/finding.schema.json")
    assert "evidence-audit" in finding["properties"]["skill"]["enum"]

    report = load_json("schemas/report.schema.json")
    dims = report["properties"]["dimension_verdicts"]["properties"]
    assert "research_evidence" in dims
~~~

Also assert that query_coverage.schema.json requires branch_id, source_policy,
queries, and artifact_hashes; each query requires query_id, status,
evidence_directions, source, and evidence_item_keys.

- [ ] **Step 2: Run the tests and verify failure**

Run:

~~~bash
python3 -m pytest tests/test_evidence_audit_contract.py -q
~~~

Expected: FAIL because query_coverage.schema.json and the new enums do not exist.

- [ ] **Step 3: Add the schema fields and written contract**

Use these terminal query states:

~~~json
["SEARCHED", "NO_HIT", "UNVERIFIED", "UNSEARCHABLE", "ERROR"]
~~~

Use these evidence directions:

~~~json
["supports", "contradicts", "limits", "unclear"]
~~~

Add optional claim properties:

~~~json
"query_ids": {"type": "array", "items": {"type": "string"}},
"evidence_direction": {"type": "string", "enum": ["supports", "contradicts", "limits", "unclear"]},
"verification_status": {"type": "string", "enum": ["VERIFIED", "UNVERIFIED", "VERIFY_PENDING"]},
"load_bearing": {"type": "boolean"},
"support_basis": {"type": "string", "enum": ["quoted_span", "annotation", "metadata", "relevance_score", "none"]}
~~~

Document that evidence spans remain verbatim claims-schema anchors and that
query_coverage.json never substitutes for claims.json.

- [ ] **Step 4: Run the contract tests**

Run:

~~~bash
python3 -m pytest tests/test_evidence_audit_contract.py -q
~~~

Expected: PASS.

- [ ] **Step 5: Commit the contract**

~~~bash
git add schemas references/research-evidence-audit-contract.md tests/test_evidence_audit_contract.py
git commit -m "feat: define research evidence audit contract"
~~~

### Task 2: Add Deterministic Evidence Coverage Checks

**Files:**
- Create: tools/check_evidence_coverage.py
- Create: tests/test_evidence_coverage.py
- Modify: references/hack-pattern-taxonomy.md

**Interfaces:**
- Consumes: check_coverage(claims_doc: dict, coverage_doc: dict) inputs conforming to Task 1.
- Produces: list[dict] findings with skill evidence-audit; CLI accepts --ledger, --coverage, and --out.

- [ ] **Step 1: Write failing checker tests**

~~~python
def claims_doc(load_bearing=False, support_basis="none"):
    return {"claims": [{"claim_id": "C001", "type": "research_claim",
            "text_span": "The proposed mechanism improves robustness.",
            "location": {"file": "EVIDENCE_MATRIX.md"}, "load_bearing": load_bearing,
            "support_basis": support_basis, "evidence_anchor": "a" * 64}]}

def coverage_doc(items=None, counter_query_run=True):
    return {"branch_id": "b1", "source_policy": "zotero",
            "counter_query_run": counter_query_run,
            "queries": [{"query_id": "Q1", "status": "SEARCHED",
                         "evidence_directions": ["supports"],
                         "source": "zotero", "evidence_item_keys": items or []}]}

def one(findings, pattern_id):
    return next(f for f in findings if f["pattern_id"] == pattern_id)

def test_load_bearing_claim_without_verified_support_is_critical():
    findings = check_coverage(claims_doc(load_bearing=True), coverage_doc(items=[]))
    assert one(findings, "HP-EVIDENCE-UNSUPPORTED")["severity"] == "critical"

def test_relevance_score_cannot_be_support():
    findings = check_coverage(
        claims_doc(load_bearing=True, support_basis="relevance_score"),
        coverage_doc(items=["Z1"]),
    )
    assert one(findings, "HP-EVIDENCE-RELEVANCE-AS-SUPPORT")["severity"] == "critical"

def test_missing_counter_query_is_soft():
    findings = check_coverage(claims_doc(), coverage_doc(counter_query_run=False))
    assert one(findings, "HP-EVIDENCE-NO-COUNTERSEARCH")["severity"] == "minor"
~~~

Also test NO_HIT preservation, UNVERIFIED evidence, missing item provenance,
stable finding IDs, and successful CLI JSON output.

- [ ] **Step 2: Run the focused tests**

~~~bash
python3 -m pytest tests/test_evidence_coverage.py -q
~~~

Expected: import failure because tools/check_evidence_coverage.py is absent.

- [ ] **Step 3: Implement the minimal checker**

Define:

~~~python
def check_coverage(claims_doc: dict, coverage_doc: dict) -> list[dict]:
    """Return deterministic, span-anchored evidence-audit findings."""

def main(argv: list[str] | None = None) -> int:
    """Read --ledger/--coverage and write a findings object to --out."""
~~~

Every above-info finding must quote the claim text_span and copy its claim_id
and evidence_anchor. Use critical only for load-bearing unsupported claims and
relevance-as-support. Use major/minor for unverifiable support, missing
countersearch, and provenance gaps.

- [ ] **Step 4: Run checker and existing adjudicator tests**

~~~bash
python3 -m pytest tests/test_evidence_coverage.py tests/test_adjudicator.py -q
~~~

Expected: PASS.

- [ ] **Step 5: Commit deterministic checks**

~~~bash
git add tools/check_evidence_coverage.py tests/test_evidence_coverage.py references/hack-pattern-taxonomy.md
git commit -m "feat: check research evidence coverage"
~~~

### Task 3: Route Evidence Findings Through the Existing Adjudicator

**Files:**
- Modify: tools/adjudicate_findings.py
- Modify: tests/test_adjudicator.py
- Modify: schemas/report.schema.json

**Interfaces:**
- Consumes: evidence-audit findings from Task 2.
- Produces: research_evidence dimension verdict and unchanged overall verdict enum.

- [ ] **Step 1: Add failing adjudicator tests**

~~~python
def test_evidence_audit_rolls_up_without_new_verdict_system():
    finding = _f(skill="evidence-audit", severity="critical")
    report = _final([finding])
    assert report["dimension_verdicts"]["research_evidence"] == "critical"
    assert report["overall_verdict"] == "HARD_FLAGS"

def test_external_evidence_gap_is_information_only():
    finding = _f(
        skill="evidence-audit",
        severity="critical",
        verdict_local="needs_external_check",
        requires_external_check=True,
    )
    assert _final([finding])["overall_verdict"] == "CLEAN_GIVEN_EVIDENCE"
~~~

- [ ] **Step 2: Verify the new dimension test fails**

~~~bash
python3 -m pytest tests/test_adjudicator.py -q
~~~

Expected: FAIL because evidence-audit has no dimension mapping.

- [ ] **Step 3: Add the dimension mapping**

~~~python
SKILL_TO_DIMENSION = {
    "consistency-audit": "consistency",
    "experiment-forensics": "experiment",
    "baseline-comparison-audit": "baseline",
    "citation-forensics": "citation",
    "presentation-signals": "presentation",
    "proof-derivation-forensics": "proof",
    "eval-design-forensics": "evaluation",
    "evidence-audit": "research_evidence",
}
~~~

Do not add a fourth overall verdict or let the workflow calculate it.

- [ ] **Step 4: Run all Anti unit tests**

~~~bash
python3 -m pytest tests -q
~~~

Expected: PASS.

- [ ] **Step 5: Commit adjudicator support**

~~~bash
git add tools/adjudicate_findings.py schemas/report.schema.json tests/test_adjudicator.py
git commit -m "feat: adjudicate research evidence findings"
~~~

### Task 4: Add the Lightweight Evidence-Audit Workflow

**Files:**
- Create: workflows/evidence-audit/SKILL.md
- Modify: references/reviewer-independence.md
- Modify: tests/test_evidence_audit_contract.py

**Interfaces:**
- Consumes: a directory containing claims.json and query_coverage.json.
- Produces: evidence-audit.deterministic.findings.json, evidence-audit.semantic.findings.json, report.json, and REPORT.md.
- Reviewer input: absolute package path, claims.json, query_coverage.json, rubric, and observability level only.

- [ ] **Step 1: Add failing workflow text-contract tests**

~~~python
def test_workflow_is_detect_only_and_context_isolated():
    text = read("workflows/evidence-audit/SKILL.md")
    for token in [
        "check_evidence_coverage.py",
        "adjudicate_findings.py",
        "fresh isolated Codex reviewer",
        "never edit",
        "claims.json",
        "query_coverage.json",
    ]:
        assert token in text
~~~

Assert that the workflow forbids WebSearch, Zotero retrieval, same-context
verdicts, repeated audit-until-clean loops, and non-deterministic final verdicts.

- [ ] **Step 2: Run and observe failure**

~~~bash
python3 -m pytest tests/test_evidence_audit_contract.py -q
~~~

Expected: FAIL because the workflow is absent.

- [ ] **Step 3: Write the workflow and independence update**

The workflow order is:

~~~text
validate package
-> run deterministic coverage checker
-> open one fresh isolated Codex reviewer
-> validate semantic finding anchors
-> run the existing deterministic adjudicator
-> render report
~~~

Generalize reviewer independence to two enforceable properties:

- the reviewer receives a frozen package and no authoring chat context;
- the reviewer cannot compute or write overall_verdict.

- [ ] **Step 4: Run contract and full tests**

~~~bash
python3 -m pytest tests -q
~~~

Expected: PASS.

- [ ] **Step 5: Commit the workflow**

~~~bash
git add workflows/evidence-audit references/reviewer-independence.md tests/test_evidence_audit_contract.py
git commit -m "feat: add isolated research evidence audit"
~~~

### Task 5: Extend the Upstream Eval and Publish the Release

**Files:**
- Create: eval/fixtures/evidence_branch/claims.json
- Create: eval/fixtures/evidence_branch/query_coverage.json
- Create: eval/expected_findings/evidence_branch.json
- Modify: eval/run_eval.py
- Modify: README.md

**Interfaces:**
- Consumes: Tasks 1-4.
- Produces: a clean upstream main commit whose SHA is the exact input to the ARIS version lock.

- [ ] **Step 1: Add the evidence-branch eval case**

The fixture must contain one verified supported claim, one load-bearing
unsupported claim, one preserved NO_HIT query, and one missing counter-query.
Expected output must require HARD_FLAGS from the unsupported claim and retain
the soft countersearch finding.

- [ ] **Step 2: Run eval and verify it initially reports the missing case**

~~~bash
python3 eval/run_eval.py
~~~

Expected before wiring: FAIL because evidence_branch is not evaluated.

- [ ] **Step 3: Wire the fixture into eval/run_eval.py and document the workflow**

Reuse the same deterministic tools invoked by workflows/evidence-audit/SKILL.md.
Do not call Web or a live model from eval. State in README that semantic
findings are optional additions and deterministic fixtures are the release gate.

- [ ] **Step 4: Run release checks**

~~~bash
python3 -m pytest tests -q
python3 eval/run_eval.py
git diff --check
git status --short
~~~

Expected: all tests/eval PASS; only intended files are modified.

- [ ] **Step 5: Commit and push the Anti upstream release**

~~~bash
git add README.md eval
git commit -m "test: gate research evidence audit release"
git push origin main
git rev-parse HEAD
~~~

Record the complete 40-character SHA printed by the final command. The ARIS
plan consumes that exact value through its lock-update command, never a
manually transcribed token.
