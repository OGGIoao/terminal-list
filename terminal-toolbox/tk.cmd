@echo off
setlocal
rem terminal-toolbox — Windows 入口包装器（配合 install.ps1 的 PATH + 别名）
rem 用法：把本目录加入 PATH 后，直接敲 tk 即可。
rem tk 在仓库内无 .py 后缀（供 macOS 软链），Windows 用 runpy 执行无后缀脚本，
rem 这样 macOS 与 Windows 共用同一份 tk 源码，不漂移。
if not defined PYTHON (set "PYTHON=python")
where %PYTHON% >nul 2>nul
if errorlevel 1 set "PYTHON=py"
%PYTHON% -c "import runpy; runpy.run_path(r'%~dp0tk', run_name='__main__')" %*
endlocal
