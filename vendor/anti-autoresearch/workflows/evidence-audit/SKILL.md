---
name: evidence-audit
description: "Use when auditing a completed research branch from a frozen claims-and-query-coverage package."
argument-hint: [package-dir]
allowed-tools: Bash(*), Read, Write, mcp__codex__codex
---

# /evidence-audit — the lightweight branch audit

Run a detect-only evidence audit on **$ARGUMENTS**, a directory that already
contains the completed branch package. The package is the boundary of this
workflow: it reads the package's `claims.json` and `query_coverage.json`, writes
findings and the existing report artifacts, and performs no source discovery.

## Required order

The order is fixed and is not an interactive loop:

```text
validate package
-> run deterministic coverage checker (`check_evidence_coverage.py`)
-> open one fresh isolated Codex reviewer
-> validate semantic finding anchors
-> run existing deterministic adjudicator (`adjudicate_findings.py`)
-> render report (`REPORT.md`)
```

The checker and reviewer propose findings. The existing adjudicator is the only
component allowed to compute `overall_verdict`; this workflow never creates a
second verdict system.

## Invariants

- **Retrieval-free:** read only the supplied package and the local Anti tools. Do
  not use network, browser, repository, or source lookup during this workflow.
- **Detect-only:** never edit `claims.json`, `query_coverage.json`, the researched
  artifact, or any other authoring input. Normalizing the generated semantic
  findings file is allowed; it is an audit output, not a research artifact.
- **One pass:** run one deterministic checker, one semantic reviewer, one anchor
  validation pass, and one adjudicator invocation. Do not repeat a run because a
  report is clean; rerun only after the frozen package or its declared inputs
  change.
- **Adjudicator ownership:** neither the reviewer nor this skill may compute or write
  `overall_verdict`. Only `tools/adjudicate_findings.py` may produce that field in
  `report.json`.
- **Frozen inputs:** the reviewer receives a frozen package and no authoring chat
  context. If either input JSON changes after validation, stop and restart from
  package validation.
- **Reviewer coverage:** a temporary coverage status map outside the package
  records the single review outcome. reviewer success marks evidence-audit
  completed; timeout or unparseable response marks it review_unavailable.
  All other tracks are explicitly not_applicable so this skill does not claim
  to have run them.

## Step 1 — Validate the package

Resolve one absolute package path and require both input files before doing any
review work:

