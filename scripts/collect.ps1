# Runs `ge ingest collect` for Task Scheduler.
#   Step log (start, end, result of each step): logs\collect.log
#   Full console output of each run:           logs\collect-output.log
# Exits with the command's exit code (non-zero if any step failed).

$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath 'C:\gridiron-edge-worker'
New-Item -ItemType Directory -Force -Path 'logs' | Out-Null

# Under Task Scheduler there is no console, so Python would print with the ANSI code page and
# fail on non-ASCII market text. Force UTF-8.
$env:PYTHONUTF8 = '1'
$env:PYTHONIOENCODING = 'utf-8'

$uv = (Get-Command uv -ErrorAction SilentlyContinue).Source
if (-not $uv) { $uv = Join-Path $env:LOCALAPPDATA 'Microsoft\WinGet\Links\uv.exe' }
if (-not (Test-Path -LiteralPath $uv)) {
    $stamp = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ss+00:00")
    Add-Content -LiteralPath 'logs\collect.log' -Encoding utf8 -Value "$stamp COLLECT not run: uv not found"
    exit 1
}

# cmd handles the redirect so stderr lines are kept as plain text and the exit code survives.
$stamp = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ss+00:00")
Add-Content -LiteralPath 'logs\collect-output.log' -Encoding utf8 -Value "===== $stamp ====="
cmd /c "`"$uv`" run ge ingest collect >> logs\collect-output.log 2>&1"
exit $LASTEXITCODE
