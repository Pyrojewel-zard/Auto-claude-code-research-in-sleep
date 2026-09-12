import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read(relative):
    return (ROOT / relative).read_text(encoding="utf-8")


def _load_schema(name):
    return json.loads((ROOT / "schemas" / name).read_text(encoding="utf-8"))


def _workflow_python_block(start_marker):
    text = read("workflows/evidence-audit/SKILL.md")
    return text.split(start_marker, 1)[1].split("\nPY\n", 1)[0]


def _run_python_block(code, *args):
    return subprocess.run(
        ["python3", "-", *(str(arg) for arg in args)],
        input=code,
        text=True,
        capture_output=True,
        check=False,
    )


def test_query_coverage_schema_declares_version_and_required_fields():
    schema = _load_schema("query_coverage.schema.json")

    assert schema["$schema"] == "http://json-schema.org/draft-07/schema#"
    assert schema["properties"]["schema_version"]["const"] == "0.1"
    assert set(schema["required"]) >= {
        "branch_id",
        "source_policy",
        "queries",
        "artifact_hashes",
    }
    assert "counter_query_run" not in schema["required"]
    assert schema["properties"]["counter_query_run"]["type"] == "boolean"


def test_query_coverage_schema_declares_query_contract():
    schema = _load_schema("query_coverage.schema.json")
    query = schema["properties"]["queries"]["items"]

    assert set(query["required"]) >= {
        "query_id",
        "status",
        "evidence_directions",
        "source",
        "evidence_item_keys",
    }
    assert query["properties"]["status"]["enum"] == [
        "SEARCHED",
        "NO_HIT",
        "UNVERIFIED",
        "UNSEARCHABLE",
        "ERROR",
    ]
    assert query["properties"]["evidence_directions"]["items"]["enum"] == [
        "supports",
        "contradicts",
        "limits",
        "unclear",
    ]


def test_current_taxonomy_version_reaches_report_paths_and_eval():
    adjudicator = read("tools/adjudicate_findings.py")
    assert 'add_argument("--taxonomy-version", default="0.6")' in adjudicator

    active_report_paths = [
        "workflows/evidence-audit/SKILL.md",
        "workflows/anti-autoresearch/SKILL.md",
        *[
            str(path.relative_to(ROOT))
            for path in sorted((ROOT / "skills").glob("*/SKILL.md"))
        ],
    ]
    for relative in active_report_paths:
        text = read(relative)
        if "--taxonomy-version" in text:
            assert "--taxonomy-version 0.5" not in text, relative
        if "TAXONOMY_VERSION" in text:
            assert "TAXONOMY_VERSION" in text and "= 0.5" not in text, relative

    assert 'CURRENT_TAXONOMY_VERSION = "0.6"' in read("eval/run_eval.py")


def test_claim_schema_adds_research_types_and_evidence_properties():
    schema = _load_schema("claims.schema.json")
    claim = schema["properties"]["claims"]["items"]

    assert {"research_claim", "evidence_statement", "hypothesis"} <= set(
        claim["properties"]["type"]["enum"]
    )
    assert set(claim["properties"]) >= {
        "query_ids",
        "evidence_direction",
        "verification_status",
        "load_bearing",
        "support_basis",
    }
    assert claim["properties"]["evidence_direction"]["enum"] == [
        "supports",
        "contradicts",
        "limits",
        "unclear",
    ]
    assert claim["properties"]["verification_status"]["enum"] == [
        "VERIFIED",
        "UNVERIFIED",
        "VERIFY_PENDING",
    ]
    assert claim["properties"]["support_basis"]["enum"] == [
        "quoted_span",
        "annotation",
        "metadata",
        "relevance_score",
        "none",
    ]
    assert claim["properties"]["query_ids"]["type"] == "array"
    assert claim["properties"]["query_ids"]["items"] == {"type": "string"}
    assert claim["properties"]["load_bearing"]["type"] == "boolean"


def test_finding_schema_adds_evidence_audit_skill():
    schema = _load_schema("finding.schema.json")

    assert "evidence-audit" in schema["properties"]["skill"]["enum"]


