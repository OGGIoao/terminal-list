#!/usr/bin/env python3
"""tkcore — terminal-kit 共享引擎（数据源无关）

把 pycheat 已验证的三件事抽象成任何「可检索文本域」都能复用的引擎：

  1. ollama 零依赖调用（仅 urllib 调本机 :11434，不引入 requests/numpy）
  2. 融合排序：本地匹配分数为基座 + 语义相对温和加成（绝不覆盖清晰命中）
  3. 模型感知向量缓存（按 domain 隔离；换嵌入模型自动失效重建）

另含处理型能力：本地 ollama 文本生成（explain / sum 用，需本机有 chat 模型）。

纯标准库，零额外依赖。tk 及其各子命令都是这台引擎上面的「数据源 + 模式」配置。
"""
import os, re, sys, json, math, difflib, hashlib, urllib.request

# ---------- ollama 基础 ----------
OLLAMA_TAGS_URL = "http://localhost:11434/api/tags"
OLLAMA_EMBED_URL = "http://localhost:11434/api/embeddings"
OLLAMA_GEN_URL = "http://localhost:11434/api/generate"
EMBED_MODEL_DEFAULT = "nomic-embed-text"           # 英文向，零额外拉取
EMBED_MODEL_PREFERS = ("bge-m3", "bge-m3:latest")  # 本机已拉则优先（中文更强）
SEMANTIC_W = 15.0        # 语义相对加成上限：本地分始终占主导，避免语义覆盖清晰命中
GEN_MODEL_PREFERS = ("qwen2.5:0.5b", "qwen2.5", "qwen3", "llama3.2")
# 这些名字是嵌入模型而非 chat 模型，挑生成模型时排除
_EMBED_NAME_HINTS = ("embed", "nomic", "bge")

CONFIG_DIR = os.path.expanduser("~/.config/cheat")
os.makedirs(CONFIG_DIR, exist_ok=True)


def ollama_available():
    """本机 ollama serve 是否在跑（短超时，不阻塞离线使用）。"""
    try:
        with urllib.request.urlopen(urllib.request.Request(OLLAMA_TAGS_URL), timeout=1.5) as r:
            return r.status == 200
    except Exception:
        return False


def _list_models():
    try:
        with urllib.request.urlopen(urllib.request.Request(OLLAMA_TAGS_URL), timeout=1.5) as r:
            return [m.get("name", "") for m in json.loads(r.read()).get("models", [])]
    except Exception:
        return []


def resolve_embed_model():
    """自动优先中文更强的 bge-m3（若本机已拉取），否则回退默认模型。"""
    if ollama_available():
        names = _list_models()
        for pref in EMBED_MODEL_PREFERS:
            if pref in names:
                return "bge-m3"
    return EMBED_MODEL_DEFAULT


def resolve_gen_model():
    """挑一个可用的 chat 模型（排除嵌入模型）；无则返回 None。"""
    if not ollama_available():
        return None
    names = _list_models()
    chat = [n for n in names if not any(h in n for h in _EMBED_NAME_HINTS)]
    for pref in GEN_MODEL_PREFERS:
        for n in chat:
            if n == pref or n.startswith(pref):
                return n
    return chat[0] if chat else None


# ---------- 向量化与相似度 ----------
def embed(text, is_query=False, model=None):
    """调 ollama embeddings；nomic 系列用 search_query/search_document 前缀对齐效果最佳。"""
    if model is None:
        model = resolve_embed_model()
    prefix = "search_query: " if is_query else "search_document: "
    payload = json.dumps({"model": model, "prompt": prefix + text}).encode("utf-8")
    req = urllib.request.Request(OLLAMA_EMBED_URL, data=payload,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read())["embedding"]


def cosine(a, b):
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    return dot / (na * nb) if na and nb else 0.0


def sha(s):
    return hashlib.md5(s.encode("utf-8")).hexdigest()


# ---------- 向量缓存（按 domain 隔离） ----------
def _vec_path(domain):
    return os.path.join(CONFIG_DIR, ".tk_%s_vectors.json" % domain)


