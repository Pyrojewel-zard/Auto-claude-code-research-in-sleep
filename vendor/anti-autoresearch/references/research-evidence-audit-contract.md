# Research Evidence Audit Contract

Version `0.1` extends the existing Anti-Autoresearch claims, findings, and
report spine to describe evidence coverage for an ARIS research branch. It is
an evidence contract, not a second verdict system.

## Scope and boundaries

Anti-Autoresearch remains detect-only. It records and audits evidence that is
already available to the run; it does not retrieve papers, call the web, or add
Zotero retrieval. A query record may say that a query was searched, had no hit,
could not be searched, or failed, but that record does not cause a search.

The reviewer proposes `evidence-audit` findings. The deterministic
`tools/adjudicate_findings.py` adjudicates all findings and computes the report
verdict. The `research_evidence` report dimension is a reporting seam, not an
LLM verdict.

## Query coverage

`schemas/query_coverage.schema.json` defines `query_coverage.json`, whose
`schema_version` is the string `0.1`. A coverage record requires:

- `branch_id`: the stable ARIS research-branch identifier;
- `source_policy`: the declared provenance policy (recorded, not executed);
- `queries`: the query coverage entries; and
- `artifact_hashes`: a mapping from recorded artifact keys or paths to content
  hashes.

Each query requires `query_id`, `status`, `evidence_directions`, `source`, and
`evidence_item_keys`. The terminal query states are:

`SEARCHED`, `NO_HIT`, `UNVERIFIED`, `UNSEARCHABLE`, and `ERROR`.

An evidence direction is one of `supports`, `contradicts`, `limits`, or
`unclear`. `evidence_item_keys` are stable references to recorded evidence
items; they are not permission to fetch an absent source.

## Claims

The claims ledger keeps its existing claim types and adds:

- `research_claim` for a branch claim under audit;
- `evidence_statement` for a recorded statement bearing on a claim; and
- `hypothesis` for an explicitly non-verified proposition.

Claims may link to coverage entries with `query_ids` and may carry
`evidence_direction`, `verification_status`, `load_bearing`, and `support_basis`.
The allowed verification statuses are `VERIFIED`, `UNVERIFIED`, and
`VERIFY_PENDING`. The allowed support bases are `quoted_span`, `annotation`,
`metadata`, `relevance_score`, and `none`.

These annotations are optional so existing evidence ledgers remain readable;
they add research-evidence semantics without replacing the span-anchored
ledger. A claim's `text_span` remains verbatim source text.

## Findings and adjudication

An `evidence-audit` finding follows the existing `finding.schema.json` contract.
The reviewer proposes a discrepancy or an evidence gap; it does not issue the
overall verdict. Any finding above `info` must carry a real `claim_id` and a
verbatim, non-empty span from the claims ledger. The deterministic adjudicator
still applies the anchoring, observability, false-positive, and other gates
before computing `overall_verdict`.

The research-evidence dimension therefore has the same human-review and
detect-only safeguards as every existing dimension. No evidence direction,
verification status, or query state can by itself become a verdict.

## Compatibility rule

The contract extends the existing JSON Schema draft-07 documents and preserves
their permissive property style. Consumers should ignore optional research
fields they do not understand and must continue to treat the deterministic
adjudicator as the sole verdict owner.