def test_report_schema_adds_research_evidence_dimension():
    schema = _load_schema("report.schema.json")

    assert "research_evidence" in schema["properties"]["dimension_verdicts"]["properties"]


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

    for forbidden in [
        "WebSearch",
        "Zotero retrieval",
        "same-context verdict",
        "audit-until-clean",
        "non-deterministic final verdict",
    ]:
        assert forbidden not in text

    assert "retrieval-free" in text.lower()
    assert "overall_verdict" in text
    assert "only" in text


def test_workflow_declares_bounded_inputs_outputs_and_order():
    text = read("workflows/evidence-audit/SKILL.md")
    for token in [
        "evidence-audit.deterministic.findings.json",
        "evidence-audit.semantic.findings.json",
        "report.json",
        "REPORT.md",
        "absolute package path",
        "rubric",
        "observability level",
        "no authoring chat context",
    ]:
        assert token in text

    order_block = text.split("## Required order", 1)[1].split("## Invariants", 1)[0]
    order = [
        order_block.index("validate package"),
        order_block.index("check_evidence_coverage.py"),
        order_block.index("fresh isolated Codex reviewer"),
        order_block.index("validate semantic finding anchors"),
        order_block.index("adjudicate_findings.py"),
        order_block.index("REPORT.md"),
    ]
    assert order == sorted(order)


def test_reviewer_independence_has_two_enforceable_properties():
    text = read("references/reviewer-independence.md")
    assert "frozen package" in text
    assert "no authoring chat context" in text
    assert "cannot compute or write `overall_verdict`" in text


def test_workflow_validates_declared_package_schema_semantics():
    text = read("workflows/evidence-audit/SKILL.md")

    for token in [
        "ledger_version",
        "source_files",
        "claim_id",
        "text_span",
        "location",
        "query_ids",
        "evidence_direction",
        "verification_status",
        "support_basis",
        "value",
        "branch_id",
        "source_policy",
        "artifact_hashes",
        "QUERY_STATUSES",
        "SEARCHED",
        "NO_HIT",
        "UNVERIFIED",
        "UNSEARCHABLE",
        "ERROR",
        "evidence_directions",
        "supports",
        "contradicts",
        "limits",
        "unclear",
        "EXTRACTORS",
        "latex_regex",
        "CONFIDENCES",
        "VALUE_DIRECTIONS",
        "AGGREGATIONS",
        "require_object(value, value_path)",
        "require_string_list(query[\"evidence_item_keys\"]",
        "type(query_id) is not str",
        "type(status) is not str",
        "import math",
        "math.isfinite(value)",
        "must be a finite number",
    ]:
        assert token in text


def test_workflow_validator_rejects_nonfinite_numbers_and_keeps_strict_integers(tmp_path):
    validator = _workflow_python_block('python3 - "$CLAIMS" "$COVERAGE" <<\'PY\'\n')
    claims = {
        "ledger_version": "0.1",
        "paper_id": "paper-1",
        "observability_level": 0,
        "source_files": [],
        "claims": [],
    }
    coverage = {
        "schema_version": "0.1",
        "branch_id": "branch-1",
        "source_policy": "local",
        "queries": [],
        "artifact_hashes": {},
    }
    claims_path = tmp_path / "claims.json"
    coverage_path = tmp_path / "query_coverage.json"

    def run(normalized):
        document = dict(claims)
        document["claims"] = [{
            "claim_id": "C001",
            "type": "number",
            "text_span": "reported value",
            "location": {"file": "paper.md"},
            "value": {"normalized": normalized},
        }]
        claims_path.write_text(json.dumps(document), encoding="utf-8")
        coverage_path.write_text(json.dumps(coverage), encoding="utf-8")
        return _run_python_block(validator, claims_path, coverage_path)

    assert run(7).returncode == 0
    assert run(float("nan")).returncode != 0
    assert run(float("inf")).returncode != 0
    assert run(True).returncode != 0


