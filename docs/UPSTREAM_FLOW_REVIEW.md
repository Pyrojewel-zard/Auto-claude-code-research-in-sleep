# Upstream flow review

ARIS is intentionally smaller than its upstream catalog. An upstream update is
therefore an input to review, not an instruction to expand the default
installation.

## Procedure

1. Fetch the upstream branch or tag into an isolated review area. Do not merge
   it into ARIS yet.
2. Enumerate new or changed `SKILL.md` files and record each candidate's name,
   purpose, entry kind, sources, host, dependencies, reviewer context, tested
   commit, and focused tests in a candidate JSON file.
3. Run the offline classifier:

   ```bash
   python3 tools/upstream_flow_review.py \
     --candidate candidate.json \
     --out upstream-flow-review.json
   ```

4. Human-review the result and select one of four dispositions:

   - `MERGE`: the behavior fits one of the four canonical entries and passes
     the reduced source, host, dependency, review, and test checks;
   - `ADAPT`: the idea is useful, but its source routing, host assumptions,
     dependency fan-out, reviewer isolation, or tests must be rewritten before
     adoption;
   - `OPTIONAL`: useful outside the core, so keep it behind an explicit
     optional/legacy profile;
   - `REJECT`: duplicate, unsafe, silently broadens retrieval, or violates
     reviewer independence.

5. For `MERGE` or `ADAPT`, implement the behavior inside the relevant
   canonical entry or shared helper. Do not add a new default public entry
   merely because upstream used a new name.
6. Run focused regression tests, the four-entry installer tests, the full ARIS
   suite, and the vendored Anti eval. Record the adopted upstream commit and
   the review JSON in the change description or release notes.

## Candidate manifest

The minimum manifest is:

```json
{
  "name": "zotero-branch-helper",
  "description": "Codex evidence branch helper for Zotero autoresearch",
  "entry_kind": "research",
  "sources": ["zotero", "local"],
  "host": "codex",
  "dependencies": ["research_state", "research_gate"],
  "tests": ["tests/test_zotero_branch_helper.py"],
  "fallback_policy": "none",
  "review_context": "not-applicable",
  "reviewed_commit": "<upstream commit>"
}
```

`fallback_policy: silent` combined with a web/arXiv/database source is a hard
reject. External expansion is acceptable only when it is explicit, gap-scoped,
and represented in the same evidence contract. An audit candidate must use a
fresh isolated reviewer; `same-context` is a hard reject.

## Four-entry boundary

The maintained default surface is:

```text
autoresearch-topic       topic → branches → Zotero → synthesis
autoresearch-proposal    draft → claims/gaps → branches → Zotero → synthesis
research-write           promoted evidence → proposal/paper → freeze
research-audit           branch/frozen package → evidence/Anti gate
```

Upstream may improve these entries or their shared internals. It must not
silently reintroduce broad search, autonomous experiment loops, or a second
public orchestration family.
