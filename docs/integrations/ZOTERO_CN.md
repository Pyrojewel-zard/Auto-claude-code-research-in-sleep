# Zotero 集成

精简后的 ARIS 流程以 Zotero 为唯一自动文献发现入口：

```text
/research -> Zotero semantic search -> evidence matrix -> /write -> /audit
```

`/research` 为每个分支 `QUERY_PACK.md` 中的 query 调用一次
`mcp__zotero_mcp__semantic_search`；结果为空时最多用声明过的别名重试一次，
随后必须记录终态。对去重后的命中，可继续读取 Zotero item details、全文
content、annotations/highlights 来核验具体段落。

## 配置 MCP

按照 Zotero MCP server 的当前说明安装，并在运行 ARIS 的宿主中暴露它。常见
的本地桌面配置示例：

```bash
uv tool install zotero-mcp-server
claude mcp add zotero -s user -- zotero-mcp -e ZOTERO_LOCAL=true
```

Web API 模式的凭证只通过 MCP server 环境配置，不要写入本仓库。

开始运行前确认宿主提供 semantic search 以及 item/content/annotation 工具。
如果 MCP 或语义索引不可用，ARIS 会记录 `ERROR` 并保留 query，不会静默切换到
WebSearch、arXiv、Semantic Scholar、OpenAlex、Exa、Gemini 或其他文献源。

## 证据契约

每个分支在 `EVIDENCE_MATRIX.md` 中为每个 query 保留一行，记录：

- Query ID 与申请书/分支 claim；
- `SEARCHED`、`NO_HIT`、`UNVERIFIED`、`UNSEARCHABLE`、`ERROR` 之一；
- Zotero `itemKey`、文献身份、匹配 chunk 或 annotation；
- `supports`、`contradicts`、`limits`、`unclear` 之一；以及
- verification status 与 coverage gap。

完成 `COVERAGE_REPORT.md` 后，默认 `external_expansion: ask` 只针对报告中的
gap 询问一次；`never` 保留 gap，`allow` 只允许预先授权的定向扩展。两者都不
改变 Zotero 的自动检索契约。

完整的 topic/proposal 流程见
[`skills/skills-codex/research/SKILL.md`](../../skills/skills-codex/research/SKILL.md)。
