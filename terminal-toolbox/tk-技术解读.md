# tk（terminal-kit）技术解读

> 把 pycheat 验证过的「卡片化 + 适配器 + 本地语义融合」范式，抽象成一个**数据源无关的共享引擎**，
> 再用统一入口 `tk` 覆盖终端里多个「平时靠人肉翻、本质是可检索/可处理文本」的域。
> 纯标准库，零额外依赖。本文档基于 `tkcore.py` 与 `tk` 的真实代码。

---

## 0. 一句话定位

`tk` 不是 7 个脚本，而是**一个引擎 + 7 个「数据源 + 模式」配置**：

- **引擎 `tkcore.py`**：融合排序 + ollama 零依赖调用 + 模型感知向量缓存 + 本地生成。
- **配置 `tk`**：`note / log / gitx / clip / todo`（检索型）+ `explain / sum`（处理型），每个域只是「采集函数 + 存储方式」的差异，引擎不动。

加一个新域 = 写一个采集函数（把数据变成 `units` 列表），不需要碰排序/向量/ollama 任何一行。

---

## 1. 为什么能跨域：核心抽象

pycheat 把「命令」当成卡片排序。但排序这件事，对任何「文本单元」都成立——
只要你能把数据切成一条条**带可搜索文本的单元**，就能套同一个融合排序。

`tkcore` 把 pycheat 里写死的「卡片」抽象成通用 **unit**：

```python
unit = {
    "key":     "唯一标识（用于缓存与显示去重）",
    "name":    "短名（最高优先级匹配，类似命令名）",
    "text":    "可搜索正文（语义向量化对象）",
    "aliases": ["人话别名 / 标签（次优先级匹配）"],   # 可选
}
```

所有域都先把数据**适配**成 `units`，再交给 `fused_rank(units, q, domain)`。这就是适配器模式：
`tk` 里的每个域函数（note_search / log_search / gitx_search / ...）就是一个适配器，
把「jsonl 行 / 日志段落 / git 提交 / 剪贴板记录 / 任务项」翻译成同一套 unit 结构。

---

## 2. 三个可复用支柱

### 2.1 ollama 零依赖调用

只用标准库 `urllib` 调本机 `:11434`，不引入 `requests`/`numpy`（保持「managed 隔离」）。两个接口：

- **embeddings**（`/api/embeddings`）：`embed(text, is_query, model)`。nomic 系列用
  `search_query: ` / `search_document: ` 前缀对齐效果（已在 pycheat 验证）。
- **generate**（`/api/generate`）：`generate(prompt, system, model)`，供 `explain`/`sum` 用。

模型选择自动分级：

```python
EMBED_MODEL_PREFERS = ("bge-m3", "bge-m3:latest")   # 中文更强，本机已拉则优先
EMBED_MODEL_DEFAULT  = "nomic-embed-text"           # 英文向，零额外拉取
# 生成模型排除嵌入模型（bge/nomic 不能对话），优先 qwen2.5:0.5b 等
```

`resolve_embed_model()` 探测本机已装模型，自动挑 `bge-m3`；`resolve_gen_model()` 排除嵌入模型后挑 chat 模型。

### 2.2 融合排序（本地基座 + 语义温和加成）

这是从 pycheat 移植并已实测的核心算法。对一个查询 `q` 和候选 units：

1. **本地分** `offline_score(unit, q)`：命名词/别名最高，二元组重叠捕捉「长人话」，正文次之。清晰命中约 30–190。
2. **语义相似度** `cosine(qvec, unit_vec)`：先相对本次查询的最佳匹配线性归一到 `[0,1]`，再乘 `SEMANTIC_W(=15)`。
3. **最终分 = 本地分 + 语义加成**，过滤掉 ≤0 的。

关键设计：**相对归一**让算法不依赖任何嵌入模型的绝对分布——bge-m3 或 nomic 都能用，区分度差异只影响加成大小，不影响「本地命中永远压得住语义」这一性质：

```
强本地命中(≥30)  ≫  纯语义加成(≤15)   → 语义绝不会覆盖一个清晰的本地命中
零本地分(=0)     +  语义相对最佳(=15)  → 同义/近义说法仍能被抬出
```

ollama 不可用时整批退回 `offline_score`（零额外开销），但**跨语言查询**（如中文查英文日志）本地分必为 0，此时强依赖 ollama；`tk` 已在启动期探测 ollama，未运行/不健康时打印一行温和提示，避免静默空结果误导。

### 2.3 模型感知向量缓存（per-domain 隔离）

每张卡的向量按 `内容hash + 模型名` 存盘，按 **domain 隔离**到 `~/.config/cheat/.tk_<domain>_vectors.json`：

```python
cache[nm] = {"hash": h, "model": model, "vec": vec}
```

