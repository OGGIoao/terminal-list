@echo off
setlocal
rem terminal-toolbox — Windows 入口包装器（配合 install.ps1 的 PATH + 别名）
rem 用法：把本目录加入 PATH 后，直接敲 pycheat / c 即可。
rem 优先用 python，若 python 不在 PATH 则回退到 Windows Python Launcher(py)。
if not defined PYTHON (set "PYTHON=python")
where %PYTHON% >nul 2>nul
if errorlevel 1 set "PYTHON=py"
%PYTHON% "%~dp0pycheat.py" %*
endlocal
