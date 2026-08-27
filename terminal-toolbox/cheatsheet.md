# 我的终端命令速查 (cheatsheet)

> 数据源: ~/WorkBuddy/2026-07-28-23-03-09/操作系统底层与终端精通课程.md
> 维护规则: 每学完一卷，就把该卷的精选命令抽成下方"卡片"。卡片字段固定为六行：
>   作用 / 用法 / 示例 / 踩坑 / Windows对照 / 来源卷
> 新增命令 = 在文末加一个 `## 命令名` 区块即可，`cheat` 函数会自动识别。
> 同步机制: 与 OS 课程文档双向引用——本文件是"即查即用"的精简版，文档是"讲透原理"的完整版。
> 最后更新: 2026-08-27（初建含 0.0 硬件/第一卷内核/第二卷文件系统/第三卷Shell+自检三连；git 实战 8 张卡；新增 ollama 指令 7 张卡：serve/pull/run/list/ps/rm/embeddings REST，供 pycheat --llm 语义检索）

---

## uname
- 别名: 看架构,芯片架构,系统架构,arch
- 作用: 查看内核与硬件架构信息（跨平台通用）
- 用法: uname [选项]
- 示例: `uname -m` → arm64（架构）; `uname -a` → 内核名+主机+版本+架构全信息
- 踩坑: 只报"架构代号"不报具体型号；要型号用 `sysctl`/`system_profiler`
- Windows对照: 无此命令，看系统用 `systeminfo` 或 `ver`（仅版本号）
- 来源卷: 0.0 硬件地基

## sysctl
- 别名: 看cpu型号,cpu信息,cpu model
- 作用: 读取 macOS/BSD 内核与硬件参数（macOS 独有）
- 用法: sysctl [-n] 键名
- 示例: `sysctl -n machdep.cpu.brand_string` → Apple M5 Pro; `sysctl hw.memsize` → 内存字节数
- 踩坑: 仅 macOS/BSD；Linux 读 `/proc`，Windows 用 `wmic cpu get`
- Windows对照: `wmic cpu get name` / PowerShell `Get-ComputerInfo`
- 来源卷: 0.0 硬件地基

## system_profiler
- 作用: 输出完整硬件/系统画像（macOS 独有，GUI"关于本机"的命令行版）
- 用法: system_profiler <数据类型>
- 示例: `system_profiler SPHardwareDataType` → 芯片/内存/序列号; `system_profiler SPSoftwareDataType` → 系统版本
- 踩坑: 不加参数会输出极长（所有数据类型）；指定类型才实用
- Windows对照: `msinfo32`（系统信息图形工具）
- 来源卷: 0.0 硬件地基

## vm_stat
- 别名: 看内存,内存占用,内存不够,内存压力,neicun,memory
- 作用: 实时看内存压力（页换入换出），对应 M 系列统一内存 UMA
- 用法: vm_stat [间隔秒]
- 示例: `vm_stat 2` → 每 2 秒刷新；关注 free/speculative 与 pageout 计数
- 踩坑: 单位是"页(4096字节)"不是 MB，要换算；高 pageout 说明内存吃紧
- Windows对照: 任务管理器"性能→内存" 或 `typeperf`
- 来源卷: 0.0 硬件地基 / 第一卷
- 常用: 是
## powermetrics
- 作用: 实时功耗/温度/各 CPU 核心负载（需 root）
- 用法: sudo powermetrics [--samplers 项] [-n 次数]
- 示例: `sudo powermetrics` → 滚屏输出（Ctrl+C 退出）; 看 CPU 各性能核/能效核占用
- 踩坑: 要 sudo 密码；输出持续刷新，用 `-n 1` 只看一次
- Windows对照: 无直接等价，靠 HWiNFO/ThrottleStop 等第三方
- 来源卷: 0.0 硬件地基

