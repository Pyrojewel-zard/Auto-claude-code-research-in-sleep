import json
import os
import subprocess
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
sys.path.insert(0, str(TOOLS))

from resolve_anti_autoresearch import resolve_anti  # noqa: E402
from update_anti_lock import update_lock  # noqa: E402


REPO_URL = "git@github.com:wanshuiyin/Anti-Autoresearch.git"
LOCKED_SHA = "0123456789abcdef0123456789abcdef01234567"
COMMITTED_LOCK_PATH = TOOLS / "anti-autoresearch.lock.json"
COMMITTED_LOCKED_SHA = "78fdac2580ac8005cafe9b543a78458e30f19c01"


def _run(*args, cwd=None):
    return subprocess.run(
        list(args), cwd=cwd, check=True, capture_output=True, text=True
    )


def _git(repo, *args):
    return _run("git", "-C", str(repo), *args)


def _write_checkout(repo, *, contract_version="0.1", with_workflow=True, eval_code="raise SystemExit(0)"):
    repo.mkdir(parents=True)
    (repo / "schemas").mkdir()
    (repo / "eval").mkdir()
    (repo / "schemas" / "query_coverage.schema.json").write_text(
        json.dumps(
            {
                "properties": {
                    "schema_version": {"const": contract_version},
                }
            }
        ),
        encoding="utf-8",
    )
    (repo / "eval" / "run_eval.py").write_text(
        f"#!/usr/bin/env python3\n{eval_code}\n", encoding="utf-8"
    )
    if with_workflow:
        workflow = repo / "workflows" / "evidence-audit"
        workflow.mkdir(parents=True)
        (workflow / "SKILL.md").write_text("# evidence audit\n", encoding="utf-8")
    _git(repo, "init", "-q")
    _git(repo, "config", "user.email", "tests@example.invalid")
    _git(repo, "config", "user.name", "resolver tests")
    _git(repo, "add", ".")
    _git(repo, "commit", "-qm", "fixture")
    return _git(repo, "rev-parse", "HEAD").stdout.strip()


def _write_lock(path, *, repo_url=REPO_URL, commit=LOCKED_SHA, contract_version="0.1"):
    path.write_text(
        json.dumps(
            {
                "repo_url": repo_url,
                "commit": commit,
                "contract_version": contract_version,
            }
        ),
        encoding="utf-8",
    )


