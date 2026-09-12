# Zotero integration

ARIS's reduced flow is Zotero-first, with four independent public entries:

```text
/autoresearch-topic or /autoresearch-proposal
  -> Zotero semantic search -> complete branch autoresearch
  -> /research-audit -> promoted synthesis -> /research-write
```

The automatic scholarly retrieval operation is
`mcp__zotero_mcp__semantic_search`. For every query in a branch's
`QUERY_PACK.md`, the selected autoresearch entry makes one semantic call, optionally retries once
with a declared alias, then records a terminal status. It can use Zotero item
details, full-text content, and annotations to verify the matched passage.

## Configure the MCP server

Install the Zotero MCP server using its own current instructions, then expose
it to the host running ARIS. A local desktop setup commonly looks like:

```bash
uv tool install zotero-mcp-server
claude mcp add zotero -s user -- zotero-mcp -e ZOTERO_LOCAL=true
```

For a Web API setup, provide the Zotero API credentials through the MCP
server's environment rather than writing them into this repository.

Verify that the host exposes semantic search and the companion item/content/
annotation tools before starting a run. If the MCP or semantic index is
unavailable, ARIS records `ERROR` and keeps the query visible; it does not
silently switch to WebSearch, arXiv, Semantic Scholar, OpenAlex, Exa, Gemini,
or another scholarly source.

## Evidence contract

Each branch writes one row per query to `EVIDENCE_MATRIX.md` and records:

- Query ID and draft/branch claim;
- query status: `SEARCHED`, `NO_HIT`, `UNVERIFIED`, `UNSEARCHABLE`, or `ERROR`;
- Zotero `itemKey`, bibliographic identity, matched chunk or annotation;
- evidence direction: `supports`, `contradicts`, `limits`, or `unclear`; and
- verification status and any coverage gap.

After `COVERAGE_REPORT.md`, the default `external_expansion: ask` policy asks
once about only the named gaps. `never` preserves them; `allow` requires an
explicit targeted policy. Neither policy changes the automatic Zotero
contract.

See [`skills/skills-codex/autoresearch-topic/SKILL.md`](../../skills/skills-codex/autoresearch-topic/SKILL.md)
and [`skills/skills-codex/autoresearch-proposal/SKILL.md`](../../skills/skills-codex/autoresearch-proposal/SKILL.md)
for the topic/proposal workflows, plus
[`skills/skills-codex/research-audit/SKILL.md`](../../skills/skills-codex/research-audit/SKILL.md)
and [`skills/skills-codex/research-write/SKILL.md`](../../skills/skills-codex/research-write/SKILL.md)
for the audit and writing handoffs. See [`ZOTERO_CN.md`](ZOTERO_CN.md) for
the Chinese version.