```bash
set -euo pipefail
ROOT=$(git rev-parse --show-toplevel 2>/dev/null || pwd)
PACKAGE=$(realpath -- "$ARGUMENTS")
CLAIMS="$PACKAGE/claims.json"
COVERAGE="$PACKAGE/query_coverage.json"

test -d "$PACKAGE"
test -f "$CLAIMS"
test -f "$COVERAGE"
test -f "$ROOT/tools/check_evidence_coverage.py"
test -f "$ROOT/tools/adjudicate_findings.py"

python3 - "$CLAIMS" "$COVERAGE" <<'PY'
import json
import math
import sys

claims_path, coverage_path = sys.argv[1:]
with open(claims_path, encoding="utf-8") as fh:
    claims = json.load(fh)
with open(coverage_path, encoding="utf-8") as fh:
    coverage = json.load(fh)

CLAIM_TYPES = {
    "number", "comparison", "scope", "method", "baseline", "citation",
    "artifact_ref", "table_cell", "caption", "research_claim",
    "evidence_statement", "hypothesis",
}
EVIDENCE_DIRECTIONS = {"supports", "contradicts", "limits", "unclear"}
VERIFICATION_STATUSES = {"VERIFIED", "UNVERIFIED", "VERIFY_PENDING"}
SUPPORT_BASES = {"quoted_span", "annotation", "metadata", "relevance_score", "none"}
QUERY_STATUSES = {"SEARCHED", "NO_HIT", "UNVERIFIED", "UNSEARCHABLE", "ERROR"}
EXTRACTORS = {"latex_regex", "pdf_text", "table_parser", "bib_parser", "manual"}
CONFIDENCES = {"high", "medium", "low"}
VALUE_DIRECTIONS = {"higher_better", "lower_better", "unknown"}
AGGREGATIONS = {"mean", "best", "median", "single", "unspecified"}


def fail(path, message):
    raise SystemExit(f"{path}: {message}")


def require_object(value, path):
    if not isinstance(value, dict):
        fail(path, "must be an object")


def require_list(value, path):
    if not isinstance(value, list):
        fail(path, "must be an array")


def require_string(value, path, nonempty=False):
    if type(value) is not str or (nonempty and not value.strip()):
        fail(path, "must be a non-empty string" if nonempty else "must be a string")


def require_string_list(value, path, nonempty_items=False):
    require_list(value, path)
    for index, item in enumerate(value):
        require_string(item, f"{path}[{index}]", nonempty=nonempty_items)


def require_integer(value, path):
    if type(value) is not int:
        fail(path, "must be an integer")


def require_number(value, path):
    if type(value) not in (int, float):
        fail(path, "must be a number")
    if type(value) is float and not math.isfinite(value):
        fail(path, "must be a finite number")


def require_boolean(value, path):
    if type(value) is not bool:
        fail(path, "must be a boolean")


def require_enum(value, path, allowed):
    if type(value) is not str or value not in allowed:
        fail(path, f"must be one of {sorted(allowed)}")


def require_fields(value, fields, path):
    for field in fields:
        if field not in value:
            fail(path, f"missing required field {field!r}")


require_object(claims, "claims.json")
require_fields(
    claims,
    {"ledger_version", "paper_id", "observability_level", "source_files", "claims"},
    "claims.json",
)
require_string(claims["ledger_version"], "claims.ledger_version", nonempty=True)
require_string(claims["paper_id"], "claims.paper_id", nonempty=True)
require_integer(claims["observability_level"], "claims.observability_level")
if not 0 <= claims["observability_level"] <= 3:
    fail("claims.observability_level", "must be between 0 and 3")
if "generated_at" in claims:
    require_string(claims["generated_at"], "claims.generated_at")

require_list(claims["source_files"], "claims.source_files")
for index, source in enumerate(claims["source_files"]):
    path = f"claims.source_files[{index}]"
    require_object(source, path)
    require_fields(source, {"path", "sha256"}, path)
    require_string(source["path"], f"{path}.path", nonempty=True)
    require_string(source["sha256"], f"{path}.sha256", nonempty=True)
    if "kind" in source:
        require_enum(source["kind"], f"{path}.kind", {"pdf", "latex", "bib", "results", "repo", "text"})

require_list(claims["claims"], "claims.claims")
claim_query_links = {}
seen_claim_ids = set()
for index, claim in enumerate(claims["claims"]):
    path = f"claims.claims[{index}]"
    require_object(claim, path)
    require_fields(claim, {"claim_id", "type", "text_span", "location"}, path)
    require_string(claim["claim_id"], f"{path}.claim_id", nonempty=True)
    if claim["claim_id"] in seen_claim_ids:
        fail(f"{path}.claim_id", "must be unique within claims.json")
    seen_claim_ids.add(claim["claim_id"])
    require_enum(claim["type"], f"{path}.type", CLAIM_TYPES)
    require_string(claim["text_span"], f"{path}.text_span", nonempty=True)

    require_object(claim["location"], f"{path}.location")
    require_fields(claim["location"], {"file"}, f"{path}.location")
    require_string(claim["location"]["file"], f"{path}.location.file", nonempty=True)
    for field in ("line", "page"):
        if field in claim["location"]:
            require_integer(claim["location"][field], f"{path}.location.{field}")
    if "section" in claim["location"]:
        require_string(claim["location"]["section"], f"{path}.location.section")

    if "query_ids" in claim:
        require_string_list(claim["query_ids"], f"{path}.query_ids", nonempty_items=True)
        claim_query_links[claim["claim_id"]] = list(claim["query_ids"])
    for field, allowed in (
        ("evidence_direction", EVIDENCE_DIRECTIONS),
        ("verification_status", VERIFICATION_STATUSES),
        ("support_basis", SUPPORT_BASES),
        ("extractor", EXTRACTORS),
        ("confidence", CONFIDENCES),
    ):
        if field in claim:
            require_enum(claim[field], f"{path}.{field}", allowed)
    if "load_bearing" in claim:
        require_boolean(claim["load_bearing"], f"{path}.load_bearing")
    if "refs" in claim:
        require_string_list(claim["refs"], f"{path}.refs")
    if "evidence_anchor" in claim:
        require_string(claim["evidence_anchor"], f"{path}.evidence_anchor")

    if "value" in claim:
        value_path = f"{path}.value"
        value = claim["value"]
        require_object(value, value_path)
        for field in ("raw", "unit", "metric"):
            if field in value:
                require_string(value[field], f"{value_path}.{field}")
        if "normalized" in value:
            require_number(value["normalized"], f"{value_path}.normalized")
        if "direction" in value:
            require_enum(value["direction"], f"{value_path}.direction", VALUE_DIRECTIONS)
        if "aggregation" in value:
            require_enum(value["aggregation"], f"{value_path}.aggregation", AGGREGATIONS)

require_object(coverage, "query_coverage.json")
require_fields(
    coverage,
    {"schema_version", "branch_id", "source_policy", "queries", "artifact_hashes"},
    "query_coverage.json",
)
if type(coverage["schema_version"]) is not str or coverage["schema_version"] != "0.1":
    fail("coverage.schema_version", "must be the string '0.1'")
require_string(coverage["branch_id"], "coverage.branch_id", nonempty=True)
source_policy = coverage["source_policy"]
if isinstance(source_policy, str):
    if not source_policy.strip():
        fail("coverage.source_policy", "must not be empty")
elif not isinstance(source_policy, dict):
    fail("coverage.source_policy", "must be a string or object")
if "counter_query_run" in coverage:
    require_boolean(coverage["counter_query_run"], "coverage.counter_query_run")

require_object(coverage["artifact_hashes"], "coverage.artifact_hashes")
for artifact_key, artifact_hash in coverage["artifact_hashes"].items():
    require_string(artifact_hash, f"coverage.artifact_hashes[{artifact_key!r}]")

require_list(coverage["queries"], "coverage.queries")
seen_query_ids = set()
for index, query in enumerate(coverage["queries"]):
    path = f"coverage.queries[{index}]"
    require_object(query, path)
    require_fields(query, {"query_id", "status", "evidence_directions", "source", "evidence_item_keys"}, path)
    query_id = query["query_id"]
    if type(query_id) is not str or not query_id.strip():
        fail(f"{path}.query_id", "must be a non-empty string")
    if query_id in seen_query_ids:
        fail(f"{path}.query_id", "must be unique within query_coverage.json")
    seen_query_ids.add(query_id)
    status = query["status"]
    if type(status) is not str or status not in QUERY_STATUSES:
        fail(f"{path}.status", f"must be one of {sorted(QUERY_STATUSES)}")
    require_string_list(query["evidence_directions"], f"{path}.evidence_directions")
    for direction in query["evidence_directions"]:
        require_enum(direction, f"{path}.evidence_directions", EVIDENCE_DIRECTIONS)
    require_string(query["source"], f"{path}.source", nonempty=True)
    require_string_list(query["evidence_item_keys"], f"{path}.evidence_item_keys", nonempty_items=True)
    if "query" in query:
        require_string(query["query"], f"{path}.query")
    if "notes" in query:
        require_string(query["notes"], f"{path}.notes")

for claim_id, query_ids in claim_query_links.items():
    missing = [query_id for query_id in query_ids if query_id not in seen_query_ids]
    if missing:
        fail(f"claims.claims[{claim_id}].query_ids", f"unknown query_id(s): {missing}")
PY

CLAIMS_SHA=$(sha256sum "$CLAIMS" | cut -d' ' -f1)
COVERAGE_SHA=$(sha256sum "$COVERAGE" | cut -d' ' -f1)
```

