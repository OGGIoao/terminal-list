#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""pycheat — 个人终端命令速查 CLI（离线、零依赖，仅用 Python 标准库）。

用法:
  pycheat                开场屏（置顶+最近）→ 输入人话搜 / 数字选卡 / 回车看全部
  pycheat <说法>         按意图搜（命令名 / 别名 / 拼音 / 内容）→ 进入浏览，可继续翻
  pycheat -c <说法>      把最佳匹配的「示例」复制到剪贴板（⌘V 直接跑）
  pycheat -l             列出全部命令（带编号 + 一句话用途）
  pycheat --llm <说法>   （预留）LLM 语义增强；未配置模型/密钥时自动退回本地匹配

交互浏览（真实终端里）底部菜单:
  n/→/j  下一张      p/←/k  上一张      b 回退      f 前进
  c 复制示例         / 重新搜索          q 退出

设计要点（呼应「即查即用」初衷）:
  - 你不需要记命令名，只要会说「想做的事」（中文/拼音/英文都行）。
  - 每张卡可带 `别名:` 字段，把人话映射到命令；搜索优先级：命令名 > 别名 > 内容 > 模糊建议。
  - 无命中不再空白，而是用 difflib 给 top-3「你是不是想找」。
  - 卡面分区配色、按「用途 → 用法 → 示例 → 通俗别名 → 踩坑(红) → 平台对照(macOS/Linux↔Windows) → 来源」顺序排版，留白不挤；各字段颜色区分（用途青、用法绿、示例黄、别名品红、踩坑红、对照蓝）。
  - 进入浏览后不退出：翻页 / 回退 / 前进 / 复制 / 重新搜索都在一个会话里完成。

