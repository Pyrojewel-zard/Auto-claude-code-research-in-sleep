# Codex 审查指南

精简后的 ARIS 以 Codex 为主执行者：

```text
/research -> /write -> /audit
```

当前 Codex 上下文负责编排和撰写；审查使用全新、隔离、只读的 Codex 上下文，
读取冻结产物。作者上下文不能为自己的 Anti-Autoresearch 结果下 verdict。

## 安装最小 surface

```bash
bash tools/install_aris_codex.sh /path/to/project --profile pyrojewel-research
```

这只安装 `research`、`write`、`audit`，不会选择宽泛的检索、实验或旧论文流水线
skill。旧 catalog 以及可选 Claude/Gemini overlay 仍保留给其他工作，但不属于默认
profile。

## 审查边界

`/research` 使用 Zotero semantic search 作为自动文献源，并在一个分支完整检索后
做轻量审计；`/write` 只接受 `PROMOTABLE` 或
`PROMOTABLE_WITH_OBLIGATIONS` 证据；`/audit` 冻结最终源码/结果包，从
`vendor/anti-autoresearch/` 与 `tools/anti-autoresearch.lock.json` 解析 Anti，
运行 vendored eval，再通过 `tools/forensics_gate.py` 汇总。

gate 原样保留 `CLEAN_GIVEN_EVIDENCE`、`SOFT_FLAGS`、`HARD_FLAGS`、
`REVIEW_UNAVAILABLE`。同族但隔离的 reviewer 标记为
`same-family-isolated`；同一上下文标记为 `same-context` 并直接 BLOCK。

## 可选跨家族审查

若投稿或本地政策确实要求独立 Claude reviewer，可显式叠加现有
`skills-codex-claude-review` overlay 并记录 provenance。它不是默认 ARIS profile
的一部分，也不能绕过冻结产物 gate。