## iostat
- 别名: 磁盘io,磁盘读写,disk io
- 作用: 磁盘 IO 吞吐监控
- 用法: iostat [间隔] [次数]
- 示例: `iostat 2` → 每 2 秒看磁盘读写；看 disk0 的 KB/s 与响应时间
- 踩坑: 首次采样是"开机至今均值"，看第二次起才是实时
- Windows对照: 资源监视器→磁盘 或 `perfmon`
- 来源卷: 0.0 硬件地基

## top / htop
- 别名: 看进程,哪个程序最占cpu,最占内存的进程,进程监控,实时进程,process
- 作用: 实时进程监控（htop 是彩色增强版，需 brew 装）
- 用法: top -o cpu ; htop
- 示例: `top -o cpu` 按 CPU 排序; htop 里 F9 发信号、F4 过滤、F5 树状
- 踩坑: top 默认交互；htop 不在系统自带，要 `brew install htop`；F9 杀进程前确认 PID
- Windows对照: 任务管理器 / Process Explorer（Sysinternals）
- 来源卷: 第一卷 内核与进程
- 常用: 是
## ps
- 别名: 查进程,进程列表,看pid,进程快照,pid
- 作用: 列出进程快照（非实时），看 PID/父PID/命令
- 用法: ps aux ; ps -o pid,ppid,comm -p <PID>
- 示例: `ps aux | head` 看全部; `ps -p 1 -o comm=` → launchd（确认 PID 1 是谁）
- 踩坑: macOS 的 `ps aux` BSD 风格，与 Linux 略有差异；`ps -ef` 也通用
- Windows对照: `tasklist` / `Get-Process`
- 来源卷: 第一卷 内核与进程

## kill
- 别名: 杀进程,关掉程序,kill process
- 作用: 向进程"发信号"（不是直接杀死），默认 SIGTERM(15) 温和请求退出
- 用法: kill <PID> ; kill -9 <PID> ; kill -TERM <PID>
- 示例: `kill 1234` 优雅退出; `kill -9 1234` 强杀（SIGKILL，进程来不及清理）
- 踩坑: `-9` 是最后手段，会跳过清理导致数据丢失/僵尸；先试默认再 `-9`
- Windows对照: `taskkill /PID 1234` / `/F` 强制
- 来源卷: 第一卷 内核与进程

## launchctl
- 别名: 管后台服务,开机启动,服务管理
- 作用: 与 macOS 的 init(PID 1, launchd) 交互：启停/加载服务、设环境变量
- 用法: launchctl list ; launchctl load/unload <plist> ; launchctl setenv KEY val
- 示例: `launchctl list | grep -i agent` 看用户级服务; `launchctl getenv PATH` 看 GUI 的 PATH
- 踩坑: 改了 launchd 的环境变量要注销重登才生效；这是 GUI 应用 PATH 的来源（不读 .zshrc）
- Windows对照: `sc`(服务控制) / 任务计划程序
- 来源卷: 第一卷 / 第四卷(环境变量分裂)

## sw_vers
- 别名: 看系统版本,系统版本,version
- 作用: 查看 macOS 系统版本（macOS 独有）
- 用法: sw_vers
- 示例: `sw_vers` → ProductName/Version/Build 三行
- 踩坑: 仅 macOS；Linux 用 `/etc/os-release`，Windows 用 `ver`/`winver`
- Windows对照: `winver`
- 来源卷: 第一卷

## uptime
- 作用: 看系统运行时长与平均负载（load average）
- 用法: uptime
- 示例: `uptime` → 运行天数 + 3 个负载数（1/5/15 分钟）；M 系列看核心数换算
- 踩坑: 负载≠CPU%，是"就绪队列长度"；多核下负载=核数才算满载
- Windows对照: 任务管理器"性能" 或 `systeminfo | find "Time"`
- 来源卷: 第一卷

