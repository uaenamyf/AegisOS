# date: 2026-09-14
# dev: AegisOS
# change: Docker-free Windows one-click launcher with .env loading, PID management, and health checks

param(
    [ValidateSet("start", "all", "backend", "frontend", "stop", "status", "restart")]
    [string]$Action = "start"
)

$ErrorActionPreference = "Stop"
$ProjectRoot = $PSScriptRoot
$PidFile = Join-Path $ProjectRoot ".aegisos-pids.json"
$BackendPort = if ($env:AEGIS_BACKEND_PORT) { $env:AEGIS_BACKEND_PORT } else { "8000" }
$FrontendPort = if ($env:AEGIS_FRONTEND_PORT) { $env:AEGIS_FRONTEND_PORT } else { "5173" }

function Resolve-Python {
    $candidates = @()
    if ($env:AEGIS_PYTHON) { $candidates += $env:AEGIS_PYTHON }
    $pythonCommand = Get-Command python -ErrorAction SilentlyContinue
    if ($pythonCommand) { $candidates += $pythonCommand.Source }
    $candidates += @(
        (Join-Path $ProjectRoot ".venv\Scripts\python.exe"),
        (Join-Path $ProjectRoot "venv\Scripts\python.exe"),
        "D:\Anaconda\envs\deeplearning\python.exe"
    )
    foreach ($candidate in ($candidates | Select-Object -Unique)) {
        if (-not (Test-Path $candidate) -and $candidate -notmatch "^[a-zA-Z0-9_.-]+$") { continue }
        try {
            if ((& $candidate -c "print(1)" 2>$null) -eq "1") { return $candidate }
        } catch { }
    }
    throw "No usable Python found. Set AEGIS_PYTHON to python.exe."
}

function Import-EnvFile {
    $rootEnv = Join-Path $ProjectRoot ".env"
    $fallbackEnv = Join-Path $ProjectRoot "tooling\configs\.env"
    $file = if (Test-Path $rootEnv) { $rootEnv } elseif (Test-Path $fallbackEnv) { $fallbackEnv } else { $null }
    if (-not $file) { return }
    Get-Content $file | ForEach-Object {
        if ($_ -match '^\s*([^#=]+?)\s*=\s*(.*)\s*$') {
            $name = $Matches[1].Trim()
            $value = $Matches[2].Trim().Trim('"').Trim("'")
            [Environment]::SetEnvironmentVariable($name, $value, "Process")
        }
    }
}

function Test-Port([int]$Port) {
    try { return (Test-NetConnection 127.0.0.1 -Port $Port -InformationLevel Quiet) } catch { return $false }
}

function Get-ProcessState {
    if (-not (Test-Path $PidFile)) { return @{} }
    try { return (Get-Content $PidFile -Raw | ConvertFrom-Json -AsHashtable) } catch { return @{} }
}

function Save-ProcessState([hashtable]$State) {
    $State | ConvertTo-Json | Set-Content $PidFile -Encoding UTF8
}

function Stop-Aegis {
    $state = Get-ProcessState
    foreach ($name in @("backend", "frontend")) {
        if ($state.ContainsKey($name)) {
            $process = Get-Process -Id ([int]$state[$name]) -ErrorAction SilentlyContinue
            if ($process) {
                Stop-Process -Id $process.Id -Force -ErrorAction SilentlyContinue
                Write-Host "[$name] stopped (pid $($process.Id))" -ForegroundColor Yellow
            }
        }
    }
    Remove-Item $PidFile -Force -ErrorAction SilentlyContinue
}

function Start-Backend {
    if (Test-Port ([int]$BackendPort)) { Write-Host "[backend] already listening on $BackendPort" -ForegroundColor Yellow; return $null }
    $python = Resolve-Python
    $process = Start-Process -FilePath $python -ArgumentList @(
        "-m", "uvicorn", "backend.main:app", "--reload", "--host", "0.0.0.0", "--port", $BackendPort
    ) -WorkingDirectory $ProjectRoot -PassThru -WindowStyle Minimized
    Write-Host "[backend] starting with $python (pid $($process.Id))" -ForegroundColor Cyan
    for ($i = 0; $i -lt 30; $i++) {
        Start-Sleep -Seconds 1
        try {
            $health = Invoke-WebRequest "http://127.0.0.1:$BackendPort/api/v1/health" -UseBasicParsing -TimeoutSec 2
            if ($health.StatusCode -eq 200) { Write-Host "[backend] healthy: http://localhost:$BackendPort" -ForegroundColor Green; return $process.Id }
        } catch { }
    }
    throw "Backend startup failed. Check port $BackendPort or Python environment."
}

function Start-Frontend {
    if (Test-Port ([int]$FrontendPort)) { Write-Host "[frontend] already listening on $FrontendPort" -ForegroundColor Yellow; return $null }
    $env:VITE_API_BASE_URL = "http://localhost:$BackendPort/api/v1"
    $env:VITE_WS_URL = "ws://localhost:$BackendPort/ws/v1/stream"
    $env:VITE_API_KEY = if ($env:AEGIS_AUTH_DEFAULT_KEY) { $env:AEGIS_AUTH_DEFAULT_KEY } else { "aegis-dev-key" }
    $process = Start-Process -FilePath "cmd.exe" -ArgumentList @("/c", "npm", "run", "dev", "--", "--host", "0.0.0.0", "--port", $FrontendPort) -WorkingDirectory (Join-Path $ProjectRoot "frontend") -PassThru -WindowStyle Minimized
    Write-Host "[frontend] starting (pid $($process.Id))" -ForegroundColor Cyan
    for ($i = 0; $i -lt 20; $i++) {
        Start-Sleep -Seconds 1
        if (Test-Port ([int]$FrontendPort)) { Write-Host "[frontend] ready: http://localhost:$FrontendPort" -ForegroundColor Green; return $process.Id }
    }
    throw "Frontend startup failed. Check npm or port $FrontendPort."
}

function Show-Status {
    $state = Get-ProcessState
    Write-Host "AegisOS status" -ForegroundColor White
    Write-Host "  backend : http://localhost:$BackendPort (port $(if (Test-Port ([int]$BackendPort)) { 'up' } else { 'down' }))"
    Write-Host "  frontend: http://localhost:$FrontendPort (port $(if (Test-Port ([int]$FrontendPort)) { 'up' } else { 'down' }))"
    if ($state.Count -gt 0) { $state | Format-Table }
}

Import-EnvFile
switch ($Action.ToLower()) {
    "stop" { Stop-Aegis; break }
    "status" { Show-Status; break }
    "restart" { Stop-Aegis; Start-Sleep -Seconds 1; $Action = "start" }
}
if ($Action.ToLower() -in @("start", "all", "restart")) {
    $state = @{}
    $backendPid = Start-Backend
    if ($backendPid) { $state.backend = $backendPid }
    $frontendPid = Start-Frontend
    if ($frontendPid) { $state.frontend = $frontendPid }
    Save-ProcessState $state
    Write-Host "`nAegisOS ready: http://localhost:$FrontendPort" -ForegroundColor Green
    Write-Host "API docs: http://localhost:$BackendPort/docs"
    Write-Host "Stop: .\start.ps1 stop | Status: .\start.ps1 status"
} elseif ($Action.ToLower() -eq "backend") {
    $state = @{ backend = (Start-Backend) }
    Save-ProcessState $state
} elseif ($Action.ToLower() -eq "frontend") {
    $state = @{ frontend = (Start-Frontend) }
    Save-ProcessState $state
}
