# IEEE 优先文献检索流程整合设计

**日期**: 2026-04-20
**状态**: 设计完成，待实现
**作者**: Claude Code (brainstorming session)

---

## 概述

将 IEEE Xplore 作为 ARIS 研究流程的首选文献来源，通过新增协调层 skill 实现：
- IEEE 优先的多轮检索
- 分级阅读编排
- 精读 subagent + 双写输出

---

## 整体架构

```
research-pipeline
    └── research-lit (修改)
            ├── ieee-lit-search (新建) ──→ IEEE 论文列表
            │       ├── ieee-keyword-gen (内嵌逻辑)
            │       └── ieee-advanced-search (现有)
            ├── arxiv (现有) ──→ arXiv 补充论文
            └── lit-reading (新建) ──→ 分级阅读 + 双写
                    ├── ieee-paper-fullcontent (现有)
                    ├── ieee-paper-detail (现有)
                    └── deep-reader subagent (新建)
```

**调用流程**：
1. `research-lit` 先调用 `ieee-lit-search` 获取 IEEE 论文
2. 用 arXiv 补充最新预印本（去重）
3. 调用 `lit-reading` 对合并后的论文列表做分级阅读
4. 输出到 `idea-stage/LIT_REVIEW.md` + wiki 入库

**修改范围**：
- 新建 2 个 skill：`ieee-lit-search`、`lit-reading`
- 修改 1 个 skill：`research-lit`（新增参数，不改变默认行为）
- 新建 1 个 subagent：`deep-reader`（精读 agent）

**与 `research-pipeline` 的关系**：
- `research-pipeline` 已通过 `research-lit` 调用文献检索，无需修改
- 用户可通过 `research-lit --source-priority ieee` 启用 IEEE 优先模式
- 未来可在 `research-pipeline` 中新增 `LIT_SOURCE_PRIORITY` 常量控制默认行为

---

## 新建 Skill 1: `ieee-lit-search`

### 职责

IEEE 优先的多轮检索编排

### 输入参数

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `query` | string | 必填 | 用户研究方向描述 |
| `venues` | string[] | 核心期刊白名单 | 期刊/会议列表 |
| `year_range` | string | 近 5 年 | 如 `2019-2024` |
| `max_results` | int | 50 | 每轮最大结果数 |

### 核心逻辑

```
1. 关键词生成
   a. 结构化分解：LLM 将 query 分解为 [方法] × [对象] × [应用] 维度
   b. LLM 扩展：每个维度生成同义词/相关术语/上下位词
   c. 组合：生成多轮搜索关键词列表

2. 多轮检索
   for each keyword_set in keyword_list:
       results += ieee-advanced-search(keyword_set, venues, year_range)

3. 去重合并
   - 按 DOI/arnumber 去重
   - 按引用数排序
   - 返回 top-N

4. 输出
   - 论文元数据列表（title, authors, venue, year, doi, arnumber, abstract, citations）
```

### 核心期刊白名单

| 领域 | 期刊/会议 |
|------|----------|
| 射频/微波 | IEEE TMTT, IEEE MWCL, IMS, RFIC, EuMIC |
| 电路/IC | IEEE JSSC, IEEE TCAS, IEEE TCAS-II, CICC, ISSCC |
| 天线/电磁 | IEEE TAP, IEEE AWPL, APS |
| 通信 | IEEE TCOM, IEEE TWC, IEEE JSAC, ICC, Globecom |

**白名单使用方式**：通过 `ieee-advanced-search` 的 Publication Title 过滤，构造布尔查询：
```
("Publication Title":IEEE Transactions on Microwave Theory and Techniques OR "Publication Title":IEEE Microwave and Wireless Components Letters OR ...)
```

### 依赖

- `ieee-advanced-search`（现有，内部已处理结果解析）

---

## 新建 Skill 2: `lit-reading`

### 职责

分级阅读编排 + 双写输出

### 输入参数

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `papers` | list | 必填 | 论文元数据列表 |
| `shallow_read_max` | int | 20 | 粗读最大数量（超过的只读 abstract）|
| `deep_read_top` | int | 5 | 精读数量 |
| `output_dir` | string | `idea-stage/` | 输出目录 |

### 核心逻辑

