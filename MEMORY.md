# terminal-list 长期记忆（MEMORY.md）

> 本文件只存跨任务长期有效的事实与约定，不记当前进度（进度看 STATUS.md）。
> 接手顺序：AGENTS.md → STATUS.md → MEMORY.md → 最近日记 → 按需读专题文件。

## 1. 项目定位

- 个人终端工具箱：自研 shell / Python CLI 小工具，命令行卡片「即查即用、意图式搜索」；你不用记命令名，只要会说想做的事。
- 公开仓库：`https://github.com/OGGIoao/terminal-list`
- 设计审美：**可复用、可迁移、单一数据源（Source of Truth）**；零散能力要收束成统一入口，不堆积互不相关的小脚本（用户长期规矩）。

## 2. 架构（单一数据源 + 适配器 + 融合排序）

- **单一数据源**：`~/.config/cheat/cheatsheet.md`（~48 张卡）。改卡 = 改这一个文件，存盘即生效，没有「代码里写死一份、文档里又写一份」的漂移。
- **适配器**：`load_cards()` 把 markdown 翻译成结构化卡片 dict（name / 别名 / 作用 / 用法 / 示例 / 踩坑）。换数据格式（YAML / Obsidian 属性）只改这一个函数，上层不动。
- **排序双路（关注点分离，可替换）**：
  - 离线 `score_card()`：本地匹配（命名词 / 别名二元组 / 正文命中打分），零联网零依赖，永远可用。
  - ollama 语义：`fused_rank()` = 本地分占主导 + 语义相似度相对归一到 [0,1] × `SEMANTIC_W=15` 温和加成。**强本地命中永远压住语义；零本地分的近义卡才被语义抬出**。绝不因语义覆盖清晰本地命中。
  - ⚠️ **铁律**：不要改回纯语义替换。`nomic-embed-text` 是英文向，短中文区分度差（全挤 0.5–0.66，区分度仅 0.15–0.22），纯语义会把 `kill` 误排到 `type` 后。已踩过坑。
- **展示层**：开场屏（推荐 / 间隔复习 / 语义提示）/ 卡面四段彩色（作用 / 用法 / 示例 / 踩坑）/ 复制 / 间隔复习。

## 3. 工具清单

| 工具 | 形态 | 用途 |
|------|------|------|
| **pycheat**（别名 `c`） | Python CLI（`pycheat.py`） | 主搜索引擎：离线意图 + ollama 融合语义 |
| **tk** | Python CLI（`tk` + `tkcore.py`） | 跨域套件：note / log / gitx / clip / todo / explain / sum |
| **hi** | bash（`hi.sh`） | 系统 / 硬件速查（mac 专属命令，未跨平台） |
| **gup** | bash（`gup.sh`） | 当前仓库一键 git 同步（ff-only，绝不 rm / reset） |
| **cheat** | zsh 函数 | 旧版，已废弃，由 pycheat 取代 |
| **seed_aliases.py** | Python | 批量补中文别名 |

- **tk 套件**：`tkcore.py` 是共享引擎（移植 pycheat 已验证的融合排序 + ollama 零依赖调用 + 模型感知缓存），`tk` 是统一入口；7 域只是「采集函数 + 存储」差异，引擎不动。
  - 检索型：note（快记本）/ log（日志跨语言语义捞针）/ gitx（提交语义搜）/ clip（剪贴板历史语义搜）/ todo（任务盒）
  - 处理型：explain（命令翻人话）/ sum（长输出摘要）—— **均需本机 chat 模型**

## 4. 关键约定与硬伤

- **ollama 语义检索**：默认 `nomic-embed-text`；若本机已拉取 `bge-m3` 则 `resolve_embed_model()` 自动优先（中文区分度约 nomic 的 6–7 倍）。向量缓存按「内容 hash + 模型名」存 `~/.config/cheat/.pycheat_vectors.json`，换模型自动失效重建。
- **零依赖**：只调标准库 `urllib` 调本机 `:11434`，不用 `requests` / `numpy`，避免污染环境（managed 隔离规矩）。
- **称呼约定**（用户指定，2026-08-27）：AI 助手名 = 小o，用户自称 = 老Z（仅该会话有效；接手人不必沿用）。
- **协作风格**（用户指定，2026-08-28）：先商量再动手——先给诊断 + 建议 + 带选项提问，让用户拍板关键分叉再实现。
- **用户背景**：从 Windows 转 macOS 的新手；讲解对照 Windows 概念、多用图示，不默认熟悉 unix 习惯。要深入底层、边讲边装、读一手资料。

## 5. 跨平台（2026-09-05 落地）

- 已支持 Windows：`pycheat.cmd` / `tk.cmd` 入口；`install.ps1` 一键加 PATH + PowerShell 别名 `c` / `pycheat` / `tk`（幂等可重跑）；首次运行自动初始化 cheatsheet（从同目录出厂副本复制到 `~/.config/cheat/`，零配置且不污染仓库）。
- 剪贴板：pycheat 复制 + tk 读取均已做 darwin / win32 / WSL / X11 全分支。
- 待补（B 方案，未做）：`hi` / `gup` 是 bash + mac 专属命令（`sw_vers` / `sysctl`），Windows 暂不可用。

## 6. 遗留与红线（接手人务必看）

- ⚠️ 仓库根的 `AGENTS.md` / `CLAUDE.md` 此前是 iCloud 软链（指向用户私有 Obsidian 知识中枢），**未纳入公开仓库**（泄露私有路径风险）。现已改为自包含 `AGENTS.md` / `CLAUDE.md` / `STATUS.md` / `MEMORY.md` 纳入 git。**不要在公开仓库恢复 iCloud 软链**。
- 单一数据源纪律：`cheatsheet.md` 是知识真源，不复制内容进代码或文档再维护两份。
- git 安全：只 add 本任务涉及文件；绝不 `git rm` / `reset`；个人目录走 `gup` 红线（ff-only，不 rm）。
- 自动化数据 `~/.workbuddy/workbuddy.db` 绝不用 `rm` / `sqlite3` / shell 删，只用自动化管理工具。
- **已修真 bug（避免回归）**：① tk 的 id 秒级碰撞（同秒多 add 显示错乱，改 uuid 后缀）② 源副本曾缺 `cheatsheet.md` 致 Windows 首次崩溃（已补出厂副本）③ 向量缓存未记模型名误用旧向量（已加 model 字段）。