## ls
- 别名: 列文件,看目录内容,list
- 作用: 列出目录内容
- 用法: ls -la <路径> ; ls -l
- 示例: `ls -la /` 看根目录(含隐藏文件 `.`开头); `ls -la ~` 看家目录隐藏项
- 踩坑: 默认不显示隐藏文件(`.`开头)，必须 `-a`；macOS 的 `@` 表示有扩展属性
- Windows对照: `dir`；`dir /a` 看隐藏
- 来源卷: 第二卷 文件系统

## mount
- 作用: 查看已挂载的文件系统及其类型/选项
- 用法: mount ; mount | grep apfs
- 示例: `mount | head` → 看 `/` 是 apfs, sealed, read-only（系统盘密封只读=SIP 体现）
- 踩坑: macOS `/` 是只读密封的；可写数据在 `/System/Volumes/Data`
- Windows对照: `mountvol` / `wmic logicaldisk get`
- 来源卷: 第二卷

## stat
- 作用: 查看文件的 inode/权限/大小/链接数等元数据
- 用法: stat -f "格式串" <文件> (macOS BSD 风格)
- 示例: `stat -f "%N inode=%i size=%z links=%l" ~/.zshrc`
- 踩坑: macOS 用 `-f` + 格式串（BSD），Linux 用 `-c`（GNU），参数不通用
- Windows对照: 无命令行等价，靠属性对话框 / `fsutil`
- 来源卷: 第二卷 (inode 与数据分离)

## ln
- 别名: 建软链,软链接,symlink
- 作用: 创建链接——硬链接(默认) 或 软链接(`-s`)，把命令"放"进 PATH
- 用法: ln 源 目标(硬) ; ln -s 源 目标(软) ; ln -sf 源 目标(强制覆盖)
- 示例: `sudo ln -sf ~/.nvm/.../bin/node /usr/local/bin/` 让 GUI 找到 node
- 踩坑: 软链指向被删→断裂(红色)；硬链接共享 inode，删原文件数据还在；跨文件系统只能用软链
- Windows对照: `mklink`(需管理员)；"快捷方式"只是 .lnk 文件不是真链接
- 来源卷: 第二卷 / 实战软链

## df
- 别名: 看磁盘,磁盘空间,磁盘占用,剩多少空间,disk,cipan
- 作用: 查看磁盘各挂载点已用/可用空间
- 用法: df -h
- 示例: `df -h` → 人类可读(GB)；看 `/System/Volumes/Data` 才是你真正能写的盘
- 踩坑: 要看"剩余可用"而非"已用"；APFS 有"可清除空间"概念
- Windows对照: `wmic logicaldisk get size,freespace`
- 来源卷: 第二卷
- 常用: 是
## du
- 别名: 文件夹大小,看目录占用,大文件,folder size
- 作用: 统计目录/文件占用大小（排查谁占空间）
- 用法: du -sh <路径> ; du -sh ~/.* 2>/dev/null | sort -h
- 示例: `du -sh ~/.*` → 看哪个隐藏目录异常大（安全巡检：藏匿/日志逃避）
- 踩坑: 不带 `-s` 会递归列出每个子项刷屏；`/` 根目录要 sudo 才全看得到
- Windows对照: 无原生递归命令，靠 TreeSize/WinDirStat
- 来源卷: 第二卷 (安全巡检)

## find
- 别名: 找文件,搜索文件,按名找,find file
- 作用: 按名称/类型/时间递归查找文件
- 用法: find <起点> -name "模式" ; find . -type f -mtime -1
- 示例: `find ~ -name "*.log" 2>/dev/null` 找所有日志; 安全巡检可疑隐藏脚本
- 踩坑: 默认递归很深，慢；配合 `2>/dev/null` 屏蔽无权限报错
- Windows对照: `dir /s /b` 或 PowerShell `Get-ChildItem -Recurse`
- 来源卷: 第二卷 / 第七卷
- 常用: 是
## xattr
- 作用: 查看/管理 macOS 扩展属性（@ 标记的来源），含 quarantine 隔离标记
- 用法: xattr -l <文件> ; xattr -d com.apple.quarantine <文件>
- 示例: `xattr -l ~/Downloads/foo.dmg` 看下载隔离标记（Gatekeeper 依据）
- 踩坑: 从网上下载的文件带 quarantine，首次打开弹"未知开发者"；删标记可绕过（谨慎）
- Windows对照: NTFS 备用数据流(ADS)，`dir /r`
- 来源卷: 第二卷 (隐藏与隔离)

