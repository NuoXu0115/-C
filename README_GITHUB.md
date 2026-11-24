# 推送到 GitHub —— 三步搞定

仓库已在本地建好并提交完毕：**14 个提交**，每个 ≤ 339 MB，便于分阶段推送与断点重试。
你只需要在 GitHub 上确认仓库为空，然后在自己电脑的 PowerShell 里跑一条命令。

> 仓库已建：<https://github.com/NuoXu0115/-C>（当前为空，默认分支 `main`）
> 远程地址已配好：`origin = https://github.com/NuoXu0115/-C.git`

---

## 第 1 步：确认仓库是空的

打开 <https://github.com/NuoXu0115/-C>，如果看到的是 "Quick setup …" 页面，就说明是空仓库 ✅

> 若你后来在网页上加了 README/LICENSE，第一次推送会被拒绝（non-fast-forward）。
> 那时要么删掉仓库重建，要么在新仓库上执行一次 `git push --force origin main`。

## 第 2 步：在你自己的 PowerShell 里运行

```powershell
cd C:\Users\ASUS\Desktop\美赛数模3
pwsh -File .\push_to_github.ps1
```

（远程地址已配置，无需再传 `-RepoUrl`；如要换仓库可加 `-RepoUrl https://github.com/用户/仓库.git`）

脚本会：

1. 检查没有任何文件超过 100 MB（GitHub 硬限制）；
2. 设置弱网参数（HTTP/1.1、500 MB postBuffer、低速阈值 10 分钟）；
3. **逐提交推送**，每段失败自动重试 4 次（间隔递增）。

> 为什么分 14 段：总量 2.23 GB，一次性 push 极易被网络中断。分段后一次失败最多重传 ~340 MB，
> 而且已推成功的段在重跑时会被跳过——断了只管重跑同一条命令。

## 第 3 步：认证（第一次推送时）

会弹出凭据窗口，二选一：

**A. 浏览器登录（最省事）**
选 "Sign in with your browser"，登录后自动完成，之后不再询问。

**B. Personal Access Token（PAT）**
1. <https://github.com/settings/tokens> → *Generate new token (classic)*
2. 勾选 **`repo`**，有效期自定
3. 命令行提示 `Username` 填用户名，`Password` **粘贴 Token**（不是账号密码）

---

## 各段体积与预计耗时

| 段 | 内容 | 大小 |
|---|---|---|
| 1 | 仓库骨架（README / LICENSE / 脚本） | < 1 MB |
| 2 | 说明文档 + 机场元数据 + TSA + 质量检查 | 23 MB |
| 3 | METAR + GHCN + HURDAT2 + 站点映射 | 169 MB |
| 4 | NCEI LCD 2023–2024 | 329 MB |
| 5 | NCEI LCD 2025 | 109 MB |
| 6 | 航班级子集 2023 + 机场日度汇总 | 245 MB |
| 7–9 | 航班级子集 2024 / 2025 / 2026 | 247 / 248 / 190 MB |
| 10–13 | BTS 原始压缩包 2023 / 2024 / 2025 / 2026 | 324 / 338 / 339 / 259 MB |
| 14 | 推送脚本更新 | < 1 MB |

按 5 MB/s 上行约 **10–15 分钟**；2 MB/s 约 20 分钟；上行 1 MB/s 则需 40 分钟以上。
建议有线网络、关闭休眠。

---

## 网络不稳怎么办（国内访问 GitHub 常见）

症状：`Failed to connect to github.com port 443`、`Recv failure: Connection was reset`、`RPC failed`。

**① 先直接重跑脚本** —— 它会自动重试 4 次/段，多数抖动都能过。

**② 改用 SSH over 443（最有效）**
```powershell
# 1) 生成密钥（若已有则跳过）
ssh-keygen -t ed25519 -C "你的邮箱"
# 2) 把 ~/.ssh/id_ed25519.pub 内容贴到 https://github.com/settings/keys
# 3) 让 github.com 走 443 端口
notepad $HOME\.ssh\config
```
在 `config` 里写：
```
Host github.com
  HostName ssh.github.com
  Port 443
  User git
```
然后切换远程地址并重新推送：
```powershell
git remote set-url origin git@github.com:NuoXu0115/-C.git
ssh -T git@github.com          # 应显示 "Hi NuoXu0115!"
pwsh -File .\push_to_github.ps1
```

**③ 走本地代理**（如果你有 Clash / v2ray，端口按实际改）
```powershell
git config --global http.proxy http://127.0.0.1:7890
git config --global https.proxy http://127.0.0.1:7890
# 推送完成后可取消：
# git config --global --unset http.proxy
```

**④ 降低单段体积**
若连 ~340 MB 的段都推不动，可以把大段再拆小（每个提交只含几个月），改完重新提交即可。

---

## 常见问题

**Q: 中途断了怎么办？**
重跑同一条命令。已推送的段会显示 `Everything up-to-date` 并跳过。

**Q: 提示 `Repository not found` / 认证失败？**
Token 缺 `repo` 权限，或远程地址拼错。检查 `git remote -v`。

**Q: 页面显示 "This repository is over 1 GB"？**
正常。GitHub 建议阈值 1 GB、硬上限 5 GB；2.23 GB 在允许范围内，只是会有提示。

**Q: 想换成自己的作者信息？**（**推送前**做）
```powershell
git config user.name  "你的名字"
git config user.email "你的邮箱"
git rebase --root --exec "git commit --amend --no-edit --reset-author"
```

**Q: 以后数据更新？**
不要改写已推送历史，直接新增提交再 `git push`。

---

## 推送完成后

在仓库页 Settings 或 About 里补：

- **Description**：`U.S. flight reliability data package (BTS on-time 2023–2026 + NOAA weather) for 2027 MCM/ICM Problem C`
- **Topics**：`mcm` `mathematical-modeling` `aviation` `bts` `noaa` `open-data` `dataset`

> 更看重长期可引用性的话，可以把 `数据/` 再归档一份到 **Zenodo** 拿 DOI；GitHub 负责协作，Zenodo 负责引用。