The two hashes are a freeze boundary. Recheck them immediately before opening
the reviewer. A changed hash invalidates the run; do not mix findings from
different package versions.

Before opening the reviewer, create the temporary coverage status map outside
the package. It is deleted when this workflow exits and is never one of the
four required package outputs:

A successful map contains "evidence-audit": "completed"; a timeout or
unparseable reviewer response contains "evidence-audit": "review_unavailable".

~~~bash
COVERAGE_STATUS=$(mktemp "${TMPDIR:-/tmp}/evidence-audit-coverage.XXXXXX.json")
trap 'rm -f "$COVERAGE_STATUS"' EXIT
python3 - "$COVERAGE_STATUS" <<'PY'
import json
import sys

status_path = sys.argv[1]
coverage = {
    "consistency-audit": "not_applicable",
    "experiment-forensics": "not_applicable",
    "baseline-comparison-audit": "not_applicable",
    "citation-forensics": "not_applicable",
    "presentation-signals": "not_applicable",
    "proof-derivation-forensics": "not_applicable",
    "eval-design-forensics": "not_applicable",
    "evidence-audit": "review_unavailable",
    "ai-style-impressions": "not_applicable",
    "adversarial-case-builder": "not_applicable",
    "novelty-duplication-advisory": "not_applicable",
}
with open(status_path, "w", encoding="utf-8") as fh:
    json.dump(coverage, fh, indent=2)