## echo $PATH
- 作用: 查看当前 PATH（命令查找路径，冒号分隔，从左到右优先）
- 用法: echo $PATH | tr ':' '\n'  （分行更易读）
- 示例: 排错"command not found"先看 PATH 含不含命令所在目录
- 踩坑: 改了 ~/.zshrc 的 PATH 必须重开终端或 `source` 才生效
- Windows对照: `echo %PATH%`(CMD) / `$env:PATH`(PowerShell)
- 来源卷: 第三卷 / 自检三连

## export
- 作用: 把变量"导出"为环境变量（子进程可见）；仅写 `VAR=val` 不会传给子进程
- 用法: export VAR=值 ; export PATH="$PATH:/新目录"
- 示例: `export PATH="$HOME/bin:$PATH"` 把自定义目录插到最前（最高优先）
- 踩坑: 直接 `PATH=val` 会清空原有 PATH；追加必须 `="$PATH:..."`
- Windows对照: `setx`(持久) / `$env:VAR=...`(会话)
- 来源卷: 第三卷

## alias
- 作用: 给命令起短别名（仅当前 shell 会话，写入 .zshrc 才持久）
- 用法: alias ll='ls -la' ; alias  (列出全部)
- 示例: `alias gs='git status'` 省敲键盘
- 踩坑: 别名可被恶意覆盖冒充真命令（PATH 劫持同理）；`type 命令` 看它到底是别名/函数/文件
- Windows对照: `doskey`（CMD，不持久）/ PowerShell 函数
- 来源卷: 第三卷 / 安全(PATH劫持/alias钓鱼)

## type
- 作用: 揭示一个"命令名"到底是什么（别名/函数/内建/文件路径）
- 用法: type <名称> ; type -a <名称>
- 示例: `type ls` 看是否被 alias; `type claude` 看真实路径 → 排错利器
- 踩坑: 同名时优先级：alias > function > 内建 > PATH 文件；用它识破伪装
- Windows对照: `where`(CMD) / `Get-Command`(PowerShell)
- 来源卷: 第三卷 / 自检

## which
- 作用: 显示命令在 PATH 中的绝对路径（自检三连之一）
- 用法: which <命令> ; which -a <命令>
- 示例: `which node` → ~/.nvm/.../bin/node；"command not found"先跑它
- 踩坑: 不识别 alias/function（用 `type` 补）；只报 PATH 内能找到的
- Windows对照: `where`(CMD)
- 来源卷: 第三卷 / 自检三连

## source
- 作用: 在当前 shell 立即执行某文件（让改动的 .zshrc 生效，不开新终端）
- 用法: source ~/.zshrc ; . ~/.zshrc
- 示例: 改完配置后 `source ~/.zshrc` 即可刷新，不必重开
- 踩坑: 如果文件有语法错，source 会报错且可能中断当前环境；先 `zsh -n` 检查
- Windows对照: 无直接等价（CMD `call` 近似但不加载环境）
- 来源卷: 第三卷

## zsh -n
- 作用: 语法检查（dry-run，不执行），改 .zshrc 后必跑的"安全闸"
- 用法: zsh -n ~/.zshrc
- 示例: 编辑前后各跑一次，无输出=语法 OK（你曾因引号写错整文件失效）
- 踩坑: 只查语法不查逻辑；配合 `cp ~/.zshrc ~/.zshrc.bak` 双保险
- Windows对照: 无（PowerShell 有 `powershell -Command` 可部分校验）
- 来源卷: 第三卷 / 防御

