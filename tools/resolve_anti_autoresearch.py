#!/usr/bin/env python3
"""Resolve the local or pinned Anti-Autoresearch checkout for ARIS."""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from dataclasses import asdict, dataclass
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
DEFAULT_LOCK_PATH = Path(__file__).resolve().with_name("anti-autoresearch.lock.json")


@dataclass(frozen=True)
class Resolution:
    repo_path: Path
    commit: str
    source_kind: str
    contract_version: str

    def as_json(self) -> dict[str, str]:
        result = asdict(self)
        result["repo_path"] = str(self.repo_path)
        return result


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


def _load_lock(lock_path: Path) -> dict[str, str]:
    try:
        payload = json.loads(Path(lock_path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"cannot read Anti lock: {lock_path}") from exc
    if not isinstance(payload, dict):
        raise ValueError("Anti lock must contain a JSON object")
    missing = {"repo_url", "commit", "contract_version", "vendor_path"} - payload.keys()
    if missing:
        raise ValueError(f"Anti lock is missing fields: {', '.join(sorted(missing))}")
    return {
        "repo_url": _require_text(payload["repo_url"], "repo_url"),
        "commit": _validate_commit(payload["commit"]),
        "contract_version": _require_text(
            payload["contract_version"], "contract_version"
        ),
        "vendor_path": _validate_vendor_path(payload["vendor_path"]),
    }


def _git(repo: Path, *args: str, check: bool = True) -> str:
    try:
        result = subprocess.run(
            ["git", "-C", str(repo), *args],
            check=check,
            capture_output=True,
            text=True,
        )
    except OSError as exc:
        raise ValueError(f"could not run git: {exc}") from exc
    if check and result.returncode != 0:
        detail = (result.stderr or result.stdout).strip()
        raise ValueError(
            f"git {' '.join(args)} failed for {repo}"
            + (f": {detail}" if detail else "")
        )
    return result.stdout.strip()


def _head(repo: Path) -> str:
    if not repo.is_dir():
        raise ValueError(f"Anti local checkout does not exist: {repo}")
    return _validate_commit(_git(repo, "rev-parse", "HEAD"))


def _assert_clean(repo: Path) -> None:
    status = _git(repo, "status", "--porcelain=v1", "--untracked-files=all")
    if status:
        raise ValueError(f"Anti checkout is dirty: {repo}")


def _assert_required_paths(repo: Path) -> None:
    missing = [
        str(relative_path)
        for relative_path in REQUIRED_ANTI_PATHS
        if not (repo / relative_path).is_file()
    ]
    if missing:
        raise ValueError("missing Anti required file(s): " + ", ".join(missing))


def _contract_version(repo: Path) -> str:
    schema_path = repo / CONTRACT_SCHEMA_PATH
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


def _verify_contract(repo: Path, expected: str) -> str:
    detected = _contract_version(repo)
    if detected != expected:
        raise ValueError(
            "Anti contract version mismatch: "
            f"expected {expected}, detected {detected}"
        )
    return detected


def _project_root(lock_path: Path) -> Path:
    lock_path = Path(lock_path).expanduser().resolve()
    if lock_path.parent.name == "tools":
        return lock_path.parent.parent
    return lock_path.parent


def _vendored_path(lock_path: Path, vendor_path: str) -> Path:
    root = _project_root(lock_path)
    relative = PurePosixPath(_validate_vendor_path(vendor_path))
    candidate = (root / Path(*relative.parts)).resolve()
    try:
        candidate.relative_to(root.resolve())
    except ValueError as exc:
        raise ValueError("Anti vendor path escapes the ARIS checkout") from exc
    return candidate


def _assert_vendored_tree(repo: Path) -> None:
    if not repo.is_dir():
        raise ValueError(f"vendored Anti tree does not exist: {repo}")
    nested_metadata = [
        path for path in repo.rglob(".git") if path.name == ".git"
    ]
    if nested_metadata:
        raise ValueError("vendored Anti tree contains nested .git metadata")
    _assert_required_paths(repo)


def _local_override(local_repo: Path | None) -> Path | None:
    if local_repo is not None:
        return Path(local_repo).expanduser().resolve()
    configured = os.environ.get("ARIS_ANTI_REPO", "").strip()
    if configured:
        return Path(configured).expanduser().resolve()
    return None


def _resolve_local(
    repo: Path, expected_contract_version: str
) -> Resolution:
    _assert_clean(repo)
    commit = _head(repo)
    _assert_required_paths(repo)
    contract_version = _verify_contract(repo, expected_contract_version)
    _assert_clean(repo)
    return Resolution(repo, commit, "local", contract_version)


def resolve_anti(
    lock_path: Path, local_repo: Path | None, cache_root: Path
) -> Resolution:
    """Resolve the vendored Anti tree, with an explicit local override."""

    lock = _load_lock(Path(lock_path))
    local = _local_override(local_repo)
    if local is not None:
        return _resolve_local(local, lock["contract_version"])

    del cache_root  # retained in the API for callers of the former resolver
    vendor_path = _vendored_path(Path(lock_path), lock["vendor_path"])
    _assert_vendored_tree(vendor_path)
    contract_version = _verify_contract(vendor_path, lock["contract_version"])
    return Resolution(vendor_path, lock["commit"], "vendored", contract_version)


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Resolve the ARIS Anti checkout.")
    parser.add_argument(
        "--lock", "--lock-path", dest="lock_path", type=Path, default=DEFAULT_LOCK_PATH
    )
    parser.add_argument("--local-repo", type=Path)
    parser.add_argument(
        "--cache-root",
        type=Path,
        default=Path.home() / ".cache" / "aris",
        help="deprecated compatibility option; ignored for vendored resolution",
    )
    parser.add_argument("--json", action="store_true", dest="as_json")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(sys.argv[1:] if argv is None else argv)
    try:
        result = resolve_anti(args.lock_path, args.local_repo, args.cache_root)
    except (OSError, ValueError) as exc:
        print(f"resolve failed: {exc}", file=sys.stderr)
        return 1

    if args.as_json:
        print(json.dumps(result.as_json(), ensure_ascii=False, sort_keys=True))
    else:
        print(f"{result.source_kind}: {result.repo_path} @ {result.commit}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
