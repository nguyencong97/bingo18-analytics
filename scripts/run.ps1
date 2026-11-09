# PowerShell runner script for Windows Task Scheduler
$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoDir = Split-Path -Parent $ScriptDir
Set-Location $RepoDir

# Jitter 0-10s
$jitter = Get-Random -Minimum 0 -Maximum 10
Start-Sleep -Seconds $jitter

# Load .env if present
if (Test-Path ".env") {
    Get-Content ".env" | ForEach-Object {
        $line = $_.Trim()
        if ($line -and -not $line.StartsWith("#") -and $line.Contains("=")) {
            $parts = $line.Split("=", 2)
            [System.Environment]::SetEnvironmentVariable($parts[0].Trim(), $parts[1].Trim(), "Process")
        }
    }
}

Write-Output "[$(Get-Date -Format o)] Chạy crawler..."
$crawlOut = python -m crawler.run 2>&1
Write-Output $crawlOut

Write-Output "[$(Get-Date -Format o)] Kiểm tra tính toàn vẹn..."
python -m stats.integrity

# Check if data files changed
$gitStatus = git status --porcelain data/
if ($gitStatus) {
    $commitMsg = "data: update draws $(Get-Date -Format 'yyyy-MM-dd HH:mm')"
    foreach ($line in $crawlOut) {
        if ($line -match "data: \+\d+ draws") {
            $commitMsg = $line
            break
        }
    }
    git add data/
    git commit -m "$commitMsg"
    Write-Output "Đã commit dữ liệu mới: $commitMsg"
}

# Healthchecks ping
if ($env:HEALTHCHECKS_URL) {
    try {
        Invoke-RestMethod -Uri $env:HEALTHCHECKS_URL -TimeoutSec 10 | Out-Null
    } catch {
        Write-Warning "Không thể ping Healthchecks: $_"
    }
}
Write-Output "[$(Get-Date -Format o)] Hoàn thành chu kỳ."
