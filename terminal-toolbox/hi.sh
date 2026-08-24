#!/usr/bin/env bash
# hi —— 一句话看到「我是谁 / 我在哪台机器 / 系统什么版本」
# 层级: 独立 .sh 脚本 + 软链全局命令（成长路线 第3/4级 演示）
# 关联 OS 课: 0.0 硬件地基（uname / sysctl 观测）、第三卷 Shell（变量 / 命令替换 / 测试）
# 维护: 想加新信息，就在下方对应区块追加即可；逻辑都抽在这一个文件里。
set -euo pipefail

# ── 基本信息（命令替换 + || 兜底，避免某条命令缺失就整体崩）──
me="${USER:-$(whoami)}"
host="$(hostname -s 2>/dev/null || echo unknown)"
os="$(sw_vers -productName 2>/dev/null || uname -s) $(sw_vers -productVersion 2>/dev/null || echo '?')"
arch="$(uname -m)"
up="$(uptime | sed 's/^ *//')"

echo "👋  hi, $me @ $host"
echo "🖥   $os  ($arch)"
echo "⏱   $up"

# ── 加 -v / --verbose 看芯片型号（macOS 专属观测，回指 0.0 硬件地基）──
if [[ "${1:-}" == "-v" || "${1:-}" == "--verbose" ]]; then
  chip="$(sysctl -n machdep.cpu.brand_string 2>/dev/null || echo '未知芯片')"
  mem_bytes="$(sysctl -n hw.memsize 2>/dev/null || echo 0)"
  mem_gb=$(( mem_bytes / 1024 / 1024 / 1024 ))
  echo "🔩  $chip  ·  ${mem_gb}GB 统一内存"
fi
