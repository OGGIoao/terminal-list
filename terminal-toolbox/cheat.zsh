# ============================================================
#  cheat —— 我的终端命令速查插件（增强版·即查即用）
#  数据源: ~/.config/cheat/cheatsheet.md
#  用法:
#    cheat                进入交互浏览（底部菜单：n/→ 下一张 · p/← 上一张 · b 回退 · f 前进 · c 复制示例 · / 搜索 · q 退出）
#    cheat <名字>         按名字精确浏览该卡（支持中途按菜单键继续翻）
#    cheat <关键词>       按内容搜索后再浏览（作用/用法/示例/踩坑，支持中文）
#    cheat -c <名字>      把示例命令复制到剪贴板（⌘V 直接跑）
#    cheat -l             列出全部命令名
#  维护: 每学完一卷，往 cheatsheet.md 末尾加 `## 命令名` 区块即可
#  升级路径: 阶段2 转 Python CLI 接 LLM 语义查询 → 阶段3 做 AI Skill
# ============================================================

CHEAT_SHEET="$HOME/.config/cheat/cheatsheet.md"

# 打印某命令名的完整卡片
_cheat_block() {
  awk -v s="$1" 'BEGIN{f=0} /^## /{f=($0=="## "s)} f{print}' "$CHEAT_SHEET"
}

# 按关键词搜：命令名含关键词「或」卡片内容含关键词，都算命中
# （你记不全名字也没关系：cheat sys 能命中 sysctl；cheat 内存 能命中 vm_stat）
_cheat_kw_names() {
  local kw="$1"
  awk -v k="$kw" '
    /^## /{
      if(inblock && hit) print name
      inblock=1; name=substr($0,4); hit=0
      if (name ~ k) hit=1          # 命令名本身含关键词
      next
    }
    { if(inblock && $0 ~ k) hit=1 } # 卡片内容含关键词
    END{ if(inblock && hit) print name }
  ' "$CHEAT_SHEET"
}