## cat ~/.zshrc
- 作用: 查看 shell 配置文件内容（自检三连之一，定位配置写坏）
- 用法: cat ~/.zshrc
- 示例: "command not found"时看 nvm/PATH 段是否还在、有无乱码/缺引号
- 踩坑: 大文件用 `less` 翻页；改前先备份
- Windows对照: 环境变量在图形界面"系统属性"，无等价文本文件
- 来源卷: 第三卷 / 自检三连

## brew
- 别名: 装软件,包管理,安装软件,install
- 作用: Homebrew 包管理器（macOS 装命令行工具的"应用商店"）
- 用法: brew install <包> ; brew list ; brew --prefix
- 示例: `brew install htop fzf ripgrep` 批量装工具；`brew list` 看已装
- 踩坑: 装的是命令行工具不是 .app；GUI 程序用 `brew install --cask`
- Windows对照: `winget` / `scoop`
- 来源卷: 第六卷 / 实战
- 常用: 是
## npm (全局)
- 作用: Node 包管理；`npm install -g` 装全局命令（claude/codex 等）
- 用法: npm install -g <包> ; npm ls -g --depth=0 ; npm config get prefix
- 示例: 全局命令装在 nvm 的 node 版本目录里，需 nvm 加载才进 PATH
- 踩坑: install-scripts 策略可能拦截 postinstall（claude 原生二进制曾因此没装上）；切换 node 版本后全局命令需重装
- Windows对照: 全局目录固定，无 nvm 概念
- 来源卷: 第六卷 / 实战

## ln -sf (实战软链·让 GUI 找到 CLI)
- 别名: 让gui找到命令,gui找不到cli,软链cli
- 作用: 把 nvm 里的命令软链到 /usr/local/bin（GUI 应用默认 PATH），解决 WeSight 检测不到
- 用法: sudo ln -sf ~/.nvm/versions/node/v26.5.0/bin/{node,npm,npx,claude,codex} /usr/local/bin/
- 示例: 执行后 WeSight 重新打开即可检测到 codex/claude
- 踩坑: 需 sudo 密码；切换 node 版本后软链指向旧路径，要重跑并改版本号
- Windows对照: 不适用（Windows GUI 读全局环境变量）
- 来源卷: 实战(WeSight 坑) / 第四卷

---

## git status
- 别名: 看改动,当前状态,改了啥,git状态
- 作用: 看仓库当前状态——哪些文件改了、哪些是新增未跟踪（动手前先跑它，知道"我改了啥"）
- 用法: git status ; git status -s
- 示例: `git status` → 列出已修改(M)/未跟踪(??); `git status -s` → 紧凑两列，左边暂存态右边工作区
- 踩坑: 改完先 `status` 再提交，避免漏改；`status -s` 更省眼；中文文件名显示成 `\345\...` 时加 `git config --global core.quotepath false`
- Windows对照: 跨平台，Git Bash / PowerShell 同命令
- 来源卷: 第六卷·实战(git)
- 常用: 是
## git log
- 作用: 看提交历史（快照时间线），确认"发生过什么、谁改的"
- 用法: git log ; git log --oneline ; git log -p <文件>
- 示例: `git log --oneline -10` → 最近 10 条一行版; `git log -p README.md` → 某文件逐次改动; `git log --stat` → 每次改了哪些文件
- 踩坑: 默认满屏，用 `--oneline` 先看梗概；翻页用 空格，退出按 q；`git log --graph --oneline` 看分支拓扑
- Windows对照: 同
- 来源卷: 第六卷

## git add / commit
- 别名: 提交,保存改动,commit代码,交代码
- 作用: 把改动「暂存」再「提交」成一次历史记录（commit 才是真保存，只改不提交等于没存）
- 用法: git add <文件> ; git commit -m "说明"
- 示例: `git add .` 暂存全部改动; `git commit -m "fix: 修复导出空指针"` 提交; `git commit -am "x"` 已跟踪文件一步提交
- 踩坑: `add .` 会连敏感文件/大文件一起提交，先 `status` 确认范围；commit 忘了 `-m` 会进编辑器卡住；改了但没 add 的内容不会进提交
- Windows对照: 同
- 来源卷: 第六卷·实战