PY
~~~

## Step 2 — Run the deterministic coverage checker

The deterministic checker sees both package files and emits its own disjoint
finding IDs. It does not retrieve evidence and it does not decide a verdict:

```bash
DETERMINISTIC="$PACKAGE/evidence-audit.deterministic.findings.json"
python3 "$ROOT/tools/check_evidence_coverage.py" \
    --ledger "$CLAIMS" \
    --coverage "$COVERAGE" \
    --out "$DETERMINISTIC"
```

Do not pass the resulting findings to the semantic reviewer. Keeping the two
inputs independent prevents the deterministic pass from becoming a leading
summary of what the reviewer is expected to find.

## Step 3 — Open one fresh isolated Codex reviewer

Recheck the freeze boundary and then open exactly one **fresh isolated Codex
reviewer**. A fresh context is required even when the executor
and reviewer use the same model family. The reviewer is read-only and receives
only this bounded input:

```bash
test "$(sha256sum "$CLAIMS" | cut -d' ' -f1)" = "$CLAIMS_SHA"
test "$(sha256sum "$COVERAGE" | cut -d' ' -f1)" = "$COVERAGE_SHA"
```

```text
absolute package path: <PACKAGE>
claims.json: <PACKAGE>/claims.json
query_coverage.json: <PACKAGE>/query_coverage.json
rubric: <the evidence-audit rubric below>
observability level: <claims.json.observability_level>
```

The reviewer receives no authoring chat context, no executor summary, no
deterministic findings, no prior reviewer response, and no report. Use this
call envelope:

```text
mcp__codex__codex:
  model: gpt-5.6-luna
  config: {"model_reasoning_effort": "max"}
  sandbox: read-only
  cwd: <PACKAGE>
  prompt: |
    Read only the absolute package path and the two named JSON files.
    Propose semantic evidence-audit findings; do not retrieve anything and do
    not edit any package input. Output one JSON array and nothing else.

    Rubric:
    - Inspect whether research claims are semantically supported, limited,
      contradicted, or left unresolved by the recorded query coverage.
    - Report discrepancies and questions for a human reviewer, never an
      accusation or a misconduct conclusion.
    - Every finding above info must contain evidence with a real claim_id and a
      verbatim, whitespace-normalized substring of that claim's text_span.
    - Declare the lowest observability level needed to decide the issue and an
      honest false_positive_risk.
    - Keep external verification requests informational and mark them with
      verdict_local=needs_external_check and requires_external_check=true.
    - Emit evidence-audit findings only. Do not compute or write overall_verdict,
      report.json, or REPORT.md.
```

Persist the single returned JSON array to
`$PACKAGE/evidence-audit.semantic.findings.json`. If the reviewer times out or
does not return a parseable array, write [], set REVIEWER_STATUS=review_unavailable,
and continue; do not hand-author a semantic finding and do not open a second
reviewer context. On a successful parseable array, set
REVIEWER_STATUS=completed before updating the temporary coverage map.

