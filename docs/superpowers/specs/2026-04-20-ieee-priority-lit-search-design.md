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
            │       └── ieee-advanced-search (新建)
            ├── arxiv (现有) ──→ arXiv 补充论文
            └── lit-reading (新建) ──→ 分级阅读 + 双写
                    ├── ieee-paper-fullcontent (新建)
                    ├── ieee-paper-detail (新建)
                    └── deep-reader subagent (新建)
```

**调用流程**：
1. `research-lit` 先调用 `ieee-lit-search` 获取 IEEE 论文
2. 用 arXiv 补充最新预印本（去重）
3. 调用 `lit-reading` 对合并后的论文列表做分级阅读
4. 输出到 `idea-stage/LIT_REVIEW.md` + wiki 入库

**修改范围**：
- 新建 5 个 skill：`ieee-lit-search`、`lit-reading`、`ieee-advanced-search`、`ieee-paper-fullcontent`、`ieee-paper-detail`
- 修改 1 个 skill：`research-lit`（新增参数，不改变默认行为）
- 新建 1 个 subagent：`deep-reader`（精读 agent）

**与 `research-pipeline` 的关系**：
- `research-pipeline` 已通过 `research-lit` 调用文献检索，无需修改
- 用户可通过 `research-lit "topic" --sources: ieee` 启用 IEEE 优先模式
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

## IEEE Skills 契约定义

### 前置条件

IEEE skills 通过浏览器自动化访问 IEEE Xplore，**无需 API 凭证**。用户需有机构访问权限（校园网/VPN）。

### `ieee-advanced-search` 契约

**输入**：
- `query`: 搜索关键词
- `publication_title`: 期刊/会议名称（完整标题，如 `IEEE Transactions on Microwave Theory and Techniques`）
- `year`: 年份范围（如 `2019-2024`）
- `max_results`: 最大结果数

**输出**（每篇论文）：
```json
{
  "title": "论文标题",
  "authors": ["作者1", "作者2"],
  "venue": "IEEE TMTT",
  "year": 2023,
  "doi": "10.1109/...",
  "arnumber": "12345678",
  "abstract": "摘要文本",
  "citations": 42,
  "pdf_url": "https://ieeexplore.ieee.org/stampPDF/getPDF.jsp?arnumber=12345678"
}
```

**失败处理**：
- 无访问权限 → 停止并询问用户：是否配置 VPN/代理？是否跳过 IEEE？
- 零结果 → 返回空列表，继续其他来源

### `ieee-paper-fullcontent` 契约

**输入**：`arnumber`

**输出**：完整论文文本（Markdown 格式，含公式、图表引用）

**失败处理**：
- 付费墙 → 返回 `null`，标记 `paywalled: true`
- 提取失败 → 返回部分内容 + 标记 `partial: true`

### `ieee-paper-detail` 契约

**输入**：`arnumber`

**输出**：
```json
{
  "title": "...",
  "authors": [...],
  "keywords": [...],
  "doi": "...",
  "references": [...],
  "cited_by_count": 42,
  "publication_info": {...}
}
```

---

## 核心期刊白名单（完整标题）

| 领域 | 缩写 | IEEE Xplore Publication Title |
|------|------|-------------------------------|
| 射频/微波 | TMTT | `IEEE Transactions on Microwave Theory and Techniques` |
| 射频/微波 | MWCL | `IEEE Microwave and Wireless Components Letters` |
| 射频/微波 | IMS | `IEEE MTT-S International Microwave Symposium` |
| 射频/微波 | RFIC | `IEEE Radio Frequency Integrated Circuits Symposium` |
| 电路/IC | JSSC | `IEEE Journal of Solid-State Circuits` |
| 电路/IC | TCAS | `IEEE Transactions on Circuits and Systems I: Regular Papers` |
| 电路/IC | TCAS-II | `IEEE Transactions on Circuits and Systems II: Express Briefs` |
| 电路/IC | ISSCC | `IEEE International Solid-State Circuits Conference` |
| 天线/电磁 | TAP | `IEEE Transactions on Antennas and Propagation` |
| 天线/电磁 | AWPL | `IEEE Antennas and Wireless Propagation Letters` |
| 通信 | TCOM | `IEEE Transactions on Communications` |
| 通信 | TWC | `IEEE Transactions on Wireless Communications` |
| 通信 | JSAC | `IEEE Journal on Selected Areas in Communications` |

**查询构造示例**：
```
publication_title:("IEEE Transactions on Microwave Theory and Techniques" OR "IEEE Microwave and Wireless Components Letters" OR "IEEE Journal of Solid-State Circuits")
```

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
       # 按来源路由全文获取
       if paper.source == "ieee":
           fullcontent = ieee-paper-fullcontent(arnumber)
       elif paper.source == "arxiv":
           # arXiv 论文保留 DOI 或下载链接，不强制获取全文
           fullcontent = null  # 标记为 arXiv 来源
           paper.arxiv_id = extract_arxiv_id(paper.doi or paper.url)
       else:
           fullcontent = null
       
       if fullcontent:
           structured_summary = LLM 提取:
               - 研究问题
               - 核心方法（1-2 句）
               - 关键结果（数字）
               - 局限性
           save to candidate_summaries[]
       else:
           # 无全文时只保留 abstract + 来源标记
           save abstract-only entry
   # 超过 shallow_read_max 的候选只保留 abstract

3. 精读层
   top_papers = select top-N by relevance + citations
   for each top_paper:
       # 仅对 IEEE 论文做精读（arXiv 论文保留链接供用户自行阅读）
       if paper.source != "ieee":
           mark as "arXiv: {arxiv_id}" and skip deep-read
           continue
       
       # Step 1: 获取全文
       fullcontent = ieee-paper-fullcontent(arnumber)
       if fullcontent is null:
           mark as "paywalled or unavailable" and skip
           continue
       
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

   b. 入库 wiki（ARIS 流程保留，额外增加）:
      for each deep_summary:
          # 方案 1: ARIS research-wiki 流程
          if research-wiki/ exists:
              slug = python3 tools/research_wiki.py slug "<title>" --author "<last>" --year <year>
              create research-wiki/papers/<slug>.md
              python3 tools/research_wiki.py add_edge research-wiki/ --from "paper:<slug>" --to ...
          
          # 方案 2: Obsidian wiki-ingest 流程（可选）
          if wiki-ingest available:
              raw_path = write to raw/notes/papers/{date}-{slug}.md
              wiki-ingest(raw_path) → wiki/sources/lit-review/
```