def test_workflow_normalizer_fail_closes_malformed_scalars_and_anchors_claim_hash(tmp_path):
    normalizer = _workflow_python_block(
        'python3 - "$CLAIMS" "$SEMANTIC" "$SEMANTIC.tmp" <<\'PY\'\n'
    )
    claims_path = tmp_path / "claims.json"
    semantic_path = tmp_path / "semantic.json"
    claims_path.write_text(json.dumps({
        "claims": [
            {
                "claim_id": "C001",
                "text_span": "A supported claim with evidence",
                "location": {"file": "paper.md", "line": 5},
                "evidence_anchor": "validated-claim-hash",
            },
            {
                "claim_id": "C002",
                "text_span": "A second supported claim",
                "location": {"file": "paper.md", "line": 6},
            },
        ]
    }), encoding="utf-8")
    semantic_path.write_text(json.dumps([
        {
            "severity": [],
            "verdict_local": {},
            "false_positive_risk": ["low"],
            "evidence": [{
                "claim_id": "C001",
                "span": "A supported claim with evidence",
                "artifact_hash": "reviewer-controlled-wrong-hash",
            }],
        },
        {
            "severity": {"unexpected": "critical"},
            "verdict_local": ["fail"],
            "false_positive_risk": {"unexpected": "low"},
            "evidence": [{
                "claim_id": "C002",
                "span": "A second supported claim",
                "artifact_hash": "reviewer-controlled-wrong-hash",
            }],
        },
    ]), encoding="utf-8")

    result = _run_python_block(
        normalizer,
        claims_path,
        semantic_path,
        semantic_path.with_suffix(".tmp"),
    )
    assert result.returncode == 0, result.stderr

    findings = json.loads(semantic_path.read_text(encoding="utf-8"))
    assert findings[0]["severity"] == "info"
    assert findings[0]["verdict_local"] == "warn"
    assert findings[0]["false_positive_risk"] == "high"
    assert findings[0]["evidence"][0]["artifact_hash"] == "validated-claim-hash"
    assert findings[1]["severity"] == "info"
    assert findings[1]["verdict_local"] == "warn"
    assert findings[1]["false_positive_risk"] == "high"
    assert "artifact_hash" not in findings[1]["evidence"][0]


def test_workflow_normalizes_malformed_review_data_and_rechecks_freeze_boundary():
    text = read("workflows/evidence-audit/SKILL.md")

    for token in [
        "if not isinstance(claim_id, str)",
        "if not isinstance(raw_evidence, list)",
        "claim_map.get(claim_id)",
        'entry["span"] = span',
        "pattern_id",
        "if not isinstance(pattern_id, str)",
        "requires_external_check",
        "type(requires_external_check) is not bool",
        "finding[\"requires_external_check\"] = requires_external_check",
        "entry[\"location\"] =",
        "entry[\"artifact_hash\"] = artifact_hash",
        "CLAIMS_SHA_NOW",
        "COVERAGE_SHA_NOW",
        "restart from package validation",
    ]:
        assert token in text

    normalize_at = text.index("## Step 4 — Validate semantic finding anchors")
    final_freeze_at = text.index("CLAIMS_SHA_NOW")
    adjudicate_at = text.index('python3 "$ROOT/tools/adjudicate_findings.py"')
    assert normalize_at < final_freeze_at < adjudicate_at


def test_workflow_keeps_one_luna_reviewer_and_adjudicator_verdict_ownership():
    text = read("workflows/evidence-audit/SKILL.md")

    assert text.count("model: gpt-5.6-luna") == 1
    assert '{"model_reasoning_effort": "max"}' in text
    assert text.count("mcp__codex__codex:") == 1
    assert "Only `tools/adjudicate_findings.py` may produce that field" in text


def test_workflow_tracks_reviewer_availability_outside_package():
    text = read("workflows/evidence-audit/SKILL.md")

    for token in [
        "temporary coverage status map",
        "COVERAGE_STATUS",
        "reviewer success",
        "completed",
        "timeout or unparseable",
        "review_unavailable",
        '"evidence-audit": "completed"',
        '"evidence-audit": "review_unavailable"',
        'coverage["evidence-audit"] = status',
        '--coverage "$COVERAGE_STATUS"',
    ]:
        assert token in text

    assert "outside the package" in text
    assert "open one fresh isolated Codex reviewer" in text
