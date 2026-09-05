#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""pycheat — 个人终端命令速查 CLI（离线、零依赖，仅用 Python 标准库）。

用法:
  pycheat                开场屏（置顶+最近）→ 输入人话搜 / 数字选卡 / 回车看全部
  pycheat <说法>         按意图搜（命令名 / 别名 / 拼音 / 内容）→ 进入浏览，可继续翻
  pycheat -c <说法>      把最佳匹配的「示例」复制到剪贴板（⌘V 直接跑）
  pycheat -l             列出全部命令（带编号 + 一句话用途）
  pycheat --llm <说法>   本地 ollama 语义检索（同义/近义也能命中；无 ollama 时自动退回本地）

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
成长路线: 路线图「阶段2 转 Python CLI 接 LLM 语义查询」已落地——本地 ollama(nomic-embed-text) 做向量语义匹配，零额外依赖；无 ollama 时退回离线二元组匹配。
"""
import argparse
import difflib
import json
import math
import os
import re
import shutil
import subprocess
import sys
import time

CHEAT_SHEET = os.path.expanduser("~/.config/cheat/cheatsheet.md")
FIELDS = ["作用", "用法", "示例", "踩坑", "Windows对照", "来源卷", "别名"]


def resolve_sheet():
    """数据源解析：优先 ~/.config/cheat/cheatsheet.md（用户级，可跨机器同步）。

    首次若不存在，自动从脚本同目录的 cheatsheet.md 初始化到用户级——零配置即用，
    且用户加卡落在可同步目录、不污染仓库（Windows 首次clone即用，macOS 同理）。"""
    preferred = os.path.expanduser("~/.config/cheat/cheatsheet.md")
    if os.path.isfile(preferred):
        return preferred
    local = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cheatsheet.md")
    if os.path.isfile(local):
        try:
            os.makedirs(os.path.dirname(preferred), exist_ok=True)
            shutil.copyfile(local, preferred)
            print("（已为你初始化命令卡到 %s，可随时编辑；仓库内置副本保持不变）" % preferred)
        except OSError as e:
            print("（⚠️ 初始化失败：%s — 将临时使用仓库内置副本）" % e)
            return local
        return preferred
    sys.exit("❌ 找不到数据源: " + preferred)


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
    s += learned_boost(card, q, LEARNED)
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


# --- 本地 ollama 语义检索（零额外依赖，仅 urllib 调本机 11434）---
OLLAMA_TAGS_URL = "http://localhost:11434/api/tags"
OLLAMA_EMBED_URL = "http://localhost:11434/api/embeddings"
EMBED_MODEL_DEFAULT = "nomic-embed-text"      # 默认英文向嵌入；中文弱但零额外拉取
EMBED_MODEL_PREFERS = ("bge-m3", "bge-m3:latest")  # 若本机已拉取则优先（中文更强）
SEMANTIC_W = 15.0            # 语义相对加成上限：本地分始终占主导，避免语义覆盖清晰命中
VEC_PATH = os.path.expanduser("~/.config/cheat/.pycheat_vectors.json")


def ollama_available():
    """本机 ollama serve 是否在跑（短超时，不阻塞离线使用）。"""
    import urllib.request
    try:
        with urllib.request.urlopen(urllib.request.Request(OLLAMA_TAGS_URL), timeout=1.5) as r:
            return r.status == 200
    except Exception:
        return False


def resolve_embed_model():
    """自动优先中文更强的 bge-m3（若本机已拉取），否则回退默认模型。"""
    if ollama_available():
        try:
            import urllib.request
            with urllib.request.urlopen(urllib.request.Request(OLLAMA_TAGS_URL), timeout=1.5) as r:
                data = json.loads(r.read())
            names = [m.get("name", "") for m in data.get("models", [])]
            for pref in EMBED_MODEL_PREFERS:
                if pref in names:
                    return "bge-m3"
        except Exception:
            pass
    return EMBED_MODEL_DEFAULT


def _embed(text, is_query=False, model=None):
    """调 ollama embeddings；nomic 系列用 search_query/search_document 前缀对齐效果最佳。"""
    import urllib.request
    if model is None:
        model = resolve_embed_model()
    prefix = "search_query: " if is_query else "search_document: "
    payload = json.dumps({"model": model, "prompt": prefix + text}).encode("utf-8")
    req = urllib.request.Request(OLLAMA_EMBED_URL, data=payload,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read())["embedding"]


def _cosine(a, b):
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    return dot / (na * nb) if na and nb else 0.0


def _card_text(card):
    parts = [card["name"]] + aliases_of(card)
    for f in ("作用", "用法", "示例", "踩坑"):
        if f in card:
            parts.append(card[f])
    return " ".join(parts)


def _hash(s):
    import hashlib
    return hashlib.md5(s.encode("utf-8")).hexdigest()


def load_vectors():
    try:
        with open(VEC_PATH, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def save_vectors(d):
    try:
        os.makedirs(os.path.dirname(VEC_PATH), exist_ok=True)
        with open(VEC_PATH, "w", encoding="utf-8") as f:
            json.dump(d, f, ensure_ascii=False)
    except OSError:
        pass


def _embed_cards(cards):
    """每张卡向量化并缓存（按内容 hash + 模型名 增量更新）；返回 {name: [vec]}。

    缓存记录带 model 字段：切换嵌入模型（如 nomic -> bge-m3）后旧向量自动失效重建，
    避免用错模型的向量做语义排序。
    """
    model = resolve_embed_model()
    cache = load_vectors()
    out = {}
    for c in cards:
        nm = c["name"]
        text = _card_text(c)
        h = _hash(text)
        rec = cache.get(nm)
        if rec and rec.get("hash") == h and rec.get("model") == model and rec.get("vec"):
            out[nm] = rec["vec"]
        else:
            vec = _embed(text, is_query=False, model=model)
            cache[nm] = {"hash": h, "model": model, "vec": vec}
            out[nm] = vec
    save_vectors(cache)
    return out


_llm_warned = False


def fused_rank(cards, q, require_llm=False):
    """融合排序：本地匹配分数为基座，ollama 语义做「相对温和加成」，绝不覆盖清晰本地命中。

    - 本地分来自 score_card()（命名词/别名/内容，含自学习加成），清晰命中区间约 30~190。
    - 语义相似度先相对本次查询的最佳匹配线性归一到 [0,1]，再乘 SEMANTIC_W(=15)，
      因此不依赖具体嵌入模型的绝对分布；强本地命中(30+)始终压过纯语义加成(<=15)。
    - 零本地分的卡若语义相对最佳，也能被抬出（让「同义/近义」说法浮上来）。
    - require_llm=True（--llm 强制语义）：ollama 不可用或向量化失败直接抛异常。
    """
    if not ollama_available():
        if require_llm:
            raise RuntimeError("ollama serve 未运行，无法做语义检索")
        return rank(cards, q)
    try:
        qvec = _embed(q, is_query=True)
        vecs = _embed_cards(cards)
    except Exception as e:
        if require_llm:
            raise
        if not _llm_warned:
            print("（⚠️ ollama 语义检索不可用：%s — 已退回本地匹配）" % e)
            _llm_warned = True
        return rank(cards, q)
    # 收集本次相似度，找出 lo/hi 做相对归一（与具体嵌入模型分布无关）
    sims = {}
    for c in cards:
        v = vecs.get(c["name"])
        sims[c["name"]] = _cosine(qvec, v) if v else -1.0
    vals = [s for s in sims.values() if s >= 0]
    lo, hi = (min(vals), max(vals)) if vals else (0.0, 0.0)
    span = (hi - lo) or 1.0
    merged = {c["name"]: [c, score_card(c, q)] for c in cards}
    for c in cards:
        s = sims.get(c["name"], -1.0)
        if s >= 0:
            merged[c["name"]][1] += SEMANTIC_W * (s - lo) / span
    ordered = sorted(((v[1], v[0]) for v in merged.values()), key=lambda x: -x[0])
    return [card for fin_score, card in ordered if fin_score > 0]


def semantic_rank(cards, q):
    """纯语义排序（保留为调试入口）；主路径请用 fused_rank。"""
    return fused_rank(cards, q, require_llm=True)


def search_rank(cards, q, use_llm=None):
    """统一搜索入口：use_llm=None 自动探测 ollama；use_llm=False 强制离线（--no-llm）；
    语义失败/未配置则退回本地 rank()。"""
    if use_llm is False:
        return rank(cards, q)
    return fused_rank(cards, q, require_llm=False)


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
        record_strength(name)
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


# --- 增量自学习别名库（零依赖；人话说法 → 命中卡，固化后下次直接命中）---
LEARN_PATH = os.path.expanduser("~/.config/cheat/.pycheat_learned.json")


def load_learned():
    try:
        with open(LEARN_PATH, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def save_learned(d):
    try:
        os.makedirs(os.path.dirname(LEARN_PATH), exist_ok=True)
        with open(LEARN_PATH, "w", encoding="utf-8") as f:
            json.dump(d, f, ensure_ascii=False, indent=2)
    except OSError:
        pass


def record_learn(q, name, cards):
    """命中某卡后调用：若 q 是新的「人话说法」（非现成命令名/别名），固化 q→name。"""
    qn = q.lower().strip()
    if len(qn) < 2:
        return
    names = {c["name"].lower() for c in cards}
    alias_pool = set()
    for c in cards:
        alias_pool.update(aliases_of(c))
    if qn in names or qn in alias_pool:
        return  # 已是命令名/别名，无需学
    global LEARNED
    d = load_learned()
    rec = d.setdefault(qn, {}).setdefault(name, {"count": 0, "last": 0})
    rec["count"] += 1
    rec["last"] = int(time.time())
    save_learned(d)
    LEARNED = d


def learned_boost(card, q, learned):
    """学习库把 q 映射到本卡名 → 给高分（接近确切别名 90）。"""
    qn = q.lower().strip()
    if not qn:
        return 0
    return 88 if learned.get(qn, {}).get(card["name"]) else 0


# --- 记忆强度（间隔复习）：记录每张卡查看次数与上次时间 ---
STRENGTH_PATH = os.path.expanduser("~/.config/cheat/.pycheat_strength.json")


def load_strength():
    try:
        with open(STRENGTH_PATH, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def save_strength(d):
    try:
        os.makedirs(os.path.dirname(STRENGTH_PATH), exist_ok=True)
        with open(STRENGTH_PATH, "w", encoding="utf-8") as f:
            json.dump(d, f, ensure_ascii=False, indent=2)
    except OSError:
        pass


def record_strength(name):
    d = load_strength()
    rec = d.setdefault(name, {"count": 0, "last": 0})
    rec["count"] += 1
    rec["last"] = int(time.time())
    save_strength(d)


def due_for_review(cards):
    """返回该复习的卡名（≤5）：曾看过 且 (看得少 或 很久没看)。分数高=更该复习。"""
    d = load_strength()
    now = int(time.time())
    day = 86400
    due = []
    for c in cards:
        nm = c["name"]
        rec = d.get(nm, {"count": 0, "last": 0})
        cnt = rec.get("count", 0)
        last = rec.get("last", 0)
        if cnt < 1:
            continue  # 从没看过的不算「复习」，留给「新学」
        age = (now - last) / day if last else 999
        if cnt < 3 or age > 7:
            score = age + (3 - cnt) * 4
            due.append((score, nm))
    due.sort(reverse=True)
    return [nm for _, nm in due][:5]


LEARNED = load_learned()


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
                r2 = search_rank(order, q2)
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
    due = due_for_review(cards)
    llm_on = ollama_available()

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
        if due:
            print(BORD + "│" + R)
            print(BORD + "│ " + R + BOLD + "↻ 该复习的：" + R + DIM +
                  " · ".join(due) + R)
        if llm_on:
            print(BORD + "│ " + R + DIM + "🧠 语义检索已启用（ollama · " + resolve_embed_model() + "）" + R)
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
        r = search_rank(cards, line)
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
    ap.add_argument("--llm", action="store_true", help="强制本地 ollama 语义检索（不可用则报错退出）")
    ap.add_argument("--no-llm", dest="no_llm", action="store_true",
                    help="强制关闭语义检索，只用离线匹配（即便 ollama 在跑）")
    ap.add_argument("--learn", metavar="ACTION", nargs="?", const="show",
                    choices=["show", "clear"], help="查看/清空自学习别名库")
    ap.add_argument("--forget", metavar="说法", help="忘掉某个自学习说法")
    ap.add_argument("--suggest", action="store_true",
                    help="非交互：输出相关命令建议行（每行一个），供 zsh command_not_found_handler 调用")
    args = ap.parse_args()

    cards = load_cards(resolve_sheet())

    if args.learn == "clear":
        save_learned({})
        print("🧹 已清空自学习别名库（~/.config/cheat/.pycheat_learned.json）")
        return
    if args.learn == "show":
        d = load_learned()
        if not d:
            print("（自学习别名库为空。多用几次人话搜索，它会自动记住你的说法。）")
        else:
            print("自学习到的说法（说法 → 命令 · 命中次数）：")
            for q, m in sorted(d.items()):
                for nm, rec in m.items():
                    print("  %-22s → %-18s %d 次" % (q, nm, rec.get("count", 0)))
        return
    if args.forget:
        d = load_learned()
        d.pop(args.forget.lower().strip(), None)
        save_learned(d)
        print("🗑️ 已忘掉说法：「%s」" % args.forget)
        return

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
        # 显式 --llm：不可用就直接报错，不静默退回
        try:
            ranked = semantic_rank(cards, q)
        except Exception as e:
            print("pycheat: ⚠️ --llm 语义检索失败：%s" % e)
            print("        确认 ollama 已启动且已拉取嵌入模型：`ollama pull %s`" % resolve_embed_model())
            return
    else:
        # 自动：ollama 在跑就用语义，否则离线
        ranked = search_rank(cards, q, None if not args.no_llm else False)
    if not ranked:
        print("pycheat: 没找到和「%s」相关的命令卡。" % q)
        sug = suggest(cards, q)
        if sug:
            print("        你是不是想找：" + " / ".join(sug))
        else:
            print("        试试 pycheat -l 看全部，或换个说法。")
        return

    best = ranked[0]
    record_learn(q, best["name"], cards)
    if args.copy:
        copy_example(best)
        return

    # 命中即进入浏览：从最佳卡开始，按相关度可继续翻看其它匹配
    browse(ranked, 0)


if __name__ == "__main__":
    main()
