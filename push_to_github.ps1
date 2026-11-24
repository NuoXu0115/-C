<#
Push this repository to GitHub using STAGED pushes.

Why staged: the repo carries ~2.75 GB of data. A single `git push` of that size
is slow and can be cut off by GitHub / the network. Pushing one commit at a time
transfers only the new objects in each step, so a dropped connection only costs
one stage (just re-run the script - it resumes from the last successful stage
because already-pushed commits are up to date).

Usage
-----
  pwsh -File push_to_github.ps1 -RepoUrl https://github.com/<user>/<repo>.git

  # or with an explicit token (avoid: token lands in your shell history)
  pwsh -File push_to_github.ps1 -RepoUrl https://<token>@github.com/<user>/<repo>.git

Prerequisite: create the repository on GitHub as an EMPTY repo
(no README, no .gitignore, no license), otherwise the first push is rejected.
#>

param(
    [string]$RepoUrl = "",
    [string]$Branch = "main"
)

$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $PSScriptRoot

if (-not (Test-Path ".git")) { throw "Not a git repository: $PSScriptRoot" }

Write-Host "=== guard: no single file may exceed 100 MB ===" -ForegroundColor Cyan
$big = Get-ChildItem -Recurse -File |
    Where-Object { $_.Length -gt 95MB -and $_.FullName -notlike "*\.git\*" }
if ($big) {
    $big | ForEach-Object { "  TOO BIG: $([math]::Round($_.Length/1MB,1)) MB  $($_.FullName)" }
    throw "GitHub rejects files over 100 MB. Aborting before any data is uploaded."
}
$total = (Get-ChildItem -Recurse -File | Where-Object { $_.FullName -notlike "*\.git\*" } |
          Measure-Object Length -Sum).Sum
Write-Host ("  ok - working tree: {0:N2} GB, largest file {1:N1} MB" -f `
    ($total/1GB), ((Get-ChildItem -Recurse -File | Where-Object { $_.FullName -notlike "*\.git\*" } |
                    Measure-Object Length -Maximum).Maximum/1MB))

Write-Host "=== remote ===" -ForegroundColor Cyan
if ([string]::IsNullOrWhiteSpace($RepoUrl)) {
    if (-not ((git remote) -contains "origin")) {
        throw "No 'origin' remote and no -RepoUrl given. Example: pwsh -File push_to_github.ps1 -RepoUrl https://github.com/USER/REPO.git"
    }
    Write-Host "  using existing remote:"
}
elseif ((git remote) -contains "origin") { git remote set-url origin $RepoUrl }
else { git remote add origin $RepoUrl }
git remote -v

Write-Host "=== staged pushes ===" -ForegroundColor Cyan
$commits = @(git log --reverse --format=%H)
if ($LASTEXITCODE -ne 0 -or $commits.Count -eq 0) { throw "No commits found." }
Write-Host ("  {0} commit(s) to publish on branch '{1}'" -f $commits.Count, $Branch)

$i = 0
foreach ($c in $commits) {
    $i++
    $subject = git log -1 --format=%s $c
    Write-Host ("==> [{0}/{1}] {2}  {3}" -f $i, $commits.Count, $c.Substring(0,8), $subject) -ForegroundColor Yellow
    git push origin "${c}:refs/heads/$Branch"
    if ($LASTEXITCODE -ne 0) {
        throw "Push failed at commit $($c.Substring(0,8)). Fix the network/auth and re-run this script - completed stages are already uploaded."
    }
}

git branch --set-upstream-to=origin/$Branch $Branch 2>$null | Out-Null
Write-Host ""
Write-Host "DONE. All commits published to $RepoUrl ($Branch)." -ForegroundColor Green
Write-Host "Note: GitHub shows a size warning above 1 GB - that is expected for this dataset."
