# AegisOS 一键启动脚本 (Windows PowerShell)
# date: 2026-07-08
# dev: GitHub Copilot (glm-5.2)
# change: 新建 Windows 版一键启动脚本，同时拉起后端(FastAPI)和前端(Vite)
# 用法:
#   .\start.ps1                启动前后端
#   .\start.ps1 backend       仅启动后端
#   .\start.ps1 frontend      仅启动前端
#   .\start.ps1 stop          停止所有

param([string]$Action = 'all')

$ErrorActionPreference = 'Stop'
$ProjectRoot = $PSScriptRoot

# ── 工具路径（优先环境变量，否则用默认值）──────────────────
$Python       = if ($env:AEGIS_PYTHON)   { $env:AEGIS_PYTHON }   else { 'D:\Python\python.exe' }
$Npm          = if ($env:AEGIS_NPM)      { $env:AEGIS_NPM }      else { 'npm' }
$BackendPort  = if ($env:AEGIS_BACKEND_PORT)  { $env:AEGIS_BACKEND_PORT }  else { '8000' }
$FrontendPort = if ($env:AEGIS_FRONTEND_PORT) { $env:AEGIS_FRONTEND_PORT } else { '5173' }

# ── 加载 .env（如果存在）─────────────────────────────────
$EnvFile = Join-Path $ProjectRoot 'tooling\configs\.env'
if (Test-Path $EnvFile) {
    Get-Content $EnvFile | ForEach-Object {
        if ($_ -match '^\s*([^#=]+)=(.*)$') {
            [Environment]::SetEnvironmentVariable($Matches[1].Trim(), $Matches[2].Trim(), 'Process')
        }
    }
}

# 全局 PID 跟踪
$global:BackendPid  = $null
$global:FrontendPid = $null

function Start-Backend {
    Write-Host '(backend) Starting FastAPI on :' $BackendPort '...' -ForegroundColor Cyan
    $proc = Start-Process -FilePath $Python `
        -ArgumentList '-m', 'uvicorn', 'backend.main:app', '--reload', '--host', '0.0.0.0', '--port', $BackendPort `
        -WorkingDirectory $ProjectRoot `
        -PassThru -NoNewWindow
    $global:BackendPid = $proc.Id
    # 等待后端启动（最多 15 秒，每秒轮询一次 health 端点）
    $maxWait = 15
    $ready = $false
    for ($i = 0; $i -lt $maxWait; $i++) {
        Start-Sleep -Seconds 1
        try {
            $resp = Invoke-WebRequest -Uri "http://127.0.0.1:$BackendPort/api/v1/health" -UseBasicParsing -TimeoutSec 3
            if ($resp.StatusCode -eq 200) {
                $ready = $true
                break
            }
        } catch {
            # 还没启动好，继续等
        }
    }
    if ($ready) {
        Write-Host "(backend) Running at http://localhost:$BackendPort" -ForegroundColor Green
        Write-Host "  Health:  GET  http://localhost:$BackendPort/api/v1/health"
        Write-Host "  API docs: http://localhost:$BackendPort/docs"
        Write-Host "  API key:  X-API-Key: aegis-dev-key"
    } else {
        Write-Host '(backend) Health check failed (server may still be starting)' -ForegroundColor Yellow
    }
}

function Start-Frontend {
    Write-Host '(frontend) Starting Vite dev server on :' $FrontendPort '...' -ForegroundColor Cyan
    $frontendDir = Join-Path $ProjectRoot 'frontend'
    $proc = Start-Process -FilePath 'cmd' `
        -ArgumentList '/c', 'npm run dev -- --port', $FrontendPort `
        -WorkingDirectory $frontendDir `
        -PassThru -NoNewWindow
    $global:FrontendPid = $proc.Id
    Start-Sleep -Seconds 3
    Write-Host "(frontend) Running at http://localhost:$FrontendPort" -ForegroundColor Green
}

function Stop-All {
    if ($global:BackendPid) {
        Stop-Process -Id $global:BackendPid -Force -ErrorAction SilentlyContinue
        Write-Host "(backend) Stopped (pid $($global:BackendPid))"
    }
    if ($global:FrontendPid) {
        Stop-Process -Id $global:FrontendPid -Force -ErrorAction SilentlyContinue
        Write-Host "(frontend) Stopped (pid $($global:FrontendPid))"
    }
}

# ── 主逻辑 ──────────────────────────────────────────────
switch ($Action.ToLower()) {
    'backend' {
        Start-Backend
        Write-Host "`nPress Ctrl+C to stop." -ForegroundColor DarkGray
        while ($true) { Start-Sleep -Seconds 1 }
    }
    'frontend' {
        Start-Frontend
        Write-Host "`nPress Ctrl+C to stop." -ForegroundColor DarkGray
        while ($true) { Start-Sleep -Seconds 1 }
    }
    'stop' {
        Stop-All
    }
    default {
        Write-Host '============================================' -ForegroundColor White
        Write-Host '   AegisOS - Starting (Backend + Frontend)  ' -ForegroundColor White
        Write-Host '============================================' -ForegroundColor White
        Write-Host ''
        Start-Backend
        Write-Host ''
        Start-Frontend
        Write-Host ''
        Write-Host '------------------------------------------' -ForegroundColor DarkGray
        Write-Host "  Backend:  http://localhost:$BackendPort"
        Write-Host "  Frontend: http://localhost:$FrontendPort"
        Write-Host "  API docs: http://localhost:$BackendPort/docs"
        Write-Host '  API key:  aegis-dev-key'
        Write-Host '------------------------------------------' -ForegroundColor DarkGray
        Write-Host ''
        Write-Host 'Press Ctrl+C to stop both.' -ForegroundColor DarkGray
        Write-Host ''
        try {
            while ($true) { Start-Sleep -Seconds 1 }
        } finally {
            Stop-All
        }
    }
}