## git branch / switch
- 别名: 建分支,切换分支,branch
- 作用: 看/建/切换分支（并行改东西互相不干扰，主线与实验分开）
- 用法: git branch ; git switch -c <新分支> ; git switch <分支>
- 示例: `git branch` 列出分支(* 当前); `git switch -c feat-x` 新建并切换; `git switch main` 回主线
- 踩坑: 切换前先 commit 或 stash，否则未提交改动会被带过去; 删分支 `git branch -d` 需已合并; 远程分支用 `git switch -c 本地名 origin/远程名`
- Windows对照: 同
- 来源卷: 第六卷

## git fetch / pull / push
- 别名: 同步,推送到远程,拉取代码,push,pull
- 作用: 与远程仓库同步——拉更新（pull）或推提交（push）
- 用法: git fetch ; git pull ; git push
- 示例: `git push` 推当前分支; `  git pull` 拉并合并; `git fetch` 只看远程有啥不自动合；`git push -u origin 分支` 首次推新分支建立跟踪
- 踩坑: push 前先 pull 防冲突; pull 冲突要手动解决再 commit; 冲突时别慌，git 会标 `<<<<<<<` 让你手动取舍
- Windows对照: 同
- 来源卷: 第六卷·实战

## git stash
- 别名: 暂存改动,暂存,stash
- 作用: 把当前未提交改动「暂存」到一边，腾空工作区（紧急切分支/拉代码时救场）
- 用法: git stash ; git stash pop ; git stash list
- 示例: `git stash` 收起改动; `git stash pop` 恢复; `git stash list` 看所有暂存; `git stash -u` 连未跟踪文件一起收
- 踩坑: 默认不收未跟踪文件（要 `-u`）；pop 冲突需手动解决；长期暂存用 `git stash save "备注"` 方便辨认
- Windows对照: 同
- 来源卷: 第六卷

## git diff
- 别名: 看差异,对比改动,diff
- 作用: 看具体改了什么（diff = 差异，比读日志直观得多）
- 用法: git diff ; git diff --staged ; git diff <版本1> <版本2>
- 示例: `git diff` 看未暂存改动; `git diff --cached` 看已暂存待提交; `git diff HEAD~1` 与上一版对比
- 踩坑: diff 默认不显示已 `add` 的，要看已暂存用 `--staged`；大文件刷屏用 `--stat` 只看增删行数
- Windows对照: 同
- 来源卷: 第六卷

## git remote / clone
- 作用: 远程仓库地址管理 / 首次把整库拉到本地
- 用法: git remote -v ; git clone <url>
- 示例: `git remote -v` 看当前远程地址; `git clone https://github.com/x/y.git` 克隆; `git remote set-url origin <新url>` 改地址
- 踩坑: clone 默认建子目录；改远程用 `set-url` 别改 `.git/config` 手滑; SSH 需配密钥，HTTPS 每次输账号（可用 credential 缓存）
- Windows对照: 同
- 来源卷: 第六卷

## git 别名 (oh-my-zsh 风格)
- 作用: 给 git 子命令起短别名，少敲键盘（g=git / gs=status / gl=log / gp=push / gpl=pull）
- 用法: 写在 ~/.zshrc，或启用 oh-my-zsh 自带 git 插件（已含一套预设别名）
- 示例: `alias g='git'` ; `alias gs='git status'` ; `alias gl='git log --oneline'` ; `alias gp='git push'` ; `alias gpl='git pull'` ; `alias gd='git diff'`
- 踩坑: 别名可能覆盖同名命令，用 `type g` 看是否被占用；oh-my-zsh git 插件已定义 g/gs/gd 等，自己再定义会冲突，建议只补插件没有的；一键同步脚本 `gup` 见《个人终端工具箱》工具 #3
- Windows对照: PowerShell 用 function 或 doskey
- 来源卷: 第三卷(alias) / 第六卷(git)