Update only the temporary status map after the single reviewer call:

~~~bash
python3 - "$COVERAGE_STATUS" "$REVIEWER_STATUS" <<'PY'
import json
import sys

status_path, status = sys.argv[1:]
if status not in {"completed", "review_unavailable"}:
    raise SystemExit(f"invalid reviewer status: {status!r}")
with open(status_path, encoding="utf-8") as fh:
    coverage = json.load(fh)
coverage["evidence-audit"] = status
with open(status_path, "w", encoding="utf-8") as fh:
    json.dump(coverage, fh, indent=2)
PY
~~~

## Step 4 — Validate semantic finding anchors

The executor validates the returned findings before adjudication. This gate
does not decide severity or a verdict; it only performs schema hygiene and the
same span direction as the adjudicator (`span in claim`, never the reverse).
It keeps unanchored proposals as `info` so the forensic record is not silently
lost. The generated output file is normalized in place through a temporary
file, while the two package inputs remain untouched:

```bash
SEMANTIC="$PACKAGE/evidence-audit.semantic.findings.json"
test "$(sha256sum "$CLAIMS" | cut -d' ' -f1)" = "$CLAIMS_SHA"
test "$(sha256sum "$COVERAGE" | cut -d' ' -f1)" = "$COVERAGE_SHA"
python3 - "$CLAIMS" "$SEMANTIC" "$SEMANTIC.tmp" <<'PY'
import json
import os
import sys

claims_path, semantic_path, temp_path = sys.argv[1:]
claims = json.load(open(claims_path, encoding="utf-8"))
claim_map = {}
for raw_claim in claims.get("claims", []):
    if not isinstance(raw_claim, dict):
        continue
    raw_claim_id = raw_claim.get("claim_id")
    if not isinstance(raw_claim_id, str) or not raw_claim_id.strip():
        continue
    claim_map[raw_claim_id] = raw_claim

def nw(value):
    return " ".join(value.split()) if isinstance(value, str) else ""

try:
    proposed = json.load(open(semantic_path, encoding="utf-8"))
except (OSError, json.JSONDecodeError):
    proposed = []

if isinstance(proposed, dict):
    if "overall_verdict" in proposed:
        proposed = []
    else:
        proposed = proposed.get("findings", [])
if not isinstance(proposed, list) or any(
    isinstance(item, dict) and "overall_verdict" in item for item in proposed
):
    proposed = []

kept = []
for index, item in enumerate(proposed, 1):
    if not isinstance(item, dict):
        continue
    finding = dict(item)
    finding["finding_id"] = f"EVIDS{index:03d}"
    finding["skill"] = "evidence-audit"
    for field in ("title", "description"):
        if not isinstance(finding.get(field), str):
            finding[field] = ""
    if "recommended_reviewer_action" in finding and not isinstance(
        finding["recommended_reviewer_action"], str
    ):
        finding.pop("recommended_reviewer_action", None)
    pattern_id = finding.get("pattern_id")
    if not isinstance(pattern_id, str):
        finding.pop("pattern_id", None)
    if type(finding.get("severity")) is not str or finding["severity"] not in {
        "critical", "major", "minor", "info"
    }:
        finding["severity"] = "info"
    if type(finding.get("verdict_local")) is not str or finding["verdict_local"] not in {
        "fail", "warn", "clean", "needs_external_check"
    }:
        finding["verdict_local"] = "warn"
    if type(finding.get("false_positive_risk")) is not str or finding["false_positive_risk"] not in {
        "low", "medium", "high"
    }:
        finding["false_positive_risk"] = "high"
    required = finding.get("observability_level_required")
    if type(required) is not int or not 0 <= required <= 3:
        finding["observability_level_required"] = 2

    requires_external_check = finding.get("requires_external_check", False)
    if type(requires_external_check) is not bool:
        # A malformed external-check flag must not let a risky proposal raise
        # the verdict; preserve valid booleans and fail closed otherwise.
        requires_external_check = "requires_external_check" in finding
    finding["requires_external_check"] = requires_external_check

    anchored = []
    raw_evidence = finding.get("evidence")
    if not isinstance(raw_evidence, list):
        raw_evidence = []
    for evidence in raw_evidence:
        if not isinstance(evidence, dict):
            continue
        claim_id = evidence.get("claim_id")
        if not isinstance(claim_id, str) or not claim_id.strip():
            continue
        claim = claim_map.get(claim_id)
        span = nw(evidence.get("span"))
        if claim and span and span in nw(claim.get("text_span")):
            entry = dict(evidence)
            entry["claim_id"] = claim_id
            entry["span"] = span
            location = claim.get("location")
            entry["location"] = dict(location) if isinstance(location, dict) else {}
            artifact_hash = claim.get("evidence_anchor")
            if isinstance(artifact_hash, str):
                entry["artifact_hash"] = artifact_hash
            else:
                entry.pop("artifact_hash", None)
            anchored.append(entry)
    finding["evidence"] = anchored
    if finding["severity"] != "info" and not anchored:
        finding["severity"] = "info"
    finding["reviewer"] = {
        "model": "gpt-5.6-luna",
        "reasoning": "max",
        "deterministic": False,
    }
    kept.append(finding)

with open(temp_path, "w", encoding="utf-8") as fh:
    json.dump(kept, fh, indent=2, ensure_ascii=False)
os.replace(temp_path, semantic_path)
PY
```

