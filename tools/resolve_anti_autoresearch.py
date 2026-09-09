#!/usr/bin/env python3
"""Resolve the local or pinned Anti-Autoresearch checkout for ARIS."""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from dataclasses import asdict, dataclass
from pathlib import Path


COMMIT_RE = re.compile(r"[0-9a-f]{40}")
CONTRACT_SCHEMA_PATH = Path("schemas/query_coverage.schema.json")
CACHE_NAMESPACE = "anti-autoresearch"
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


def _load_lock(lock_path: Path) -> dict[str, str]:
    try:
        payload = json.loads(Path(lock_path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"cannot read Anti lock: {lock_path}") from exc
    if not isinstance(payload, dict):
        raise ValueError("Anti lock must contain a JSON object")
    missing = {"repo_url", "commit", "contract_version"} - payload.keys()
    if missing:
        raise ValueError(f"Anti lock is missing fields: {', '.join(sorted(missing))}")
    return {
        "repo_url": _require_text(payload["repo_url"], "repo_url"),
        "commit": _validate_commit(payload["commit"]),
        "contract_version": _require_text(
            payload["contract_version"], "contract_version"
        ),
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
        raise ValueError(f"pinned Anti cache is dirty: {repo}")


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
    commit = _head(repo)
    contract_version = _verify_contract(repo, expected_contract_version)
    return Resolution(repo, commit, "local", contract_version)


def _clone_pinned(repo_url: str, commit: str, cache_root: Path) -> Path:
    cache_root = Path(cache_root).expanduser().resolve()
    cache_path = cache_root / CACHE_NAMESPACE / commit
    cache_path.parent.mkdir(parents=True, exist_ok=True)

    if not cache_path.exists():
        try:
            subprocess.run(
                ["git", "clone", "--no-tags", repo_url, str(cache_path)],
                check=True,
                capture_output=True,
                text=True,
            )
        except (OSError, subprocess.CalledProcessError) as exc:
            if cache_path.exists():
                shutil.rmtree(cache_path)
            detail = getattr(exc, "stderr", "") or str(exc)
            raise ValueError(f"could not clone pinned Anti repository: {detail.strip()}") from exc
    elif not cache_path.is_dir():
        raise ValueError(f"pinned Anti cache path is not a directory: {cache_path}")

    # Reject an existing dirty cache before fetch/checkout can alter it.  The
    # final check below closes the path before a dirty checkout is returned.
    _assert_clean(cache_path)

    # A commit-addressed path is never accepted merely because it exists.  The
    # object must be present and HEAD must be detached at the lock's exact SHA.
    object_check = _git(
        cache_path, "rev-parse", "--verify", f"{commit}^{{commit}}", check=False
    )
    if not object_check:
        try:
            _git(cache_path, "fetch", "--no-tags", "origin", commit)
        except ValueError as exc:
            raise ValueError(
                f"pinned Anti commit {commit} is unavailable in cache {cache_path}"
            ) from exc
    _git(cache_path, "checkout", "--detach", commit)
    actual = _head(cache_path)
    if actual != commit:
        raise ValueError(
            f"pinned Anti checkout is at {actual}, expected locked commit {commit}"
        )
    _assert_clean(cache_path)
    return cache_path


def resolve_anti(
    lock_path: Path, local_repo: Path | None, cache_root: Path
) -> Resolution:
    """Resolve an Anti checkout, honoring local development overrides first."""

    lock = _load_lock(Path(lock_path))
    local = _local_override(local_repo)
    if local is not None:
        return _resolve_local(local, lock["contract_version"])

    cache_path = _clone_pinned(lock["repo_url"], lock["commit"], Path(cache_root))
    contract_version = _verify_contract(cache_path, lock["contract_version"])
    _assert_clean(cache_path)
    return Resolution(cache_path, lock["commit"], "pinned", contract_version)


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