数据源: ~/.config/cheat/cheatsheet.md（仓库自带 cheatsheet.md 作兜底，clone 即可跑）
成长路线: 这是路线图「阶段2 转 Python CLI 接 LLM 语义查询」的第一步（当前纯离线）。
"""
import argparse
import difflib
import os
import re
import shutil
import subprocess
import sys

CHEAT_SHEET = os.path.expanduser("~/.config/cheat/cheatsheet.md")
FIELDS = ["作用", "用法", "示例", "踩坑", "Windows对照", "来源卷", "别名"]


def resolve_sheet():
    """数据源解析：优先 ~/.config/cheat/cheatsheet.md；仓库自带 cheatsheet.md 作兜底（clone 即可跑）。"""
    preferred = os.path.expanduser("~/.config/cheat/cheatsheet.md")
    if os.path.isfile(preferred):
        return preferred
    local = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cheatsheet.md")
    if os.path.isfile(local):
        return local
    return preferred  # 仍指向默认路径，保留原「找不到数据源」报错


def load_cards(path):
    """解析 cheatsheet.md，返回卡片列表（每张是 dict，含 name 与各字段）。"""
    if not os.path.isfile(path):
        sys.exit("❌ 找不到数据源: " + path)
    cards = []
    cur = None
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.rstrip("\n")
            m = re.match(r"^##\s+(.*)$", line)
            if m:
                if cur:
                    cards.append(cur)
                cur = {"name": m.group(1).strip()}
                continue
            fm = re.match(r"^-\s*([^:：]+)[:：]\s*(.*)$", line)
            if fm and cur is not None:
                key = fm.group(1).strip()
                val = fm.group(2).strip()
                cur[key] = val
    if cur:
        cards.append(cur)
    return cards


def aliases_of(card):
    return [a.strip().lower() for a in card.get("别名", "").split(",") if a.strip()]


def bigrams(s):
    """取连续 2 字片段（中文按字、英文按字符），用于模糊重叠打分。"""
    s = s.lower()
    return {s[i : i + 2] for i in range(len(s) - 1)} if len(s) > 1 else {s}


def overlap(a, b):
    """a、b 共享的二元组个数（取较小值封顶，避免长文本虚高）。"""
    x, y = bigrams(a), bigrams(b)
    if not x or not y:
        return 0
    return min(len(x & y), 3)


def score_card(card, q):
    """给一张卡对查询 q 打分：命令名/别名最高，二元组重叠捕捉「长人话」，内容次之。"""
    q = q.lower().strip()
    if not q:
        return 0
    s = 0
    name = card["name"].lower()
    if q == name:
        s += 100
    elif q in name or name in q:
        s += 55
    s += 25 * overlap(q, name)
    for a in aliases_of(card):
        if q == a:
            s += 90
        elif q in a or a in q:
            s += 45
        s += 30 * overlap(q, a)
    blob = " ".join(card.get(f, "") for f in ("作用", "用法", "示例", "踩坑")).lower()
    if q in blob:
        s += 18
    s += 10 * overlap(q, blob)
    return s


def rank(cards, q):
    """返回按相关度降序、得分>0 的卡片列表。"""
    rs = [(score_card(c, q), c) for c in cards]
    rs = [(s, c) for s, c in rs if s > 0]
    rs.sort(key=lambda x: -x[0])
    return [c for _, c in rs]


def candidates(cards):
    """所有「命令名 + 别名」组成的候选词，用于模糊建议。"""
    c = []
    for card in cards:
        c.append(card["name"].lower())
        c += aliases_of(card)
    return c


def suggest(cards, q):
    """无命中时，用 difflib 找最像的 3 个候选，反查回卡名。"""
    cands = candidates(cards)
    close = difflib.get_close_matches(q.lower(), cands, n=3, cutoff=0.35)
    out = []
    for cc in close:
        for card in cards:
            if cc == card["name"].lower() or cc in aliases_of(card):
                if card["name"] not in out:
                    out.append(card["name"])
                break
    return out[:3]


# --- 最近浏览历史（本地文件，零依赖；用于开场屏「最近查看」）---
HIST = os.path.expanduser("~/.config/cheat/.pycheat_recent")


def record_view(name):
    """把刚看过的卡名追加到本地历史，文件超 60 行则裁掉旧的。"""
    try:
        with open(HIST, "a") as f:
            f.write(name + "\n")
        with open(HIST) as f:
            lines = f.read().splitlines()
        if len(lines) > 60:
            with open(HIST, "w") as f:
                f.write("\n".join(lines[-60:]) + "\n")
    except OSError:
        pass


def recent_views(cards, exclude=()):
    """返回最近看过、且不在排除集里的卡名（去重、最多 5 个）。"""
    try:
        with open(HIST) as f:
            lines = f.read().splitlines()
    except OSError:
        return []
    names = {c["name"] for c in cards}
    seen, out = set(), []
    for n in reversed(lines):
        if n in names and n not in seen and n not in exclude:
            seen.add(n)
            out.append(n)
        if len(out) >= 5:
            break
    return out


# --- 颜色：仅交互终端启用，管道/重定向(NO_COLOR 或 非 tty)自动关闭 ---
import re as _re

_NOCOLOR = bool(os.environ.get("NO_COLOR")) or not sys.stdout.isatty()


def _c(code):
    return "" if _NOCOLOR else "\033[%sm" % code


R = _c(0)          # 复位
BOLD = _c("1")
CYAN = _c("1;36")  # 用途
GREEN = _c("1;32") # 用法 / macOS·Linux
YELLOW = _c("1;33")# 示例
MAG = _c("1;35")   # 通俗别名
RED = _c("1;31")   # 踩坑
BLUE = _c("1;34")  # 平台对照 / Windows
DIM = _c("2;37")   # 来源 / 边框
BORD = _c("90")    # 边框线

W = 58  # 卡面宽度


def _hilight_backticks(text, base):
    """示例里 `code` 包住的部分加粗，便于一眼看到该敲的命令。"""
    return _re.sub(r"`([^`]+)`", lambda m: BOLD + m.group(1) + R + base, text)


def render(card):
    """卡面：用途 → 用法 → 示例 → 通俗别名 → 踩坑(红) → 平台对照，分区不挤。"""
    print(BORD + "╭─ " + R + BOLD + card["name"] + R +
          BORD + " " + "─" * max(8, W - 4 - len(card["name"])) + R)
    print(BORD + "│" + R)

    if "作用" in card:
        print(BORD + "│ " + R + CYAN + "用途    " + R + card["作用"])
        print(BORD + "│" + R)

    if "用法" in card:
        print(BORD + "│ " + R + GREEN + "用法    " + R + card["用法"])
        print(BORD + "│" + R)

    if "示例" in card:
        ex = _hilight_backticks(card["示例"], YELLOW)
        print(BORD + "│ " + R + YELLOW + "示例    " + R + ex)
        print(BORD + "│" + R)

    if "别名" in card:
        al = "、".join(a.strip() for a in card["别名"].split(",") if a.strip())
        print(BORD + "│ " + R + MAG + "通俗别名" + R + "  " + MAG + al + R)
        print(BORD + "│" + R)

    if "踩坑" in card:
        print(BORD + "│ " + R + RED + "踩坑    " + R + RED + card["踩坑"] + R)
        print(BORD + "│" + R)

    win = card.get("Windows对照", "")
    if win:
        print(BORD + "│ " + R + BLUE + "平台对照" + R)
        print(BORD + "│   " + R + GREEN + "macOS / Linux : " + R + card["name"])
        print(BORD + "│   " + R + BLUE + "Windows       : " + R + win)
        print(BORD + "│" + R)

    if "来源卷" in card:
        print(BORD + "│ " + R + DIM + "来源    " + R + DIM + card["来源卷"] + R)

    print(BORD + "└" + "─" * W + R)


def _clipboard_command():
    """探测当前系统可用的剪贴板写入命令，返回 (args列表, 粘贴提示) 或 None。
    优先级：macOS pbcopy → Windows PowerShell → WSL clip.exe →
    Wayland wl-copy → X11 xclip/xsel → termux。"""
    import shutil
    import os

    # macOS
    if sys.platform == "darwin" and shutil.which("pbcopy"):
        return (["pbcopy"], "⌘V")

    # 原生 Windows（在 Windows 上跑 Python）
    if sys.platform == "win32":
        return (["powershell", "-NoProfile", "-Command",
                 "$input | Set-Clipboard"], "Ctrl+V")

    # WSL：直接用 Windows 的 clip.exe（路径固定，不依赖 PATH 解析 .exe）
    wsl_clip = "/mnt/c/Windows/System32/clip.exe"
    if os.path.exists(wsl_clip):
        return ([wsl_clip], "Ctrl+V（粘贴到 Windows 侧）")
    if shutil.which("clip.exe"):
        return (["clip.exe"], "Ctrl+V")

    # Linux（Wayland 优先，再 X11）
    if shutil.which("wl-copy"):
        return (["wl-copy"], "Ctrl+V")
    if shutil.which("xclip"):
        return (["xclip", "-selection", "clipboard"], "Ctrl+V")
    if shutil.which("xsel"):
        return (["xsel", "--clipboard", "--input"], "Ctrl+V")

    # Android / Termux
    if shutil.which("termux-clipboard-set"):
        return (["termux-clipboard-set"], "长按粘贴")

    return None


def copy_example(card):
    ex = card.get("示例", "")
    if not ex:
        print("（该卡无「示例」可复制）")
        return
    cb = _clipboard_command()
    if cb:
        args, paste_hint = cb
        try:
            subprocess.run(args, input=ex, text=True, check=True)
            print("✅ 示例已复制，直接 %s 运行：\n   %s" % (paste_hint, ex))
            return
        except Exception:
            pass  # 落到下面的手写降级
    print("（剪贴板不可用，请手动复制）示例: " + ex)


def list_all(cards):
    """格式化的命令清单（编号 + 一句话用途），不再裸拼名字。"""
    print("可用命令（共 %d 张）：" % len(cards))
    for i, c in enumerate(cards, 1):
        print("  %2d. %-24s %s" % (i, c["name"], c.get("作用", "")))


def read_key():
    """读一个按键（含方向键）。非交互终端返回 None。"""
    if not sys.stdin.isatty():
        return None
    try:
        import tty
        import termios
    except ImportError:
        return None
    fd = sys.stdin.fileno()
    try:
        old = termios.tcgetattr(fd)
    except Exception:
        return None
    try:
        tty.setraw(fd)
        c = sys.stdin.read(1)
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old)
    if c == "\x03":  # Ctrl-C
        raise KeyboardInterrupt
    if c == "\x1b":
        try:
            c2 = sys.stdin.read(1)
            c3 = sys.stdin.read(1)
        except Exception:
            return "esc"
        if c2 == "[":
            return {"C": "right", "D": "left", "A": "up", "B": "down"}.get(c3, "esc")
        return "esc"
    return c


def pick_card(cards):
    """交互选起始卡：优先 fzf（带用途、可搜），否则编号列表选择。非 tty 返回 0。"""
    if sys.stdin.isatty() and shutil.which("fzf"):
        lines = ["%s\t%s" % (c["name"], c.get("作用", "")) for c in cards]
        try:
            proc = subprocess.run(
                ["fzf", "--prompt", "命令 ▶ ", "--delimiter", "\t",
                 "--with-nth", "1,2", "--height", "50%", "--reverse"],
                input="\n".join(lines), text=True, capture_output=True,
            )
            pick = proc.stdout.strip()
        except Exception:
            pick = ""
        if pick:
            name = pick.split("\t", 1)[0]
            for i, c in enumerate(cards):
                if c["name"] == name:
                    return i
        return None  # fzf 被取消
    if sys.stdin.isatty():
        list_all(cards)
        while True:
            try:
                s = input("\n选序号（回车退出）: ").strip()
            except EOFError:
                return None
            if not s:
                return None
            try:
                n = int(s) - 1
                if 0 <= n < len(cards):
                    return n
            except ValueError:
                pass
            print("  ⚠️ 序号无效，重输")
    return 0


def print_menu():
    print(" " + BOLD + "n/→/j" + R + " 下一张   " + BOLD + "p/←/k" + R +
          " 上一张   " + BOLD + "b" + R + " 回退   " + BOLD + "f" + R + " 前进")
    print(" " + BOLD + "c" + R + " 复制示例      " + BOLD + "/" + R +
          " 重新搜索      " + BOLD + "q" + R + " 退出")


def browse(order, start):
    """交互浏览循环：渲染 + 底部菜单 + 翻页/回退/前进/复制/搜索，直到 q 退出。"""
    if not order:
        return
    idx = start
    hist, future = [], []
    tty = sys.stdout.isatty()
    while True:
        if tty:
            sys.stdout.write("\033[2J\033[H")  # 清屏，制造「翻页」观感
        print("〔 %d / %d 〕" % (idx + 1, len(order)))
        record_view(order[idx]["name"])
        render(order[idx])
        print_menu()
        k = read_key()
        if k is None:
            return  # 非交互：展示首张后即退出（脚本/管道场景）
        if k in ("q", "Q"):
            break
        if k in ("n", "right", "j", "down"):
            if idx < len(order) - 1:
                hist.append(idx)
                future.clear()
                idx += 1
        elif k in ("p", "left", "k", "up"):
            if idx > 0:
                hist.append(idx)
                future.clear()
                idx -= 1
        elif k == "b":
            if hist:
                future.append(idx)
                idx = hist.pop()
        elif k == "f":
            if future:
                hist.append(idx)
                idx = future.pop()
        elif k == "c":
            copy_example(order[idx])
            try:
                input("（回车继续）")
            except (EOFError, KeyboardInterrupt):
                break
        elif k == "/":
            try:
                q2 = input("\n重新搜索（输入说法）: ").strip()
            except (EOFError, KeyboardInterrupt):
                break
            if q2:
                r2 = rank(order, q2)
                if r2:
                    hist.append(idx)
                    future.clear()
                    order = r2
                    idx = 0
                else:
                    print("  ⚠️ 没找到「%s」，保持当前" % q2)
                    input("（回车继续）")
        # 其它键忽略


def show_opening(cards):
    """开场屏：价值主张 + 人话示例 + 置顶(常用)列表 + 最近查看 + 操作提示；进入小型 REPL。"""
    pinned = [c for c in cards if c.get("常用") and c["常用"] not in ("否", "no", "false")]
    pinned_names = [c["name"] for c in pinned][:6]
    recent = recent_views(cards, exclude=set(pinned_names))

    def screen():
        print(BORD + "╭─ " + R + BOLD + "pycheat · 离线命令速查" + R +
              BORD + " " + "─" * 36 + R)
        print(BORD + "│" + R)
        print(BORD + "│ " + R + CYAN + "说人话就能搜：" + R +
              GREEN + "看哪个程序最占内存" + R + " · " +
              GREEN + "哪个文件夹最大" + R + " · " +
              GREEN + "装个新软件" + R)
        print(BORD + "│" + R)
        print(BORD + "│ " + R + MAG + "★ 你可能关心的指令" + R)
        for i, nm in enumerate(pinned_names, 1):
            c = next(cc for cc in cards if cc["name"] == nm)
            print(BORD + "│ " + R + DIM + str(i) + R + BORD + "  " + R +
                  (c.get("作用", nm))[:16] + BORD + "  " + R + GREEN + nm + R)
        if recent:
            print(BORD + "│" + R)
            print(BORD + "│ " + R + YELLOW + "↺ 最近查看：" + R +
                  DIM + " · ".join(recent) + R)
        print(BORD + "│" + R)
        print(BORD + "└" + "─" * 46 + R)
        print(DIM + "操作：输入想做的事 " + R + BOLD + "↵" + R + DIM +
              " 搜 · 数字直接选 · " + BOLD + "↵" + R + DIM +
              " 看全部 · " + BOLD + "?" + R + DIM + " 帮助" + R)

    while True:
        screen()
        try:
            line = input(BOLD + "pycheat> " + R).strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return
        if line == "":
            start = pick_card(cards)
            if start is not None:
                browse(cards, start)
            continue
        if line == "?":
            print(DIM + "\n怎么用 pycheat：" + R)
            print("  • 直接打「想做的事」(中文/拼音/英文都行)，回车即搜")
            print("  • 打数字 1~%d 直接看「你可能关心的」对应卡" % len(pinned_names))
            print("  • 直接回车 → 浏览全部命令(fzf 搜索)")
            print("  • 看卡时：n 下一张 / p 上一张 / c 复制示例 / q 退出")
            try:
                input(DIM + "（回车返回开场）" + R)
            except (EOFError, KeyboardInterrupt):
                pass
            continue
        if line.isdigit():
            n = int(line) - 1
            if 0 <= n < len(pinned_names):
                browse([c for c in cards if c["name"] == pinned_names[n]], 0)
                continue
            print(DIM + "  ⚠️ 超出范围（1~%d）" % len(pinned_names) + R)
            continue
        r = rank(cards, line)
        if not r:
            sug = suggest(cards, line)
            print(DIM + "  ⚠️ 没找到「%s」" % line + R)
            if sug:
                print(DIM + "    你是不是想找：" + R + " / ".join(sug))
            try:
                input(DIM + "（回车返回开场）" + R)
            except (EOFError, KeyboardInterrupt):
                pass
            continue
        browse(r, 0)
        continue


def main():
    ap = argparse.ArgumentParser(description="个人终端命令速查（离线·即查即用）")
    ap.add_argument("query", nargs="*", help="想做的事 / 命令名 / 拼音")
    ap.add_argument("-c", "--copy", action="store_true", help="复制最佳匹配的示例到剪贴板")
    ap.add_argument("-l", "--list", action="store_true", help="列出全部命令（带编号+用途）")
    ap.add_argument("--llm", action="store_true", help="（预留）LLM 语义增强，未配置则退回本地")
    ap.add_argument("--suggest", action="store_true",
                    help="非交互：输出相关命令建议行（每行一个），供 zsh command_not_found_handler 调用")
    args = ap.parse_args()

    cards = load_cards(resolve_sheet())

    if args.list:
        list_all(cards)
        return

    if args.suggest:
        # 非交互建议模式：给 zsh 钩子用。输出 Top-3 相关命令名（每行一个），无则静默空输出。
        # 单字符查询噪声太大，直接忽略（zsh 钩子也已过滤 <2，这里双保险）。
        q = " ".join(args.query).strip()
        if len(q) >= 2:
            names = [c["name"] for c in rank(cards, q)[:3]]
            if not names:
                names = suggest(cards, q)
            for n in names:
                print(n)
        return

    if not args.query:
        # 无参数：真实终端先进开场屏（REPL），否则给格式化清单
        if sys.stdin.isatty():
            show_opening(cards)
            return
        list_all(cards)
        return

    q = " ".join(args.query).strip()

    if args.llm:
        print("（LLM 模式预留：当前未配置模型/密钥，已退回本地匹配）")

    ranked = rank(cards, q)
    if not ranked:
        print("pycheat: 没找到和「%s」相关的命令卡。" % q)
        sug = suggest(cards, q)
        if sug:
            print("        你是不是想找：" + " / ".join(sug))
        else:
            print("        试试 pycheat -l 看全部，或换个说法。")
        return

    best = ranked[0]
    if args.copy:
        copy_example(best)
        return

    # 命中即进入浏览：从最佳卡开始，按相关度可继续翻看其它匹配
    browse(ranked, 0)


if __name__ == "__main__":
    main()
