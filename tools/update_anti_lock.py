#!/usr/bin/env python3
"""Validate an Anti-Autoresearch checkout and write its ARIS lock entry."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path
from pathlib import PurePosixPath


COMMIT_RE = re.compile(r"[0-9a-f]{40}")
VENDOR_PATH = "vendor/anti-autoresearch"
REQUIRED_ANTI_PATHS = (
    Path("workflows/anti-autoresearch/SKILL.md"),
    Path("workflows/evidence-audit/SKILL.md"),
    Path("eval/run_eval.py"),
    Path("tools/adjudicate_findings.py"),
    Path("tools/build_claim_ledger.py"),
    Path("tools/check_evidence_coverage.py"),
    Path("schemas/artifact_manifest.schema.json"),
    Path("schemas/claims.schema.json"),
    Path("schemas/finding.schema.json"),
    Path("schemas/query_coverage.schema.json"),
    Path("schemas/report.schema.json"),
)
CONTRACT_SCHEMA_PATH = Path("schemas/query_coverage.schema.json")
EVAL_PATH = Path("eval/run_eval.py")


def _require_text(value: str, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be a non-empty string")
    return value.strip()


def _validate_commit(commit: str) -> str:
    commit = _require_text(commit, "commit")
    if COMMIT_RE.fullmatch(commit) is None:
        raise ValueError("commit must be an exact 40-character lowercase SHA-1")
    return commit


def _validate_vendor_path(vendor_path: str) -> str:
    vendor_path = _require_text(vendor_path, "vendor_path")
    if "\\" in vendor_path:
        raise ValueError("vendor_path must use POSIX separators")
    parsed = PurePosixPath(vendor_path)
    if parsed.is_absolute() or ".." in parsed.parts or "." in parsed.parts:
        raise ValueError("vendor_path must be a relative path without dot segments")
    if str(parsed) != VENDOR_PATH:
        raise ValueError(f"vendor_path must be {VENDOR_PATH}")
    return str(parsed)


def _git(checkout: Path, *args: str) -> str:
    try:
        result = subprocess.run(
            ["git", "-C", str(checkout), *args],
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        detail = getattr(exc, "stderr", "") or str(exc)
        raise ValueError(f"git {' '.join(args)} failed: {detail.strip()}") from exc
    return result.stdout.strip()


def _contract_version(checkout: Path) -> str:
    schema_path = checkout / CONTRACT_SCHEMA_PATH
    if not schema_path.is_file():
        raise ValueError(f"missing Anti contract schema: {CONTRACT_SCHEMA_PATH}")
    try:
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        version = schema["properties"]["schema_version"]["const"]
    except (OSError, json.JSONDecodeError, KeyError, TypeError) as exc:
        raise ValueError(
            f"cannot read Anti contract version from {CONTRACT_SCHEMA_PATH}"
        ) from exc
    return _require_text(version, "Anti contract version")


def _assert_required_paths(checkout: Path) -> None:
    missing = [
        str(relative_path)
        for relative_path in REQUIRED_ANTI_PATHS
        if not (checkout / relative_path).is_file()
    ]
    if missing:
        raise ValueError("missing Anti required file(s): " + ", ".join(missing))


def _assert_clean(checkout: Path) -> None:
    status = _git(checkout, "status", "--porcelain=v1", "--untracked-files=all")
    if status:
        raise ValueError("Anti checkout is dirty")


def validate_checkout(checkout: Path, expected_contract_version: str) -> str:
    """Validate a tested checkout and return its exact HEAD commit."""

    checkout = Path(checkout).expanduser().resolve()
    expected_contract_version = _require_text(
        expected_contract_version, "contract_version"
    )
    if not checkout.is_dir():
        raise ValueError(f"Anti checkout does not exist: {checkout}")

    _assert_clean(checkout)
    commit = _validate_commit(_git(checkout, "rev-parse", "HEAD"))
    _assert_required_paths(checkout)

    detected_contract_version = _contract_version(checkout)
    if detected_contract_version != expected_contract_version:
        raise ValueError(
            "Anti contract version mismatch: "
            f"expected {expected_contract_version}, detected {detected_contract_version}"
        )

    try:
        result = subprocess.run(
            [sys.executable, str(checkout / EVAL_PATH)],
            cwd=str(checkout),
            check=False,
            capture_output=True,
            text=True,
        )
    except OSError as exc:
        raise ValueError(f"could not run Anti eval: {exc}") from exc
    if result.returncode != 0:
        detail = (result.stderr or result.stdout).strip()
        raise ValueError(
            f"Anti eval failed with exit code {result.returncode}"
            + (f": {detail}" if detail else "")
        )

    _assert_clean(checkout)
    return commit


def update_lock(
    lock_path: Path,
    repo_url: str,
    commit: str,
    contract_version: str,
    vendor_path: str = VENDOR_PATH,
) -> None:
    """Write one validated Anti-Autoresearch lock entry."""

    repo_url = _require_text(repo_url, "repo_url")
    commit = _validate_commit(commit)
    contract_version = _require_text(contract_version, "contract_version")
    vendor_path = _validate_vendor_path(vendor_path)
    lock_path = Path(lock_path)
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "repo_url": repo_url,
        "commit": commit,
        "contract_version": contract_version,
        "vendor_path": vendor_path,
    }
    lock_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate a tested Anti checkout and write its ARIS lock."
    )
    parser.add_argument("--repo-url", required=True)
    parser.add_argument("--checkout", required=True, type=Path)
    parser.add_argument("--contract-version", required=True)
    parser.add_argument("--vendor-path", default=VENDOR_PATH)
    parser.add_argument("--out", required=True, type=Path)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(sys.argv[1:] if argv is None else argv)
    try:
        commit = validate_checkout(args.checkout, args.contract_version)
        update_lock(
            args.out,
            args.repo_url,
            commit,
            args.contract_version,
            args.vendor_path,
        )
    except (OSError, ValueError) as exc:
        print(f"update failed: {exc}", file=sys.stderr)
        return 1
    print(f"wrote {args.out} at {commit}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
