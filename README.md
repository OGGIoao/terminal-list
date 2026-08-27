# 个人终端工具箱 · Personal Terminal Toolbox

> 把我亲手用 shell / Python 造的命令行工具与脚本，沉淀成**可复用、可检索、可跨机器同步**的个人命令库。
> 设计初衷：**你不用记命令名，只要会说"想做的事"**（中文 / 拼音 / 英文都行），工具替你找到该敲的那条。

---

## 这是什么

一个"边学边造"的 terminal 工具箱。它既是**活文档**（每张卡记录一个工具的用途 / 用法 / 示例 / 通俗别名 / 踩坑 / 平台对照），也是**可运行的脚本集合**（`pycheat` / `hi` / `gup`）。

配套课程文档（也在此仓库，便于追溯背景）：
- [`个人终端工具箱.md`](个人终端工具箱.md) — 本工具箱的说明书与成长路线图（工具卡 #1–#4 在此）
- [`操作系统底层与终端精通课程.md`](操作系统底层与终端精通课程.md) — 主线课程，工具卡里的"关联 OS 课卷"指向它
- [`芯片架构横向博览知识系统.md`](芯片架构横向博览知识系统.md) — 横向行业追踪

---

## 工具清单

| # | 工具 | 形态 | 一句话 |
|---|------|------|--------|
| 1 | `cheat`（✗ 已废弃） | zsh 函数 | **已由 `pycheat` 取代**（`c` 别名现指向 pycheat；敲错提示钩子改调 `pycheat --suggest`） |
| 2 | `hi` | shell 脚本（`hi.sh`，软链 `~/bin/hi`） | 你是谁 / 在哪台机器 / 什么系统芯片，一眼看清 |
| 3 | `gup` | shell 脚本（`gup.sh`，软链 `~/bin/gup`） | 一键 git 同步（pull ff-only → 提交 → push），安全红线不 rm/不 force |
| 4 | `pycheat` | Python CLI（`pycheat.py`，软链 `~/bin/pycheat`） | 离线命令速查：开场屏（置顶+最近+↻该复习的）+ 人话搜索 + 自学习别名 + **本地 ollama 语义检索**(同义也能命中) + 彩色卡面 + 浏览不退出 |

更完整的字段说明、截图式卡面示例，见 [`个人终端工具箱.md`](个人终端工具箱.md)。

---

## 目录结构

```
terminal-list/
├── README.md
├── 个人终端工具箱.md                 # 活文档（工具卡 + 路线图）
├── 操作系统底层与终端精通课程.md      # 主线课程
├── 芯片架构横向博览知识系统.md        # 横向行业追踪
├── 阶段总结-2026-08-12.md
├── LICENSE
├── .gitignore
├── terminal-toolbox/                # ← 真正可运行的工具
│   ├── pycheat.py        # 工具#4：命令速查 CLI（仅标准库；可选接本机 ollama 做语义检索，零额外依赖）
│   ├── hi.sh             # 工具#2：系统/身份速览
│   ├── gup.sh            # 工具#3：安全一键 git 同步
│   ├── seed_aliases.py   # 给 cheatsheet 批量补「别名:」字段的辅助脚本
│   └── cheatsheet.md     # 数据源（47 张卡，含 7 张 ollama 指令卡）；pycheat 读它
└── 可视化放映/                      # 课程配套幻灯片（HTML）
```

---

## 安装（macOS）

> 下面用 `~/bin` 做用户级命令目录（无需 `sudo`）。若该目录不在 `PATH`，先在 `~/.zshrc` 加一行：
> `export PATH="$HOME/bin:$PATH"`

```bash
# 1) 克隆（或下载）本仓库
git clone https://github.com/OGGIoao/terminal-list.git
cd terminal-list

# 2) 把脚本软链成全局命令（注意保持可执行）
chmod +x terminal-toolbox/*.sh terminal-toolbox/pycheat.py
ln -s "$PWD/terminal-toolbox/hi.sh"        ~/bin/hi
ln -s "$PWD/terminal-toolbox/gup.sh"       ~/bin/gup
ln -s "$PWD/terminal-toolbox/pycheat.py"   ~/bin/pycheat

# 3) 桥接层：c 别名 + 敲错提示钩子（旧版 cheat.zsh 已废弃，这里重建精简版）
cat > ~/.cheat.zsh <<'EOF'
# 个人终端工具箱 · 桥接层（c=pycheat + 敲错提示）
alias c='pycheat'
command_not_found_handler() {
  local q="$1"
  [ "${#q}" -lt 2 ] && return 127
  local hits
  hits=$(pycheat --suggest "$q" 2>/dev/null)
  [ -n "$hits" ] && echo "💡 你是不是想用这些命令？"$'\n'"$hits"
  return 127
}
EOF
echo '[ -s "$HOME/.cheat.zsh" ] && \. "$HOME/.cheat.zsh"' >> ~/.zshrc
source ~/.zshrc

# 4) 放好数据源 cheatsheet（推荐；不放也能跑，见下方"兜底"）
mkdir -p ~/.config/cheat
cp terminal-toolbox/cheatsheet.md ~/.config/cheat/cheatsheet.md
```

