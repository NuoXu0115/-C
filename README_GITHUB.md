# 推送到 GitHub —— 三步搞定

仓库已经在本地建好并提交完毕（分 6 个提交，便于分阶段推送）。
你只需要在 GitHub 上建一个空仓库，然后运行一条命令。

---

## 第 1 步：在 GitHub 建一个**空**仓库

打开 <https://github.com/new>：

| 选项 | 选什么 |
|---|---|
| Repository name | 例如 `mcm-2027c-flight-reliability-data` |
| Visibility | **Public**（你之前选的） |
| Initialize this repository with | **全部不勾** —— 不要 README、不要 .gitignore、不要 license |

> ⚠️ 必须留空。若 GitHub 上已有初始提交，第一次推送会被拒绝（non-fast-forward）。

建好后复制仓库地址，形如：
`https://github.com/<你的用户名>/mcm-2027c-flight-reliability-data.git`

## 第 2 步：运行推送脚本

在项目根目录（`美赛数模3`）打开 PowerShell：

```powershell
pwsh -File .\push_to_github.ps1 -RepoUrl https://github.com/<你的用户名>/<仓库名>.git
```

脚本会：

1. 检查没有任何文件超过 100 MB（GitHub 硬限制）；
2. 设置 `origin` 远程地址；
3. **按提交逐个推送**，而不是一次性推 2.75 GB。

> 为什么逐个推：总量约 2.75 GB，一次性 push 容易被网络或 GitHub 中断；
> 逐个提交推只传输新增对象，断了重跑脚本即可从断点继续（已推的会显示 up-to-date）。

## 第 3 步：认证

脚本运行到第一次 push 时会要求凭据，两种方式任选：

**A. 浏览器登录（最省事）**
Windows 的 Git Credential Manager 会弹窗，选 "Sign in with your browser"，登录后自动完成。

**B. 用 Personal Access Token（PAT）**
1. 打开 <https://github.com/settings/tokens> → *Generate new token (classic)*
2. 勾选 **`repo`** 权限，有效期自定（建议 30 天）
3. 复制生成的 `ghp_...`
4. 在命令行提示 `Username` 处填你的 GitHub 用户名，`Password` 处**粘贴 Token**（不是账号密码）

> 不要把 Token 写进对话或脚本里。若不小心泄漏，立刻在设置页撤销。

---

## 预计耗时

| 阶段 | 内容 | 大小 |
|---|---|---|
| 1 | 仓库骨架（README / LICENSE / 脚本） | < 1 MB |
| 2 | 说明文档 + 机场元数据 + TSA + 质量检查 | ~25 MB |
| 3 | 气象数据（METAR / LCD / GHCN / HURDAT2） | ~607 MB |
| 4 | 整理后的航班级与机场日度数据 | ~879 MB |
| 5 | BTS 原始月度压缩包（45 个） | ~1.31 GB |

按 5 MB/s 上行带宽估算，全程约 **10–15 分钟**；上行慢的话可能到 40 分钟以上。
建议用有线网络，中途别让电脑休眠。

---

## 常见问题

**Q: 推送中途断了怎么办？**
直接重跑同一条命令。已推送的提交会被跳过（`Everything up-to-date`），从断点继续。

**Q: 提示 `remote contains work that you do not have locally`？**
说明第 1 步没建成空仓库（GitHub 帮你生成了 README）。删掉那个仓库重建，或先执行：
```powershell
git fetch origin
git push --force origin main
```
（仅在确认那个仓库里没有你要保留的内容时才用 `--force`。）

**Q: 提示 `Repository not found` / 认证失败？**
Token 没有 `repo` 权限，或仓库地址拼错。重新生成 Token 并确认 URL 精确匹配。

**Q: GitHub 页面上显示 "This repository is over 1 GB" 警告？**
正常。GitHub 的建议阈值是 1 GB、硬上限 5 GB；2.75 GB 在允许范围内，只是页面会有提示。

**Q: 想换成我自己的作者信息？**（在**推送之前**做）
```powershell
git config user.name  "你的名字"
git config user.email "你的邮箱"
git rebase --root --exec "git commit --amend --no-edit --reset-author"
```
推送之后再改就需要 force-push 了。

**Q: 以后数据有更新怎么办？**
不要改写已推送的历史，直接在本地新增提交后再 `git push` 即可。

---

## 推送完成后建议补充

在仓库页面点 ⚙️ Settings 或直接编辑 About：

- **Description**：`U.S. flight reliability data package (BTS on-time 2023–2026 + NOAA weather) for 2027 MCM/ICM Problem C`
- **Topics**：`mcm` `mathematical-modeling` `aviation` `bts` `noaa` `open-data` `dataset`
- **Website**：可留空

另外，`README.md` 里的引用块有 `<your-account>/<repo>` 占位符，记得替换成真实地址。
