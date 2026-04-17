# ARIS Vault Integration — 项目隔离输出

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让 ARIS 每次运行不同主题时，所有产出文件自动存放到 vault 的 `raw/projects/{slug}/` 目录下，实现主题隔离和知识库集成。

**Architecture:** 核心策略是 `cd` 传播：每个 orchestrator skill 在启动时解析 `PROJECT_DIR` 并 `cd` 进去，所有子 skill 的相对路径写入自然路由到正确目录。只在 orchestrator 级 skill 添加解析逻辑，不修改子 skill 的写入路径。slug 碰撞时追加日期后缀。

**Tech Stack:** Bash, Markdown, Claude Code skills

---

### Task 1: 创建 output-rules.md 共享参考

**Files:**
- Create: `/home/DataTransfer/Pyrojewel/vscode/Auto-claude-code-research-in-sleep/skills/shared-references/output-rules.md`

- [ ] **Step 1: 写入 output-rules.md**

内容：

```markdown
# ARIS 输出路径规则

## PROJECT_DIR 解析与传播

每个 ARIS orchestrator skill（idea-discovery, research-pipeline, auto-review-loop, rebuttal）启动时执行以下逻辑：

### 解析步骤

1. **用户指定** — 如果 `$ARGUMENTS` 包含 `-- project: /path/to/dir`，提取路径
2. **Vault 自动检测** — 从当前目录向上查找 `CLAUDE.md`：
   - 找到 → `vault_root = CLAUDE.md 所在目录`
   - 生成 slug（见下方规则）
   - 如果 `raw/projects/{slug}` 已存在 → `slug = {slug}-{YYYY-MM-DD}`（日期后缀避免碰撞）
   - `PROJECT_DIR = {vault_root}/raw/projects/{slug}/`
3. **默认** — `PROJECT_DIR = $(pwd)`（向后兼容）

### 传播策略

解析 `PROJECT_DIR` 后，执行：

```bash
mkdir -p "$PROJECT_DIR/refine-logs" "$PROJECT_DIR/paper"
cd "$PROJECT_DIR"
echo "📁 Project directory: $(pwd)"
```

所有子 skill 使用相对路径写入文件，`cd` 后自动路由到正确目录。

### Slug 生成规则

从 `$ARGUMENTS`（研究方向描述）生成 slug：

```
"passive device modeling for RF IC" → passive-device-modeling
"LNA noise optimization in 110nm"   → lna-noise-optimization
"AI-assisted topology synthesis"     → ai-topology-synthesis
```

规则：小写、空格→连字符、去掉介词（for/in/the/a/of）、截断到 5 个词以内。如果目标目录已存在，追加日期后缀。

### 目录结构

```
{PROJECT_DIR}/
├── IDEA_REPORT.md              — idea-discovery 产出
├── IDEA_CANDIDATES.md          — compact 模式
├── REF_PAPER_SUMMARY.md        — 参考论文摘要
├── RESEARCH_BRIEF.md           — 研究简报（用户可提供）
├── refine-logs/
│   ├── FINAL_PROPOSAL.md       — 精炼后的提案
│   ├── EXPERIMENT_PLAN.md      — 实验路线图
│   ├── EXPERIMENT_TRACKER.md   — 实验追踪
│   ├── REVIEW_SUMMARY.md       — 评审摘要
│   └── REFINEMENT_REPORT.md    — 精炼报告
├── AUTO_REVIEW.md              — auto-review-loop 累积日志
├── REVIEW_STATE.json           — 状态持久化
├── NARRATIVE_REPORT.md         — 研究叙事
├── STORY.md                    — 研究故事（compact）
├── findings.md                 — 关键发现（compact）
├── EXPERIMENT_LOG.md           — 实验日志（compact）
├── paper/                      — LaTeX 论文源文件
└── poster/                     — 会议海报（可选）
```

### 向后兼容

- 如果不在 vault 中运行，`PROJECT_DIR = $(pwd)`，行为不变
- 不破坏现有任何项目的文件布局
```

### Task 2: 修改 idea-discovery SKILL.md

**Files:**
- Modify: `/home/DataTransfer/Pyrojewel/vscode/Auto-claude-code-research-in-sleep/skills/idea-discovery/SKILL.md`

- [ ] **Step 1: 在 `## Pipeline` 之前（Phase 0 之前）插入 Project Directory Resolution 章节**

```markdown
## Project Directory Resolution

**Run this before Phase 0.** Determine and `cd` into the project output directory.

1. **Check for user override**: If `$ARGUMENTS` contains `-- project: <path>`, extract the path as `PROJECT_DIR`.
2. **Check for vault context**: Search upward from `$(pwd)` for `CLAUDE.md`:
   - Found → `vault_root = parent directory of CLAUDE.md`
   - Generate slug from `$ARGUMENTS`: lowercase, spaces→hyphens, remove stopwords (for/in/the/a/of), max 5 words
   - If `raw/projects/{slug}` already exists → append date: `{slug}-{YYYY-MM-DD}`
   - `PROJECT_DIR = {vault_root}/raw/projects/{slug}/`
3. **Fallback**: `PROJECT_DIR = $(pwd)` (current working directory, backward compatible)

Create directories and change to it:

```bash
mkdir -p "$PROJECT_DIR/refine-logs" "$PROJECT_DIR/paper"
cd "$PROJECT_DIR"
echo "📁 Project directory: $(pwd)"
```

All subsequent file operations naturally write to `$PROJECT_DIR` because all paths in this skill are relative.
```

- [ ] **Step 2: 不需要修改文件路径引用** — `cd` 传播已解决。

