#!/usr/bin/env bash
# gup —— 一键把「当前 git 仓库」的改动提交并推送到远端
# 层级: 独立 .sh 脚本 + 软链全局命令（成长路线 第3/4级，git 实战版）
# 关联 OS 课: 第三卷 Shell（变量/命令替换/退出码）、第六卷 git 实战
#
# 安全设计（呼应《个人终端工具箱》§7 红线）：
#   1. 只在「当前 git 仓库内」操作，绝不递归删、绝不碰工作区外的文件
#   2. 不删除任何东西（无 rm / 无 reset --hard）
#   3. 提交前先 pull（--ff-only 仅快进），冲突就停下来让人处理，绝不强制覆盖
#   4. 无改动则什么都不做直接退出
#   5. 既不涉及 ~/.workbuddy/workbuddy.db（自动化数据），也不做任何破坏性操作
set -euo pipefail

# —— 必须先 cd 到 git 仓库内 ——
if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  echo "❌ 当前目录不是 git 仓库。请先「cd 到你要同步的仓库根目录」再跑 gup。" >&2
  exit 1
fi
root="$(git rev-parse --show-toplevel)"
cd "$root" || exit 1

branch="$(git symbolic-ref --short HEAD 2>/dev/null || echo main)"
echo "📁 仓库: $root  (分支: $branch)"

# —— 无改动则直接退出（不做任何写操作）——
if [ -z "$(git status --porcelain)" ]; then
  echo "✅ 没有改动，无需提交。"
  if git remote | grep -q .; then
    git fetch --quiet 2>/dev/null || true
  fi
  exit 0
fi

# —— 展示将要提交的范围，让人心里有数 ——
echo "📦 将提交以下改动（M 改 / A 加 / D 删 / ?? 未跟踪）："
git status --short

# —— 先拉远端（仅快进，避免覆盖你的本地历史）——
if git remote | grep -q .; then
  echo "⬇️  先 git pull（--ff-only）..."
  if ! git pull --ff-only; then
    echo "⚠️  pull 失败或产生冲突。请手动「git pull」解决后再跑 gup。" >&2
    exit 1
  fi
fi

# —— 暂存并提交（只针对本仓库内改动；敏感目录请用 .gitignore 排除）——
git add -A
msg="auto: 同步于 $(date '+%Y-%m-%d %H:%M')"
git commit -m "$msg" >/dev/null
echo "✅ 已提交: $msg"

# —— 推送（没有 upstream 就给命令，而不是直接报错）——
if git remote | grep -q .; then
  if git rev-parse --abbrev-ref --symbolic-full-name '@{u}' >/dev/null 2>&1; then
    if git push; then
      echo "⬆️  已推送。"
    else
      echo "⚠️  push 失败（可能被拒绝）。先手动「git pull」合并后再 gup。" >&2
      exit 1
    fi
  else
    echo "ℹ️  当前分支 '$branch' 没有 upstream，未自动推送。"
    echo "    首次推送请手动：git push -u origin $branch"
  fi
else
  echo "ℹ️  没有配置 remote，仅完成本地提交（要同步到远端先：git remote add origin <url>）。"
fi

echo "✅ 完成。"
