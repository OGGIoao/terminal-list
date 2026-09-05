# STATUS.md — terminal-list 当前状态

> 唯一当前态。更新进度 / 下一动作 / 阻塞时只改本文件，不在多处重复维护。
> 更新日期：2026-09-05

## 当前主线

个人终端工具箱已成型且全部推到 GitHub：主搜索 `pycheat`（离线 + ollama 融合语义）、跨域套件 `tk`（7 域）、跨平台（macOS / Windows）。最新提交 `9ab0cd4` 刚完成 Windows 支持。随后用户决定「换人接手」，故建立本仓库**自包含中枢**（`AGENTS.md` / `STATUS.md` / `MEMORY.md`，取代此前指向私人 iCloud 的软链），以便交接。

## 已完成（按提交线）

1. init：三套核心文档（OS 课 / 芯片课 / 工具箱）
2. 仓库自包含化：去掉 Obsidian 软链，纳入脚本
3. 废弃旧版 `cheat`
4. 剪贴板跨平台化
5. 增量自学习别名 + 间隔复习
6. ollama 语义检索 → 融合排序（`bge-m3` 自动优先）
7. `bge-m3` 拉取成功 + 缓存模型感知修复 + 使用说明文档
8. ollama 卡实战示例 + `ollama show` 演示卡 + 速查小抄附录
9. `tk` 跨域套件（`tkcore` 引擎 + 7 域：note / log / gitx / clip / todo / explain / sum）
10. 跨平台支持（`.cmd` 入口 + `install.ps1` + 首次自动初始化 cheatsheet）
11. **本批：建立仓库自包含中枢（换人接手用）**

## 当前状态

- 最新提交：`9ab0cd4`（跨平台）
- 工具箱功能：全可用（mac / win）。`explain` / `sum` 需本机有 **chat 模型**才可用（`bge-m3` / `nomic-embed-text` 不能对话）。
- 已实测验证：`note` / `todo` / `gitx` / `clip` / `log` 语义召回（含「连接被拒绝」→ 英文 `connection refused` 段 的**跨语言捞针**）；`explain` / `sum` 缺 chat 模型时友好降级。
- 中枢：本仓库现含 `AGENTS.md` / `STATUS.md` / `MEMORY.md`（自包含，已纳入 git）；旧的 iCloud 软链移为 `.icloud.bak` 且不提交。

## 下一动作（接手人可接）

1. 可选：拉 chat 模型 `ollama pull qwen2.5:0.5b`，让 `explain` / `sum` 立即可用。
2. 可选：把 `tk` 软链到 `~/bin/tk`（参照 `pycheat` 的 `~/bin` 做法），统一入口。
3. 可选（B 方案，未做）：把 `hi` / `gup` 用 Python 重写跨平台版（当前是 bash + mac 专属命令 `sw_vers` / `sysctl`，Windows 暂不可用）。
4. 用户待决：iCloud 软链 `AGENTS.md` / `CLAUDE.md` 是否纳入公开仓库（**当前决定：不纳入**，已改为自包含）。

## 阻塞 / 风险

- 无硬阻塞。唯一风险是公开仓库误含 iCloud 私有路径软链——已在本次中枢化时排除（改为自包含文件）。
- ollama 偶发 502 / 服务不健康：`tk` 已在启动期探测并温和提示；**跨语言查询（中文查英文日志）强依赖 ollama 健康**。

## 接手人第一步

1. `git clone` 仓库（或拷贝 `terminal-toolbox/`）。
2. 读 `AGENTS.md` → 本文件 → `MEMORY.md` → 最近日记 `2026-09-05.md`。
3. 装 Python（3.9+，勾 Add to PATH）。
4. （可选）装 ollama + `ollama pull bge-m3` 开语义检索。
5. **macOS**：把 `pycheat` / `tk` 软链到 `~/bin`。**Windows**：PowerShell 跑 `install.ps1` 后重开终端，用 `c` / `tk`。
6. 试：`c`、`c 查端口占用`、`tk note 记一笔`、`tk log "连接被拒绝" -p app.log`。