---

## ollama serve
- 别名: 启动ollama,开ollama服务,ollama后台,起服务
- 作用: 启动 ollama 本地服务（默认监听 11434 端口），供 pycheat --llm 等本机程序调用
- 用法: `ollama serve` （后台常驻；macOS 也可用 `brew services start ollama` 开机自启）
- 示例: `ollama serve &`  → 后台启动；`curl -s http://localhost:11434/api/tags` 验证在跑
- 踩坑: 端口 11434 被占会起不来；`api/tags` 返回空 `{"models":[]}` 说明服务在跑但还没拉模型
- Windows对照: 同 `ollama serve`；或设为系统服务
- 来源卷: 工具箱·ollama

## ollama pull
- 别名: 下载模型,拉模型,装模型,获取模型
- 作用: 从模型库拉取模型到本机（首次使用某模型必须这一步）
- 用法: `ollama pull <模型名>`
- 示例: `ollama pull nomic-embed-text`  → 向量化模型，pycheat 语义检索依赖它
- 示例: `ollama pull qwen2.5:0.5b`       → 轻量聊天模型，练手用
- 踩坑: 模型名带标签，如 `qwen2.5:0.5b`；只写 `qwen2.5` 会拉默认标签 latest；向量模型别乱删，pycheat 靠它
- Windows对照: 同
- 来源卷: 工具箱·ollama

## ollama run
- 别名: 跑模型,聊天,和模型对话,开聊
- 作用: 进入模型对话（没有会自动先 pull）
- 用法: `ollama run <模型名>`
- 示例: `ollama run qwen2.5:0.5b`  → 进对话筐，输入 `/bye` 退出
- 踩坑: 首次 run 会先下载，可能等一会儿；多轮对话占内存，0.5b 很轻，7b 以上注意 RAM
- Windows对照: 同
- 来源卷: 工具箱·ollama

## ollama list
- 别名: 看有哪些模型,模型列表,已装模型
- 作用: 列出本机已拉取的模型
- 用法: `ollama list`
- 示例: `ollama list`  → 看 NAME / ID / SIZE / MODIFIED
- 踩坑: 列表为空不代表服务没起，只是还没 pull 任何模型
- Windows对照: 同
- 来源卷: 工具箱·ollama

## ollama ps
- 别名: 看运行中的模型,模型进程,谁在跑
- 作用: 查看正在运行的模型进程（占多少内存）
- 用法: `ollama ps`
- 示例: `ollama ps`  → 看已加载模型的显存/内存占用
- 踩坑: 模型加载后常驻，不用时 `ollama stop <名>` 释放资源
- Windows对照: 同
- 来源卷: 工具箱·ollama

## ollama rm
- 别名: 删模型,卸载模型,移除模型
- 作用: 删除本机模型，释放磁盘
- 用法: `ollama rm <模型名>`
- 示例: `ollama rm qwen2.5:0.5b`
- 踩坑: 删除后下次 run 会重新下载（再等一次）；`nomic-embed-text` 是 pycheat 语义检索底座，别乱删
- Windows对照: 同
- 来源卷: 工具箱·ollama

## ollama embeddings (REST)
- 别名: 向量化接口,embedding调用,语义向量,文本转向量
- 作用: 用任意程序调 ollama 做文本向量化（pycheat --llm 就是这么干的）
- 用法: POST http://localhost:11434/api/embeddings   body: {"model":...,"prompt":...}
- 示例: `curl -s -X POST http://localhost:11434/api/embeddings -H "Content-Type: application/json" -d '{"model":"nomic-embed-text","prompt":"要向量化的文本"}'`
- 踩坑: 返回 JSON 里的 `embedding` 字段是浮点数组（nomic-embed-text 为 768 维）；需先 `ollama pull nomic-embed-text`
- Windows对照: 同（URL 不变，仍是本机 11434）
- 来源卷: 工具箱·ollama