The semantic file must exist even when it is `[]`. It remains separate from the
deterministic file; do not merge or duplicate either finding set.

## Step 5 — Run the existing adjudicator and render the report

Read `paper_id` and the declared observability level from the already validated
`claims.json`, then invoke the existing adjudicator once over both disjoint
finding files:

```bash
PAPER_ID=$(python3 - "$CLAIMS" <<'PY'
import json, sys
print(json.load(open(sys.argv[1], encoding="utf-8"))["paper_id"])
PY
)
LEVEL=$(python3 - "$CLAIMS" <<'PY'
import json, sys
print(json.load(open(sys.argv[1], encoding="utf-8"))["observability_level"])
PY
)

# This is the final package freeze check: it runs after semantic normalization
# and immediately before the only adjudicator invocation.
CLAIMS_SHA_NOW=$(sha256sum "$CLAIMS" | cut -d' ' -f1)
COVERAGE_SHA_NOW=$(sha256sum "$COVERAGE" | cut -d' ' -f1)
if [ "$CLAIMS_SHA_NOW" != "$CLAIMS_SHA" ] || [ "$COVERAGE_SHA_NOW" != "$COVERAGE_SHA" ]; then
    echo "Frozen package changed after semantic normalization; restart from package validation." >&2
    exit 1
fi

python3 "$ROOT/tools/adjudicate_findings.py" \
    --findings "$DETERMINISTIC" "$SEMANTIC" \
    --ledger "$CLAIMS" \
    --paper-id "$PAPER_ID" \
    --observability-level "$LEVEL" \
    --taxonomy-version 0.6 \
    --coverage "$COVERAGE_STATUS" \
    --out "$PACKAGE/report.json" \
    --md "$PACKAGE/REPORT.md"
```

This command both computes the existing report verdict and renders the
human-readable report. Do not inspect a reviewer label as a verdict and do not
write a replacement report. The final verdict is a deterministic function of
the frozen package, the two finding files, and the declared observability level.

## Output contract

A successful run leaves exactly these required audit outputs in the package:

- `evidence-audit.deterministic.findings.json` — deterministic coverage findings;
- `evidence-audit.semantic.findings.json` — one fresh review's validated
  semantic findings, or `[]`;
- `report.json` — the existing adjudicator's machine-readable report;
- `REPORT.md` — the existing adjudicator's human-readable rendering.

`report.json["overall_verdict"]` is owned by
`tools/adjudicate_findings.py` and remains one of Anti-Autoresearch's existing
three verdict values. This workflow adds the `research_evidence` dimension
through the existing finding-to-dimension mapping; it does not add another
verdict vocabulary or another adjudication path.
