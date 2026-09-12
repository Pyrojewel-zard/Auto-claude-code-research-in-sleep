# Codex 审查指南

精简后的 ARIS 以 Codex 为主执行者：

```text
/autoresearch-topic    -> /research-audit -> /research-write
/autoresearch-proposal -> /research-audit -> /research-write
```

当前 Codex 上下文负责编排和撰写；审查使用全新、隔离、只读的 Codex 上下文，
读取冻结产物。作者上下文不能为自己的 Anti-Autoresearch 结果下 verdict。

## 安装最小 surface

```bash
bash tools/install_aris_codex.sh /path/to/project --profile pyrojewel-research
```

这只安装四个入口：`autoresearch-topic`、`autoresearch-proposal`、
`research-write`、`research-audit`，不会选择宽泛的检索、实验或旧论文流水线
skill。旧 catalog 以及可选 Claude/Gemini overlay 仍保留给其他工作，但不属于默认
profile。

## 审查边界

`/autoresearch-topic` 用于从主题开始；`/autoresearch-proposal` 用于从已有申请书/项目
申请书草案开始。两者都使用 Zotero semantic search 作为自动文献源，并在一个分支
完整检索后调用 `/research-audit`；`/research-write` 只接受 `PROMOTABLE` 或
`PROMOTABLE_WITH_OBLIGATIONS` 证据；`/research-audit` 可审计分支证据，也可冻结最终源码/结果包，从
`vendor/anti-autoresearch/` 与 `tools/anti-autoresearch.lock.json` 解析 Anti，
运行 vendored eval，再通过 `tools/forensics_gate.py` 汇总。

gate 原样保留 `CLEAN_GIVEN_EVIDENCE`、`SOFT_FLAGS`、`HARD_FLAGS`、
`REVIEW_UNAVAILABLE`。同族但隔离的 reviewer 标记为
`same-family-isolated`；同一上下文标记为 `same-context` 并直接 BLOCK。

## 可选跨家族审查

若投稿或本地政策确实要求独立 Claude reviewer，可显式叠加现有
`skills-codex-claude-review` overlay 并记录 provenance。它不是默认 ARIS profile
的一部分，也不能绕过冻结产物 gate。

后续 upstream flow 不会静默扩展默认入口，先按
[`UPSTREAM_FLOW_REVIEW.md`](UPSTREAM_FLOW_REVIEW.md) 作为候选进行审查。