### Task 3: 修改 research-pipeline SKILL.md

**Files:**
- Modify: `/home/DataTransfer/Pyrojewel/vscode/Auto-claude-code-research-in-sleep/skills/research-pipeline/SKILL.md`

- [ ] **Step 1: 插入与 Task 2 相同的 Project Directory Resolution 章节**

- [ ] **Step 2: 不需要修改子 skill 调用** — 子 skill 继承当前工作目录。

### Task 4: 修改 auto-review-loop SKILL.md

**Files:**
- Modify: `/home/DataTransfer/Pyrojewel/vscode/Auto-claude-code-research-in-sleep/skills/auto-review-loop/SKILL.md`

- [ ] **Step 1: 在 `## Workflow` → `### Initialization` 之前插入 Project Directory Resolution**

```markdown
## Project Directory Detection

If `$ARGUMENTS` contains `-- project: <path>`, use that as `PROJECT_DIR`.
Otherwise, search upward from `$(pwd)` for `CLAUDE.md`:
- Found: `vault_root = parent directory`, generate slug, `PROJECT_DIR = {vault_root}/raw/projects/{slug}/`
- Not found: `PROJECT_DIR = $(pwd)`

Create `mkdir -p "$PROJECT_DIR" "$PROJECT_DIR/paper"` and `cd "$PROJECT_DIR"`.
```

### Task 5: 修改 experiment-bridge SKILL.md

**Files:**
- Modify: `/home/DataTransfer/Pyrojewel/vscode/Auto-claude-code-research-in-sleep/skills/experiment-bridge/SKILL.md`

- [ ] **Step 1: 在 Constants 之后、Phase 1 之前插入 Project Directory Resolution**（与 Task 4 相同模式）

### Task 6: 修改 paper-writing SKILL.md

**Files:**
- Modify: `/home/DataTransfer/Pyrojewel/vscode/Auto-claude-code-research-in-sleep/skills/paper-writing/SKILL.md`

- [ ] **Step 1: 插入 Project Directory Resolution**

- [ ] **Step 2: 将 `paper/` 备份逻辑改为相对于当前目录**

原逻辑：`paper/` 备份为 `paper-backup-{timestamp}/`。`cd` 后仍正确，无需修改。

### Task 7: 修改其他读取项目文件的 orchestrator skill

**Files:**
- Modify: `/home/DataTransfer/Pyrojewel/vscode/Auto-claude-code-research-in-sleep/skills/rebuttal/SKILL.md`
- Modify: `/home/DataTransfer/Pyrojewel/vscode/Auto-claude-code-research-in-sleep/skills/paper-plan/SKILL.md`
- Modify: `/home/DataTransfer/Pyrojewel/vscode/Auto-claude-code-research-in-sleep/skills/grant-proposal/SKILL.md`
- Modify: `/home/DataTransfer/Pyrojewel/vscode/Auto-claude-code-research-in-sleep/skills/research-refine/SKILL.md`
- Modify: `/home/DataTransfer/Pyrojewel/vscode/Auto-claude-code-research-in-sleep/skills/research-refine-pipeline/SKILL.md`

- [ ] **Step 1: 每个 skill 插入简化的 Project Directory Detection**

```markdown
## Project Directory

If already in a vault project directory (from a parent skill's cd), use current directory.
Otherwise, check for `-- project:` in `$ARGUMENTS` or vault detection (same as Task 2).
```

### Task 8: 在 vault 中创建 projects/ 目录并更新配置

**Files:**
- Create: `/mnt/d/obsidian_wiki/raw/projects/.gitkeep`
- Modify: `/mnt/d/obsidian_wiki/.claude/commands/wiki-init.md`
- Modify: `/mnt/d/obsidian_wiki/CLAUDE.md`

- [ ] **Step 1: 创建目录**

```bash
mkdir -p /mnt/d/obsidian_wiki/raw/projects
touch /mnt/d/obsidian_wiki/raw/projects/.gitkeep
```

- [ ] **Step 2: 更新 wiki-init.md** — 在 raw/ 路径列表中添加 `projects`

- [ ] **Step 3: 更新 CLAUDE.md** — 在 raw/ 子目录说明表中添加：

```
| `projects/` | ARIS 项目产出（按主题隔离） | `passive-device-modeling/IDEA_REPORT.md` |
```

### Task 9: 同步 skills 并验证

- [ ] **Step 1: 运行同步脚本**

```bash
bash /home/DataTransfer/Pyrojewel/vscode/Auto-claude-code-research-in-sleep/sync-skills.sh
```

- [ ] **Step 2: 验证** — 确认所有修改的 skill 已同步到 `~/.claude/skills/`

---

## 执行顺序

1 → 2 → 3 → 4 → 5 → 6 → 7 → 8 → 9

## 设计决策

| 决策 | 理由 |
|------|------|
| `cd` 传播而非变量替换 | 所有 skill 使用相对路径，`cd` 后自动路由，无需逐文件修改 |
| 只改 orchestrator | 子 skill 继承工作目录，修改量最小 |
| slug 碰撞追加日期 | 避免覆盖历史项目，保留完整的主题演进 |
| `-- project:` 参数 | ASCII 兼容，用户可指定任意输出路径 |

## 测试验证

```bash
# 在 vault 目录测试路径解析
cd /mnt/d/obsidian_wiki/
# 预期：PROJECT_DIR = /mnt/d/obsidian_wiki/raw/projects/{slug}/

# 在非 vault 目录测试（向后兼容）
cd /tmp/test-aris/
# 预期：PROJECT_DIR = /tmp/test-aris/
```