**Windows / Linux 说明**
- `hi.sh` / `gup.sh` 是 POSIX shell 脚本，在 Linux/macOS 通用；Windows 需用 WSL 或 Git Bash。
- `pycheat.py` 是纯 Python 标准库，**跨平台可跑**。剪贴板复制自动探测：macOS `pbcopy` / Windows PowerShell / WSL `clip.exe` / Linux `wl-copy`·`xclip`·`xsel` / Termux，均无则降级为手写复制。

**cheatsheet 兜底**：`pycheat` 优先读 `~/.config/cheat/cheatsheet.md`；若该路径不存在，会自动改用**脚本同目录的 `cheatsheet.md`**。所以即便跳过第 4 步，clone 下来直接 `python3 terminal-toolbox/pycheat.py` 也能用。

---

## 快速上手

```bash
# pycheat：说人话就能搜
pycheat                       # 开场屏：置顶常用 + 最近查看 + ↻该复习的，输入"想做的事"回车即搜
pycheat 看哪个程序最占内存     # 直接意图搜索 → 进入彩色卡面浏览（命中后该说法被记住，下次直命中）
pycheat -c 看哪个文件夹最大    # 把最佳匹配的「示例」复制到剪贴板，⌘V 直接跑
pycheat -l                    # 列出全部 47 张卡（编号 + 一句话用途）
pycheat --learn show          # 查看你「教给它的」人话说法与命中次数
pycheat --forget 看哪个程序最占内存   # 忘掉某个自学习说法
pycheat --llm 哪个进程吃 RAM       # 强制本地 ollama 语义检索（同义也能命中；无 ollama 则报错退出）
pycheat --no-llm 看哪个程序最占内存  # 强制离线匹配（即便 ollama 在跑）

# c（= pycheat 的短名，已接好别名与敲错提示钩子）
c                             # 进开场屏：置顶常用 + 最近查看，输入"想做的事"回车即搜
c df                          # 直接搜某条

# hi：我是谁 / 在哪 / 什么芯片
hi
hi -v                         # 附带芯片架构信息

# gup：安全一键同步当前仓库
gup                           # 在当前 git 仓库里：ff-only pull → 时间戳提交 → push
```

浏览卡面时底部菜单：
`n/→/j` 下一张 · `p/←/k` 上一张 · `b` 回退 · `f` 前进 · `c` 复制示例 · `/` 重新搜索 · `q` 退出

---

## 数据源与自定义

所有卡片都在 `terminal-toolbox/cheatsheet.md`，格式极简——`## 标题` 起一张卡，下面用 `- 字段: 值` 写字段：

```markdown
## df
- 作用: 看磁盘各分区还剩多少空间
- 用法: df -h
- 示例: `df -h`
- 别名: 磁盘空间、哪个盘满了、disk free
- 踩坑: 默认按块显示不直观，务必加 -h 看人类可读单位
- Windows对照: macOS/Linux 用 df -h；Windows 用 `wsl df -h` 或资源管理器属性
- 来源卷: 终端工具箱·磁盘
```

- 想加自己的命令？直接往 `cheatsheet.md` 追加 `## 新命令` + 字段即可，`pycheat` / `c` 立刻能搜到。
- `别名:` 字段是"人话命中"的关键（中文二元组重叠 + 拼音 + 英文都能匹配）；`seed_aliases.py` 可批量给已有卡片补别名。
- `常用: 是` 标记的卡会出现在 pycheat 开场屏的"★ 你可能关心的指令"。

---

## 成长路线

工具按"循序渐进"的方式沉淀，逐步从易到难：

```
alias 别名  →  zsh 函数  →  .sh 脚本  →  软链到 ~/bin（用户级）
                                       →  oh-my-zsh 插件（团队化）
                                       →  Python CLI + 本地 ollama 向量语义查询（阶段2·已落地）
```

`pycheat` 是当前路线图的"阶段 2"：**离线、零依赖、即查即用**为基础，叠加**自学习别名**（越用越懂你）、**间隔复习**（开场屏提醒巩固）与**本地 ollama 语义检索**（同义/近义也能命中）。语义检索零额外依赖（仅 `urllib` 调本机 `11434`），自动探测 ollama——在跑就用语义、否则退回离线；`--llm` 强制、`--no-llm` 强制离线。

> 排序策略是**本地匹配为主、语义为温和加成**的融合排序（fusion）：本地命中分占主导，语义相似度只做相对温和加成，**绝不让语义覆盖一个清晰的本地命中**；零本地分的近义卡也能被语义抬出。嵌入模型默认 `nomic-embed-text`，若本机已拉取中文更强的 `bge-m3` 会自动优先（无需改代码）。

---

## 安全红线（务必遵守）

- `gup` 只在**当前仓库内**操作；**绝不 `rm` / `reset --hard` / `force push`**；先 ff-only pull 再提交，无改动直接退出。
- 自动化数据 `~/.workbuddy/workbuddy.db` **绝不用 `rm`/`sqlite3`/shell 删除**，只走自动化管理工具。
- 个人目录只提交明确要同步的文件，不盲目把无关改动一并提交。

---

## License

见 [`LICENSE`](LICENSE)（MIT）。