def _run_updater(checkout, output, *, contract_version="0.1"):
    return subprocess.run(
        [
            sys.executable,
            str(TOOLS / "update_anti_lock.py"),
            "--repo-url",
            REPO_URL,
            "--checkout",
            str(checkout),
            "--contract-version",
            contract_version,
            "--out",
            str(output),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )


def test_update_lock_rejects_short_sha(tmp_path):
    with pytest.raises(ValueError):
        update_lock(tmp_path / "lock.json", REPO_URL, "abc123", "0.1")


def test_update_lock_writes_url_commit_and_contract(tmp_path):
    lock_path = tmp_path / "nested" / "lock.json"

    update_lock(lock_path, REPO_URL, LOCKED_SHA, "0.1")

    assert json.loads(lock_path.read_text(encoding="utf-8")) == {
        "repo_url": REPO_URL,
        "commit": LOCKED_SHA,
        "contract_version": "0.1",
    }


def test_committed_lock_preserves_exact_tested_pin():
    assert json.loads(COMMITTED_LOCK_PATH.read_text(encoding="utf-8")) == {
        "repo_url": REPO_URL,
        "commit": COMMITTED_LOCKED_SHA,
        "contract_version": "0.1",
    }


@pytest.mark.skipif(
    not os.environ.get("ARIS_VALIDATE_ANTI_REMOTE"),
    reason="set ARIS_VALIDATE_ANTI_REMOTE=1 to opt into the network check",
)
def test_committed_lock_remote_advertises_exact_pin():
    lock = json.loads(COMMITTED_LOCK_PATH.read_text(encoding="utf-8"))
    result = subprocess.run(
        ["git", "ls-remote", "--exit-code", lock["repo_url"]],
        check=False,
        capture_output=True,
        text=True,
        timeout=30,
    )

    assert result.returncode == 0, result.stderr or result.stdout
    advertised_commits = {
        line.split(maxsplit=1)[0]
        for line in result.stdout.splitlines()
        if line.strip()
    }
    assert lock["commit"] in advertised_commits


def test_updater_reads_clean_checkout_head(tmp_path):
    checkout = tmp_path / "checkout"
    head = _write_checkout(checkout)
    output = tmp_path / "lock.json"

    result = _run_updater(checkout, output)

    assert result.returncode == 0, result.stderr
    assert json.loads(output.read_text(encoding="utf-8"))["commit"] == head


@pytest.mark.parametrize(
    ("fixture_kwargs", "expected_message"),
    [
        ({"with_workflow": False}, "workflow"),
        ({"eval_code": "raise SystemExit(1)"}, "eval"),
    ],
)
def test_updater_rejects_invalid_checkout(tmp_path, fixture_kwargs, expected_message):
    checkout = tmp_path / "checkout"
    _write_checkout(checkout, **fixture_kwargs)
    output = tmp_path / "lock.json"

    result = _run_updater(checkout, output)

    assert result.returncode != 0
    assert expected_message in (result.stderr + result.stdout).lower()


def test_updater_rejects_dirty_checkout(tmp_path):
    checkout = tmp_path / "checkout"
    _write_checkout(checkout)
    (checkout / "untracked.txt").write_text("dirty\n", encoding="utf-8")

    result = _run_updater(checkout, tmp_path / "lock.json")

    assert result.returncode != 0
    assert "dirty" in (result.stderr + result.stdout).lower()


def test_local_checkout_must_match_contract(tmp_path):
    local_repo = tmp_path / "local"
    commit = _write_checkout(local_repo)
    lock_path = tmp_path / "lock.json"
    _write_lock(lock_path, commit=commit)

    result = resolve_anti(lock_path, local_repo, tmp_path / "cache")

    assert result.repo_path == local_repo.resolve()
    assert result.commit == commit
    assert result.source_kind == "local"
    assert result.contract_version == "0.1"


def test_local_checkout_rejects_contract_mismatch(tmp_path):
    local_repo = tmp_path / "local"
    commit = _write_checkout(local_repo, contract_version="0.2")
    lock_path = tmp_path / "lock.json"
    _write_lock(lock_path, commit=commit, contract_version="0.1")

    with pytest.raises(ValueError, match="contract"):
        resolve_anti(lock_path, local_repo, tmp_path / "cache")


def test_environment_local_override_wins_over_distribution(tmp_path, monkeypatch):
    local_repo = tmp_path / "local"
    commit = _write_checkout(local_repo)
    lock_path = tmp_path / "lock.json"
    _write_lock(lock_path, repo_url="not-a-clone-source", commit=commit)
    monkeypatch.setenv("ARIS_ANTI_REPO", str(local_repo))

    result = resolve_anti(lock_path, None, tmp_path / "cache")

    assert result.source_kind == "local"
    assert result.commit == commit


def test_resolver_json_cli_exposes_structured_resolution(tmp_path):
    local_repo = tmp_path / "local"
    commit = _write_checkout(local_repo)
    lock_path = tmp_path / "lock.json"
    _write_lock(lock_path, commit=commit)
    environment = os.environ.copy()
    environment["ARIS_ANTI_REPO"] = str(local_repo)

    result = subprocess.run(
        [
            sys.executable,
            str(TOOLS / "resolve_anti_autoresearch.py"),
            "--lock",
            str(lock_path),
            "--cache-root",
            str(tmp_path / "cache"),
            "--json",
        ],
        cwd=ROOT,
        env=environment,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout) == {
        "repo_path": str(local_repo.resolve()),
        "commit": commit,
        "source_kind": "local",
        "contract_version": "0.1",
    }


def test_distribution_resolution_is_commit_pinned(tmp_path, monkeypatch):
    source_repo = tmp_path / "source"
    commit = _write_checkout(source_repo)
    lock_path = tmp_path / "lock.json"
    _write_lock(lock_path, repo_url=str(source_repo), commit=commit)
    monkeypatch.delenv("ARIS_ANTI_REPO", raising=False)

    result = resolve_anti(lock_path, None, tmp_path / "cache")

    assert result.source_kind == "pinned"
    assert result.commit == commit
    assert result.repo_path.is_relative_to((tmp_path / "cache").resolve())
    assert result.repo_path.name == commit


def test_distribution_resolution_rejects_untracked_cache_tampering(
    tmp_path, monkeypatch
):
    source_repo = tmp_path / "source"
    commit = _write_checkout(source_repo)
    lock_path = tmp_path / "lock.json"
    cache_root = tmp_path / "cache"
    _write_lock(lock_path, repo_url=str(source_repo), commit=commit)
    monkeypatch.delenv("ARIS_ANTI_REPO", raising=False)

    result = resolve_anti(lock_path, None, cache_root)
    (result.repo_path / "untracked.txt").write_text("tampered\n", encoding="utf-8")

    with pytest.raises(ValueError, match="dirty"):
        resolve_anti(lock_path, None, cache_root)
    assert (
        (result.repo_path / "untracked.txt").read_text(encoding="utf-8")
        == "tampered\n"
    )


def test_distribution_resolution_rejects_tracked_cache_tampering(
    tmp_path, monkeypatch
):
    source_repo = tmp_path / "source"
    commit = _write_checkout(source_repo)
    lock_path = tmp_path / "lock.json"
    cache_root = tmp_path / "cache"
    _write_lock(lock_path, repo_url=str(source_repo), commit=commit)
    monkeypatch.delenv("ARIS_ANTI_REPO", raising=False)

    result = resolve_anti(lock_path, None, cache_root)
    schema_path = result.repo_path / "schemas" / "query_coverage.schema.json"
    schema_path.write_text('{"tampered": true}\n', encoding="utf-8")

    with pytest.raises(ValueError, match="dirty"):
        resolve_anti(lock_path, None, cache_root)
    assert schema_path.read_text(encoding="utf-8") == '{"tampered": true}\n'