```
1. 检视层
   for each paper in papers:
       if abstract not relevant:
           mark as skipped
       else:
           mark as candidate

2. 粗读层
   candidates_limited = candidates[:shallow_read_max]
   for each candidate in candidates_limited:
       fullcontent = ieee-paper-fullcontent(arnumber) 或 arxiv-fulltext(doi)
       structured_summary = LLM 提取:
           - 研究问题
           - 核心方法（1-2 句）
           - 关键结果（数字）
           - 局限性
       save to candidate_summaries[]
   # 超过 shallow_read_max 的候选只保留 abstract

3. 精读层
   top_papers = select top-N by relevance + citations
   for each top_paper:
       # Step 1: 获取全文
       fullcontent = ieee-paper-fullcontent(arnumber)
       # Step 2: 获取完整元数据
       detail = ieee-paper-detail(arnumber)
       # Step 3: Dispatch 精读 subagent
       deep_summary = dispatch deep-reader subagent(
           paper_metadata=detail,
           fullcontent=fullcontent
       )
       save to deep_summaries[]

4. 双写输出
   a. 写入 idea-stage/LIT_REVIEW.md:
      - 检视统计（总数/候选/跳过）
      - 粗读摘要表
      - 精读详细笔记
      - 研究趋势/空白分析

   b. 入库 wiki:
      for each deep_summary:
          # Step 1: 先写入 raw
          raw_path = write to raw/notes/papers/{date}-{slug}.md
          # Step 2: 调用 wiki-ingest
          wiki-ingest(raw_path) → wiki/sources/lit-review/
```

### 依赖

- `ieee-paper-fullcontent`（现有）
- `ieee-paper-detail`（现有）
- `arxiv`（现有，用于 arXiv 论文全文）
- `wiki-ingest`（现有）
- `deep-reader` subagent（新建）

---

## 新建 Subagent: `deep-reader`

### 职责

精读单篇论文，提取核心思路返回给主流程

### 触发方式

`lit-reading` 通过 `Agent` tool dispatch

### 输入

- `paper_metadata`：论文元数据
- `fullcontent`：论文全文

### 输出格式

```markdown
# {paper_title}

## 核心问题
[一句话描述论文要解决什么问题]

## 核心方法
[1-2 句描述方法的关键思路，不含实现细节]

## 关键结果
| 指标 | 值 | 对比基准 |
|------|-----|---------|
| ... | ... | ... |

## 方法论启发
[该方法对我们研究的可借鉴之处]

## 局限性
[方法的前提假设、适用范围、未解决的问题]

## 与我们的关系
- [ ] 可直接引用
- [ ] 方法可借鉴
- [ ] 结果可对比
- [ ] 无直接相关

## 后续行动
[如需深入：要读的参考文献、要复现的实验、要对比的基线]
```

### Agent 配置

- `subagent_type: general-purpose`
- `model: sonnet`
- 单篇论文超时：5 分钟

---

## 修改 Skill: `research-lit`

### 设计决策：非破坏性修改

**不修改 `research-lit` 的默认行为**，保持 arXiv 优先。通过新增参数 `--source-priority: ieee` 启用 IEEE 优先流程。

### 当前逻辑（arXiv 优先，保持不变）

```
research-lit:
    1. arxiv(query) → arXiv 论文
    2. semantic-scholar(query) → 已发表论文
    3. 合并去重
    4. 返回论文列表
```

### 新增逻辑（IEEE 优先，通过参数启用）

当用户指定 `--source-priority: ieee` 时：

```
research-lit --source-priority ieee:
    1. ieee-lit-search(query, venues, year_range) → IEEE 论文
    2. arxiv(query) → arXiv 预印本补充
    3. 按 DOI 去重合并
    4. lit-reading(papers) → 分级阅读 + 双写
    5. 返回 LIT_REVIEW.md 路径
```

### 新增参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `source_priority` | `arxiv` | 可选 `ieee` 启用 IEEE 优先流程 |
| `venues` | 核心期刊白名单 | 传递给 ieee-lit-search |
| `year_range` | 近 5 年 | 传递给 ieee-lit-search |
| `deep_read_top` | 5 | 传递给 lit-reading |

### 输出变化

- 默认（arXiv 优先）：返回论文元数据列表（保持不变）
- IEEE 优先模式：返回 `LIT_REVIEW.md` 路径 + 论文列表

---

## 实现优先级

1. **P0**: `ieee-lit-search` — 核心检索编排
2. **P0**: `lit-reading` — 分级阅读编排
3. **P1**: `deep-reader` subagent — 精读 agent
4. **P1**: `research-lit` 修改 — 整合调用

---

## 风险与缓解

| 风险 | 缓解措施 |
|------|----------|
| IEEE API 限流 | 多轮检索间加入延迟，缓存结果 |
| 精读 subagent 超时 | 设置 5 分钟超时，失败时降级为粗读 |
| 关键词生成质量不稳定 | 提供示例 prompt，要求 LLM 先输出推理过程 |
| wiki 入库冲突 | 使用 `wiki-ingest` 的相似度检测避免重复 |
