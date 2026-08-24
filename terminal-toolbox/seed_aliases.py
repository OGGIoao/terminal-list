#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""seed_aliases.py — 给 cheatsheet.md 的核心卡片批量补 `别名:` 字段。

只做一件事：在每张指定卡的 `## 名字` 下一行插入 `- 别名: ...`（若已存在则跳过）。
别名 = 人话说法 + 拼音 + 英文，目的是让 pycheat 的「按意图搜」能命中自然查询。

安全：先备份 cheatsheet.md 为 .bak.alias，再写回。
用法：python3 seed_aliases.py
"""
import os
import re
import shutil

PATH = os.path.expanduser("~/.config/cheat/cheatsheet.md")

# 卡名(必须与 cheatsheet 的 ## 标题完全一致) -> 别名(逗号分隔)
ALIASES = {
    "vm_stat": "看内存,内存占用,内存不够,内存压力,neicun,memory",
    "top / htop": "看进程,哪个程序最占cpu,最占内存的进程,进程监控,实时进程,process",
    "ps": "查进程,进程列表,看pid,进程快照,pid",
    "df": "看磁盘,磁盘空间,磁盘占用,剩多少空间,disk,cipan",
    "du": "文件夹大小,看目录占用,大文件,folder size",
    "iostat": "磁盘io,磁盘读写,disk io",
    "find": "找文件,搜索文件,按名找,find file",
    "kill": "杀进程,关掉程序,kill process",
    "uname": "看架构,芯片架构,系统架构,arch",
    "sysctl": "看cpu型号,cpu信息,cpu model",
    "ln": "建软链,软链接,symlink",
    "brew": "装软件,包管理,安装软件,install",
    "git status": "看改动,当前状态,改了啥,git状态",
    "git add / commit": "提交,保存改动,commit代码,交代码",
    "git branch / switch": "建分支,切换分支,branch",
    "git fetch / pull / push": "同步,推送到远程,拉取代码,push,pull",
    "git stash": "暂存改动,暂存,stash",
    "git diff": "看差异,对比改动,diff",
    "ls": "列文件,看目录内容,list",
    "launchctl": "管后台服务,开机启动,服务管理",
    "sw_vers": "看系统版本,系统版本,version",
    "ln -sf (实战软链·让 GUI 找到 CLI)": "让gui找到命令,gui找不到cli,软链cli",
}


def main():
    shutil.copy(PATH, PATH + ".bak.alias")
    lines = open(PATH, encoding="utf-8").read().split("\n")
    out = []
    added = []
    i = 0
    while i < len(lines):
        line = lines[i]
        out.append(line)
        m = re.match(r"^##\s+(.*)$", line)
        if m:
            name = m.group(1).strip()
            if name in ALIASES:
                has = any(re.match(r"^-\s*别名", l) for l in lines[i + 1:i + 8])
                if not has:
                    out.append("- 别名: " + ALIASES[name])
                added.append(name + ("(已存在跳过)" if has else ""))
        i += 1
    open(PATH, "w", encoding="utf-8").write("\n".join(out))
    print("已处理 %d 张卡：" % len(added))
    for a in added:
        print("  + " + a)
    missed = [k for k in ALIASES if k not in [a.split("(")[0] for a in added]]
    if missed:
        print("⚠️ 未匹配到的卡名（检查拼写）：" + ", ".join(missed))


if __name__ == "__main__":
    main()