切换嵌入模型（nomic→bge-m3）后，旧向量因 `model` 字段不符自动失效重建——这是 pycheat 上一轮踩过的 bug 修出来的机制，tkcore 直接复用。domain 隔离保证 note/log/gitx 的缓存互不污染。

---

## 3. 两种模式

| 模式 | 域 | 数据形态 | 核心调用 |
|---|---|---|---|
| **检索型** | note / log / gitx / clip / todo | 把文本切成 units，人话/语义召回 | `fused_rank(units, q, domain)` |
| **处理型** | explain / sum | 输入文本 → 本地 ollama 生成新文本 | `generate(prompt, system)` |

检索型回答「哪条相关」，处理型回答「帮我解释/总结这段」——同一套 ollama 底座，换了个出口。

---

## 4. 各域实现要点（适配器怎么写）

| 域 | 数据源 | 采集方式 | 存储 | 备注 |
|---|---|---|---|---|
| `note` | 快记 | 逐条 jsonl → unit(text+tags) | `~/.config/cheat/.tk_note.jsonl` | tags 当作 aliases 参与匹配 |
| `todo` | 任务 | 逐条 jsonl → unit(text+tags) | `.tk_todo.jsonl` | 过滤 `done`，`--done` 改写文件 |
| `clip` | 剪贴板历史 | 每次 `clip -r` 记录 `pbpaste` 结果 | `.tk_clip.jsonl` | 跨平台读剪贴板（mac/win/linux） |
| `log` | 日志文件 | 按空行切段落 → unit（截断 4000 字） | 不存，运行时扫描 | 目录递归 3 层 `*.log` |
| `gitx` | git 历史 | `git log --pretty=format:%H%x1f...%x1e` 切提交 | 不存，运行时读 | 用 RS(`\x1e`)/`\x1f` 分隔，抗 body 内空行 |
| `explain` | 命令/选项 | — | — | 调 chat 模型，需本机有生成模型 |
| `sum` | 长文本 | 从文件或 stdin 读 | — | 截断 12000 字喂模型 |

**id 唯一性**：note/todo/clip 的 `id` 用「秒级时间戳 + 6 位 uuid 后缀」，避免同秒多次 add 时 id 碰撞导致显示错乱（这是初版实测发现的 bug，已修）。

---

## 5. 与 pycheat 的关系

- `pycheat` 是这套范式最早的「命令域」实例：它把 `cheatsheet.md` 适配成卡片、用 `fused_rank` 排序。
- `tkcore` 是把 pycheat 已验证的引擎**抽出来的一般化版本**——把「卡片」换成「通用 unit」，把 `cheatsheet` 换成「任意采集函数」。
- 二者刻意不互相 import（pycheat 已稳定上线），保持独立；将来若想统一，`pycheat` 可视为 `tk` 的一个 `cmd` 域。

---

## 6. 已知局限与演进方向

1. **跨语言查询强依赖 ollama**：中文查纯英文日志，离线分必为 0，ollama 不可用就空。已加启动期提示。
2. **explain / sum 需 chat 模型**：本机只有嵌入模型（bge-m3/nomic 不能对话），需先 `ollama pull qwen2.5:0.5b`；代码会友好报错。
3. **clip 历史靠手动 `clip -r`**：macOS 无内建剪贴板历史，可后续接 `pbv` 或 shell 钩子自动记录。
4. **日志段落切分较粗**：按空行分段，复杂多行堆栈可再细化（如按时间戳/级别行分块）。
5. **向量缓存随卡/记录增长**：目前全量重算后整体写回，量大可改增量写。

---

## 7. 安装与速查

```bash
# 安装（软链到全局命令，参照 pycheat 的 ~/bin 做法）
ln -s ~/terminal-toolbox/tk ~/bin/tk
ln -s ~/terminal-toolbox/tkcore.py ~/bin/tkcore.py   # 或保证 tkcore.py 与 tk 同目录

# 常用
tk note -a "想法" -t 标签        # 记
tk note 关键词                   # 语义搜
tk todo -a "任务"                # 加任务
tk todo 文档                     # 按内容召回
tk log "连接被拒绝" -p app.log   # 日志语义捞针
tk gitx "ollama 语义" -r .       # git 提交语义搜
tk clip -r                       # 记录当前剪贴板
tk clip 关键词                   # 剪贴板历史语义搜
tk explain "tar -xzf"            # 命令翻人话（需 chat 模型）
cat long.log | tk sum -f -       # 长输出摘要（需 chat 模型）
```

**一句话总结**：`tk` 把「单一数据源 + 适配器 + 本地语义融合」做成了可复用的引擎，
加新工具 = 加一个适配器，而非从零写脚本——这正是「可复用、可迁移、单真源」工程审美的落地。
