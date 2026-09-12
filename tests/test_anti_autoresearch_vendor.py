import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
VENDOR = ROOT / "vendor" / "anti-autoresearch"
LOCK = ROOT / "tools" / "anti-autoresearch.lock.json"
EXPECTED_COMMIT = "78fdac2580ac8005cafe9b543a78458e30f19c01"


REQUIRED = (
    "workflows/anti-autoresearch/SKILL.md",
    "workflows/evidence-audit/SKILL.md",
    "eval/run_eval.py",
    "tools/adjudicate_findings.py",
    "tools/build_claim_ledger.py",
    "tools/check_evidence_coverage.py",
    "schemas/artifact_manifest.schema.json",
    "schemas/claims.schema.json",
    "schemas/finding.schema.json",
    "schemas/query_coverage.schema.json",
    "schemas/report.schema.json",
)


def test_vendor_is_a_complete_clean_ant_snapshot():
    assert VENDOR.is_dir()
    assert sum(1 for path in VENDOR.rglob("*") if path.is_file()) >= 74
    for relative in REQUIRED:
        assert (VENDOR / relative).is_file(), relative

    forbidden_names = {".git", ".pytest_cache", "__pycache__", ".eval_run"}
    forbidden = [
        path
        for path in VENDOR.rglob("*")
        if path.name in forbidden_names
        or path.as_posix().endswith("/eval/fixtures/synthetic_corruptions")
    ]
    assert forbidden == []


def test_lock_records_the_vendored_provenance():
    lock = json.loads(LOCK.read_text(encoding="utf-8"))
    assert lock["commit"] == EXPECTED_COMMIT
    assert lock["vendor_path"] == "vendor/anti-autoresearch"
    assert lock["contract_version"] == "0.1"
    assert lock["repo_url"] == "git@github.com:wanshuiyin/Anti-Autoresearch.git"


def test_vendored_contract_schema_is_valid_json():
    schema = json.loads(
        (VENDOR / "schemas" / "query_coverage.schema.json").read_text(
            encoding="utf-8"
        )
    )
    assert schema["properties"]["schema_version"]["const"] == "0.1"


@pytest.mark.parametrize("relative", REQUIRED)
def test_vendor_required_paths_are_regular_files(relative):
    path = VENDOR / relative
    assert path.is_file()
    assert not path.is_symlink()