# 取某卡的「示例」行里反引号包裹的命令（用于 -c 复制）
_cheat_examples() {
  awk -v s="$1" '
    BEGIN { f = 0 }
    /^## / { f = ($0 == "## " s) }
    f && /^- 示例:/ {
      line = $0
      while (match(line, /`[^`]+`/)) {
        print substr(line, RSTART+1, RLENGTH-2)
        line = substr(line, RSTART+RLENGTH)
      }
    }
  ' "$CHEAT_SHEET"
}

# 复制文本到剪贴板（macOS / Linux 自适应）
_cheat_copy() {
  if command -v pbcopy >/dev/null 2>&1; then
    print -n "$1" | pbcopy
  elif command -v xclip >/dev/null 2>&1; then
    print -n "$1" | xclip -selection clipboard
  elif command -v wl-copy >/dev/null 2>&1; then
    print -n "$1" | wl-copy
  else
    echo "（无剪贴板工具，仅打印）" >&2
    echo "$1"
    return
  fi
  echo "✅ 已复制到剪贴板，直接 ⌘V 粘贴运行：" >&2
  echo "$1"
}

# 取全部命令名（每行一个）
_cheat_all_names() {
  grep -E '^## ' "$CHEAT_SHEET" | sed 's|^## ||'
}

# 读一个按键（兼容方向键）；结果写到 REPLY
_cheat_getkey() {
  local k
  read -rs -k1 k
  if [[ "$k" == $'\033' ]]; then
    read -rs -k1 -t 0.01 k2 2>/dev/null
    read -rs -k1 -t 0.01 k3 2>/dev/null
    case "$k2$k3" in
      '[C') k='right' ;;
      '[D') k='left' ;;
      '[A') k='up' ;;
      '[B') k='down' ;;
    esac
  fi
  REPLY="$k"
}

# ============ 交互浏览模式（底部菜单 + 回退/前进） ============
# 用法：
#   cheat            浏览全部卡片
#   cheat <关键词>  先按关键词过滤，再从第一张开始浏览
# 菜单：n/→ 下一张  p/← 上一张  b 回退  f 前进  c 复制示例  / 搜索  q 退出
_cheat_browse() {
  local kw="$1"
  local -a names
  local raw
  if [[ -n "$kw" ]]; then
    raw=$(_cheat_kw_names "$kw")
    names=(${(f)raw})
    if (( ${#names[@]} == 0 )); then
      echo "cheat: 没找到和 '$kw' 相关的命令卡。" >&2
      echo "       试试 cheat -l 看全部，或换个关键词。" >&2
      return 1
    fi
  else
    raw=$(_cheat_all_names)
    names=(${(f)raw})
  fi
  local n=${#names[@]}
  local i=1
  local -a hist=(); local h=0
  _cheat_push() {
    if (( h == 0 )) || [[ "${hist[$h]}" != "$i" ]]; then
      hist+=("$i"); h=${#hist[@]}
    fi
  }

  while true; do
    _cheat_push
    local name="${names[$i]}"
    clear
    printf '\033[1;36m┌─[ %s/%s ] %s ────────────────────────────────\033[0m\n' "$i" "$n" "$name"
    printf '\033[2m(来源 cheatsheet.md · 随时按菜单键)\033[0m\n\n'
    _cheat_block "$name"
    printf '\n'
    printf '\033[7m n/→下一张  p/←上一张  b回退  f前进  c复制示例  /搜索  q退出 \033[0m\n'

    # 非交互式 shell（脚本/cron/沙箱）：只展示当前卡，避免卡在等待按键
    if [[ ! -o interactive ]]; then
      echo "（当前为非交互 shell，已直接展示此卡；在真实终端里运行可获得底部菜单）"
      break
    fi

    _cheat_getkey
    local key="$REPLY"
    case "$key" in
      $'\n'|n|j|right|down) (( i < n )) && (( i++ )) ;;
      p|k|left|up)          (( i > 1 )) && (( i-- )) ;;
      b) (( h > 1 )) && { (( h-- )); i=${hist[$h]} } ;;
      f) (( h < ${#hist[@]} )) && { (( h++ )); i=${hist[$h]} } ;;
      c)
        local ex; ex=$(_cheat_examples "$name")
        _cheat_copy "$ex"
        read -rs -k1 -t 1.2 && true   # 让「已复制」提示停留约 1 秒再刷新
        ;;
      '/')
        printf '\n\033[36m搜索: \033[0m'
        local kw2; read -r kw2
        raw=$(_cheat_kw_names "$kw2")
        names=(${(f)raw})
        n=${#names[@]}
        (( n == 0 )) && { echo "无匹配，保持原列表"; raw=$(_cheat_all_names); names=(${(f)raw}); n=${#names[@]} }
        i=1; h=0; continue
        ;;
      q|Q) break ;;
      *) ;;
    esac
  done
}

cheat() {
  # 数据源不存在则提示
  if [[ ! -f "$CHEAT_SHEET" ]]; then
    echo "cheatsheet 不存在: $CHEAT_SHEET" >&2
    return 1
  fi

  # -l / --list 列出全部命令名
  if [[ "${1:-}" == "-l" || "${1:-}" == "--list" ]]; then
    grep -E '^## ' "$CHEAT_SHEET" | sed 's|^## ||' | column
    return
  fi

  # -c / --copy 复制示例到剪贴板
  if [[ "${1:-}" == "-c" || "${1:-}" == "--copy" ]]; then
    local ex; ex=$(_cheat_examples "$2")
    if [[ -z "$ex" ]]; then
      echo "未找到 '$2' 的示例命令（可能该卡没有「示例:」行）。" >&2
      return 1
    fi
    _cheat_copy "$ex"
    return
  fi

  # 无参数 / 有参数：进入交互浏览模式（底部菜单 + 回退/前进）
  #   无参数 → 浏览全部；有参数 → 先按关键词过滤，再从第一张开始浏览
  local q="${1:-}"
  _cheat_browse "$q"
}

# 敲错命令时，主动提示 cheat 里相关的卡（zsh 特殊函数）
command_not_found_handler() {
  local tried="$1"
  [[ ${#tried} -lt 2 ]] && return 1
  # 1) 命令名里包含 tried（模糊）
  local names; names=$(grep -E '^## ' "$CHEAT_SHEET" | sed 's|^## ||' | grep -iF "$tried")
  # 2) 或卡片内容含 tried
  if [[ -z "$names" ]]; then
    names=$(_cheat_kw_names "$tried")
  fi
  if [[ -n "$names" ]]; then
    echo "💡 没找到命令 '$tried'，但 cheat 里有相关的：" >&2
    echo "$names" | tr '\n' ' ' >&2; echo "" >&2
    echo "   输入 cheat <名字> 看详情（直接 cheat 回车可模糊选）" >&2
  fi
  return 1
}

# 快捷别名：c 调用 cheat（少敲几个字）
alias c='cheat'