### 依赖

- `ieee-paper-fullcontent`（新建）
- `ieee-paper-detail`（新建）
- `arxiv`（现有，用于 arXiv 论文保留链接/DOI）
- `research-wiki`（现有，ARIS wiki 流程）
- `wiki-ingest`（可选，Obsidian wiki 流程）
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

- **运行时**: Claude Code `Agent` tool
- `subagent_type: general-purpose`
- `model: sonnet`
- 单篇论文超时：5 分钟

### 失败处理

- 超时 → 降级为粗读，保留 abstract + 标记 "deep-read-timeout"
- 提取失败 → 返回部分结果 + 标记 "partial-extraction"

---

## 修改 Skill: `research-lit`

### 设计决策：非破坏性修改

**不修改 `research-lit` 的默认行为**。当前逻辑为知识库优先：

```
research-lit (当前):
    1. Zotero → 本地已收藏论文
    2. Obsidian → 用户笔记
    3. Local PDFs → 本地文件
    4. Web (arXiv/S2/DeepXiv/Exa) → 外部检索
```

通过新增 `--sources: ieee` 参数启用 IEEE 优先流程，复用现有 `--sources:` 机制。

### 新增逻辑（IEEE 优先，通过参数启用）

当用户指定 `--sources: ieee` 时：

```
research-lit --sources: ieee:
    1. ieee-lit-search(query, venues, year_range) → IEEE 论文
    2. arxiv(query) → arXiv 预印本补充
    3. 按 DOI 去重合并
    4. lit-reading(papers) → 分级阅读 + 双写
    5. 返回 LIT_REVIEW.md 路径
```

### 与现有 `--sources:` 机制的关系

| 参数 | 行为 |
|------|------|
| `--sources: all` | 默认行为：Zotero → Obsidian → Local → Web |
| `--sources: ieee` | IEEE 优先：ieee-lit-search → arxiv → lit-reading |
| `--sources: ieee, zotero` | IEEE + Zotero（合并去重）|

### 新增参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `venues` | 核心期刊白名单 | 传递给 ieee-lit-search |
| `year_range` | 近 5 年 | 传递给 ieee-lit-search |
| `deep_read_top` | 5 | 传递给 lit-reading |

### 输出变化

- 默认（`--sources: all`）：返回论文元数据列表（保持不变）
- IEEE 模式（`--sources: ieee`）：返回 `LIT_REVIEW.md` 路径 + 论文列表

---

## 实现优先级

1. **P0**: `ieee-advanced-search` — IEEE 检索基础 skill
2. **P0**: `ieee-paper-fullcontent` — IEEE 全文提取 skill
3. **P0**: `ieee-paper-detail` — IEEE 元数据提取 skill
4. **P0**: `ieee-lit-search` — 核心检索编排
5. **P0**: `lit-reading` — 分级阅读编排
6. **P1**: `deep-reader` subagent — 精读 agent
7. **P1**: `research-lit` 修改 — 整合调用

---

## 风险与缓解

| 风险 | 缓解措施 |
|------|----------|
| IEEE 无访问权限 | 停止并询问用户：配置 VPN/代理？跳过 IEEE？ |
| IEEE Xplore 访问限流 | 多轮检索间加入延迟，缓存结果，检测 429 响应 |
| 付费墙全文 | 标记 `paywalled: true`，保留 abstract + DOI |
| 零 IEEE 结果 | 返回空列表，继续 arXiv 补充 |
| 精读 subagent 超时 | 设置 5 分钟超时，失败时降级为粗读 |
| 关键词生成质量不稳定 | 提供示例 prompt，要求 LLM 先输出推理过程 |
| arXiv 论文无 DOI | 保留 arXiv ID + 下载链接，不强制获取全文 |
| 论文重复（不同来源） | 按 DOI/arXiv ID/normalized title 三级去重 |
| LIT_REVIEW.md 已存在 | 追加时间戳版本，保留历史 |
| wiki 入库冲突 | 使用 `research-wiki` 的 slug 去重 + 相似度检测 |
| 输出目录不存在 | 自动创建 `idea-stage/` |