def _load_vec(domain):
    try:
        with open(_vec_path(domain), encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def _save_vec(domain, d):
    try:
        with open(_vec_path(domain), "w", encoding="utf-8") as f:
            json.dump(d, f, ensure_ascii=False)
    except OSError:
        pass


def embed_units(units, domain):
    """units: list of {"key","text"}；返回 {key: vec}。按 domain 隔离缓存（hash+model）。"""
    model = resolve_embed_model()
    cache = _load_vec(domain)
    out = {}
    for u in units:
        k, text = u["key"], u["text"]
        h = sha(text)
        rec = cache.get(k)
        if rec and rec.get("hash") == h and rec.get("model") == model and rec.get("vec"):
            out[k] = rec["vec"]
        else:
            vec = embed(text, is_query=False, model=model)
            cache[k] = {"hash": h, "model": model, "vec": vec}
            out[k] = vec
    _save_vec(domain, cache)
    return out


# ---------- 离线打分（通用 unit） ----------
def _bigrams(s):
    s = s.lower()
    return {s[i:i + 2] for i in range(len(s) - 1)} if len(s) > 1 else {s}


def _overlap(a, b):
    x, y = _bigrams(a), _bigrams(b)
    if not x or not y:
        return 0
    return min(len(x & y), 3)


def offline_score(unit, q):
    """对通用 unit 打分：name/aliases 最高，二元组重叠捕捉「长人话」，text 次之。"""
    q = q.lower().strip()
    if not q:
        return 0
    s = 0
    name = str(unit.get("name", "")).lower()
    if q == name:
        s += 100
    elif q in name or name in q:
        s += 55
    s += 25 * _overlap(q, name)
    for a in unit.get("aliases", []):
        a = str(a).lower()
        if q == a:
            s += 90
        elif q in a or a in q:
            s += 45
        s += 30 * _overlap(q, a)
    blob = str(unit.get("text", "")).lower()
    if q in blob:
        s += 18
    s += 10 * _overlap(q, blob)
    return s


# ---------- 融合排序（通用 units） ----------
_llm_warned = False


def fused_rank(units, q, domain, require_llm=False):
    """通用融合排序：本地分基座 + 语义相对温和加成。units 每项含 key/text/name/aliases。

    - 本地分来自 offline_score()（name/别名/内容），清晰命中区间约 30~190。
    - 语义相似度相对本次查询最佳匹配线性归一到 [0,1] 再乘 SEMANTIC_W(=15)，
      不依赖具体嵌入模型绝对分布；强本地命中始终压过纯语义加成(<=15)。
    - 零本地分的卡若语义相对最佳也能被抬出（同义/近义浮上来）。
    - require_llm=True（强制语义）：ollama 不可用或向量化失败直接抛异常。
    """
    if not ollama_available():
        if require_llm:
            raise RuntimeError("ollama serve 未运行，无法做语义检索")
        return _rank_offline(units, q)
    try:
        qvec = embed(q, is_query=True)
        vecs = embed_units(units, domain)
    except Exception as e:
        if require_llm:
            raise
        if not _llm_warned:
            print("（⚠️ ollama 不可用：%s — 已退回本地匹配）" % e)
            _llm_warned = True
        return _rank_offline(units, q)
    sims = {}
    for u in units:
        v = vecs.get(u["key"])
        sims[u["key"]] = cosine(qvec, v) if v else -1.0
    vals = [s for s in sims.values() if s >= 0]
    lo, hi = (min(vals), max(vals)) if vals else (0.0, 0.0)
    span = (hi - lo) or 1.0
    merged = {u["key"]: [u, offline_score(u, q)] for u in units}
    for u in units:
        sv = sims.get(u["key"], -1.0)
        if sv >= 0:
            merged[u["key"]][1] += SEMANTIC_W * (sv - lo) / span
    ordered = sorted(((v[1], v[0]) for v in merged.values()), key=lambda x: -x[0])
    return [u for fin, u in ordered if fin > 0]


def _rank_offline(units, q):
    rs = [(offline_score(u, q), u) for u in units]
    rs = [(s, u) for s, u in rs if s > 0]
    rs.sort(key=lambda x: -x[0])
    return [u for _, u in rs]


# ---------- 处理型：本地 ollama 文本生成 ----------
def generate(prompt, system=None, model=None):
    """调 ollama /api/generate 做文本生成（explain / sum 用）。无 chat 模型则抛异常。"""
    if model is None:
        model = resolve_gen_model()
    if not model:
        raise RuntimeError("本机没有可用的 chat 模型；请先 `ollama pull qwen2.5:0.5b`")
    payload = {"model": model, "prompt": prompt, "stream": False}
    if system:
        payload["system"] = system
    req = urllib.request.Request(OLLAMA_GEN_URL,
                                 data=json.dumps(payload).encode("utf-8"),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=120) as resp:
        return json.loads(resp.read()).get("response", "")
