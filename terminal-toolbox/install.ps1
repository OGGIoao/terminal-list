# install.ps1 — terminal-toolbox Windows 一键安装
# 用法（任选其一）：
#   1) 资源管理器里右键本文件 →「使用 PowerShell 运行」
#   2) 在 PowerShell 中：cd 到本目录后执行  .\install.ps1
# 作用：
#   1) 检查 Python（语义检索可选检查 ollama）
#   2) 把工具箱目录加入「用户 PATH」（持久化，重启终端生效）
#   3) 在 PowerShell $PROFILE 写入别名 c / pycheat / tk
# 全程不修改系统盘以外的任何文件，可重复运行（幂等）。

$ErrorActionPreference = "Stop"
$TB = $PSScriptRoot  # 本脚本所在目录，即工具箱根

Write-Host "== terminal-toolbox Windows 安装 ==" -ForegroundColor Cyan

# ---------- 1) 检查 Python ----------
$py = Get-Command python -ErrorAction SilentlyContinue
if (-not $py) { $py = Get-Command py -ErrorAction SilentlyContinue }
if (-not $py) {
    Write-Host "❌ 未检测到 Python。" -ForegroundColor Red
    Write-Host "   请先安装 Python 3.9+，并务必勾选安装界面的 'Add python.exe to PATH'。" -ForegroundColor Yellow
    Write-Host "   下载：https://www.python.org/downloads/" -ForegroundColor Yellow
    Write-Host "   装好重新运行本脚本即可。" -ForegroundColor Yellow
    pause
    exit 1
}
Write-Host "✅ Python: $($py.Source)" -ForegroundColor Green

# ---------- 2) 可选检查 ollama（语义检索用）----------
$ol = Get-Command ollama -ErrorAction SilentlyContinue
if ($ol) {
    Write-Host "✅ ollama 已安装（语义检索可用；首次用会提示拉取 bge-m3/nomic-embed-text）" -ForegroundColor Green
} else {
    Write-Host "⚠️ 未检测到 ollama（可选）。装了才能用本地语义检索：" -ForegroundColor Yellow
    Write-Host "   下载：https://ollama.com/download" -ForegroundColor Yellow
}

# ---------- 3) 加入用户 PATH（持久化）----------
$userPath = [Environment]::GetEnvironmentVariable("Path", "User")
if ($userPath -notlike "*$TB*") {
    if ([string]::IsNullOrEmpty($userPath)) { $newPath = $TB }
    else { $newPath = $userPath.TrimEnd(';') + ";" + $TB }
    [Environment]::SetEnvironmentVariable("Path", $newPath, "User")
    Write-Host "✅ 已将工具箱目录加入用户 PATH：`n   $TB" -ForegroundColor Green
} else {
    Write-Host "✅ 工具箱目录已在用户 PATH 中" -ForegroundColor Green
}

# ---------- 4) 写 PowerShell 别名（幂等，不重复）----------
$marker = "# terminal-toolbox aliases"
$aliasBlock = @"

$marker
function c { python "$TB\pycheat.py" @args }
function pycheat { python "$TB\pycheat.py" @args }
function tk { python -c "import runpy; runpy.run_path(r'$TB\tk', run_name='__main__')" @args }
"@
if (-not (Test-Path $PROFILE)) {
    New-Item -ItemType File -Path $PROFILE -Force | Out-Null
}
$existing = Get-Content $PROFILE -Raw -ErrorAction SilentlyContinue
if ($existing -notmatch [regex]::Escape($marker)) {
    Add-Content -Path $PROFILE -Value $aliasBlock
    Write-Host "✅ 已在 $PROFILE 写入别名 c / pycheat / tk" -ForegroundColor Green
} else {
    Write-Host "✅ $PROFILE 已含 terminal-toolbox 别名（未重复写入）" -ForegroundColor Green
}

Write-Host ""
Write-Host "🎉 安装完成！请「重新打开 PowerShell」使 PATH 与别名生效，然后试试：" -ForegroundColor Cyan
Write-Host "   c              # 进开场屏（推荐 / 复习 / 语义提示）" -ForegroundColor White
Write-Host "   c 查端口占用    # 人话搜命令" -ForegroundColor White
Write-Host "   c -c 关键词     # 复制示例到剪贴板" -ForegroundColor White
Write-Host "   tk note 记一笔  # 终端快记本" -ForegroundColor White
Write-Host ""
Write-Host "数据同步：把 C:\Users\你\.config\cheat\cheatsheet.md 放进 OneDrive/iCloud 并双向同步，" -ForegroundColor DarkGray
Write-Host "即可让 Windows 与 macOS 共享同一份命令卡（详见跨平台使用指南.md）。" -ForegroundColor DarkGray
pause
