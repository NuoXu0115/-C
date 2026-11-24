<#
Push this repository to GitHub using STAGED pushes with automatic retries.

Why staged: the repo carries ~2.75 GB of data. A single `git push` of that size is
slow and easily cut off. Pushing one commit at a time bounds the cost of a dropped
connection to one stage (<= ~340 MB), and already-pushed commits are skipped when
you re-run the script.

Usage
-----
  pwsh -File push_to_github.ps1                     # uses existing 'origin'
  pwsh -File push_to_github.ps1 -RepoUrl https://github.com/<user>/<repo>.git

Prerequisite: create the repository on GitHub as an EMPTY repo
(no README, no .gitignore, no license), otherwise the first push is rejected.

If HTTPS keeps failing on your network, see the SSH fallback in README_GITHUB.md.
#>

param(
    [string]$RepoUrl = "",
    [string]$Branch  = "main",
    [int]$Retries    = 4
)

$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $PSScriptRoot

if (-not (Test-Path ".git")) { throw "Not a git repository: $PSScriptRoot" }

# ---------------------------------------------------------------- size guard
Write-Host "=== guard: no single file may exceed 100 MB ===" -ForegroundColor Cyan
$tracked = git ls-files
$big = $tracked | ForEach-Object {
    $f = Get-Item -LiteralPath $_ -ErrorAction SilentlyContinue
    if ($f -and $f.Length -gt 95MB) { "  TOO BIG: {0:N1} MB  {1}" -f ($f.Length/1MB), $_ }
}
if ($big) { $big; throw "GitHub rejects files over 100 MB. Aborting before any data is uploaded." }
$maxMB = ($tracked | ForEach-Object { (Get-Item -LiteralPath $_).Length } | Measure-Object -Maximum).Maximum/1MB
Write-Host ("  ok - {0} files, largest {1:N1} MB" -f $tracked.Count, $maxMB)

# ------------------------------------------------- network hardening for CN/lossy links
Write-Host "=== network settings ===" -ForegroundColor Cyan
git config http.version HTTP/1.1          # HTTP/2 multiplexing often resets here
git config http.postBuffer 524288000
git config http.lowSpeedLimit 1000        # abort only if < 1 KB/s ...
git config http.lowSpeedTime 600          # ... for 10 minutes
Write-Host "  http.version=HTTP/1.1, postBuffer=500MB, slow-abort=1KB/s for 600s"

# ---------------------------------------------------------------- remote
Write-Host "=== remote ===" -ForegroundColor Cyan
if ([string]::IsNullOrWhiteSpace($RepoUrl)) {
    if (-not ((git remote) -contains "origin")) {
        throw "No 'origin' remote and no -RepoUrl given."
    }
    Write-Host "  using existing remote"
}
elseif ((git remote) -contains "origin") { git remote set-url origin $RepoUrl }
else { git remote add origin $RepoUrl }
git remote -v

# ---------------------------------------------------------------- staged pushes
Write-Host "=== staged pushes ===" -ForegroundColor Cyan
$commits = @(git log --reverse --format=%H)
if ($LASTEXITCODE -ne 0 -or $commits.Count -eq 0) { throw "No commits found." }
Write-Host ("  {0} stage(s) -> branch '{1}', up to {2} attempts each" -f $commits.Count, $Branch, $Retries)
Write-Host ""

$i = 0
$t0 = Get-Date
foreach ($c in $commits) {
    $i++
    $short   = $c.Substring(0,8)
    $subject = git log -1 --format=%s $c

    $ok = $false
    for ($attempt = 1; $attempt -le $Retries; $attempt++) {
        Write-Host ("==> [{0}/{1}] {2} (attempt {3}/{4})  {5}" -f `
            $i, $commits.Count, $short, $attempt, $Retries, $subject) -ForegroundColor Yellow
        git push origin "${c}:refs/heads/$Branch"
        if ($LASTEXITCODE -eq 0) { $ok = $true; break }

        if ($attempt -lt $Retries) {
            $wait = [Math]::Min(10 * $attempt, 60)
            Write-Host ("    push failed; retrying in {0}s (network resets are normal on some links)" -f $wait) -ForegroundColor DarkYellow
            Start-Sleep -Seconds $wait
        }
    }
    if (-not $ok) {
        Write-Host ""
        Write-Host ("Stage {0} ({1}) failed after {2} attempts." -f $i, $short, $Retries) -ForegroundColor Red
        Write-Host "Already-pushed stages are safe. Fix the network/auth, then re-run this script:" -ForegroundColor Red
        Write-Host "    pwsh -File .\push_to_github.ps1" -ForegroundColor Red
        Write-Host "It resumes from the first unpublished stage." -ForegroundColor Red
        exit 1
    }
}

$span = [math]::Round(((Get-Date) - $t0).TotalMinutes, 1)
git branch --set-upstream-to=origin/$Branch $Branch 2>$null | Out-Null
Write-Host ""
Write-Host ("DONE - all {0} stages published in {1} min." -f $commits.Count, $span) -ForegroundColor Green
Write-Host "Open the repository page; GitHub may show a '>1 GB' notice, which is expected."
