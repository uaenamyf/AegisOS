# AegisOS CyberDrill 无人干预演示脚本
# date: 2026-09-05
# dev: AegisOS Dev
# 用法:
#   .\tooling\scripts\drill_demo.ps1
#   .\tooling\scripts\drill_demo.ps1 -TargetRange 192.168.1.0/24 -MaxRounds 3
#   .\tooling\scripts\drill_demo.ps1 -SkipBackendStart   # 后端已运行时跳过自动启动
#   .\tooling\scripts\drill_demo.ps1 -KeepRunning        # 演示结束后不停止自动启动的后端
# 说明: 无人干预全流程——自动启动后端 -> 发起演练 -> 轮询至收敛 -> 输出总结与落盘路径。

param(
    [string]$TargetRange = "10.0.0.0/24",
    [int]$MaxRounds = 5,
    [int]$Port = 8000,
    [string]$ApiKey = "aegis-dev-key",
    [switch]$SkipBackendStart,
    [switch]$KeepRunning,
    [switch]$UseRealModel
)

$ErrorActionPreference = "Stop"
$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$BaseUrl = "http://127.0.0.1:$Port/api/v1"
$Headers = @{ "X-API-Key" = $ApiKey }
$script:BackendProc = $null

# ---- Python 解释器探测 ------------------------------------
# 优先 $env:AEGIS_PYTHON;否则探测能 import fastapi 的解释器绝对路径
# (Start-Process 子进程不继承当前 shell 的 PATH 解析,须用绝对路径)。
$Python = if ($env:AEGIS_PYTHON) {
    $env:AEGIS_PYTHON
} else {
    $found = $null
    $candidates = @(
        (Get-Command python -ErrorAction SilentlyContinue).Source,
        "python"
    ) | Where-Object { $_ } | Select-Object -Unique
    foreach ($cand in $candidates) {
        try {
            $prev = $ErrorActionPreference
            $ErrorActionPreference = "Continue"
            $out = & $cand -c "import fastapi, sys; print(sys.executable)" 2>&1
            $ErrorActionPreference = $prev
            if ($LASTEXITCODE -eq 0 -and ($out | Out-String).Trim()) {
                $found = $cand
                break
            }
        } catch {
            $ErrorActionPreference = "Continue"
        }
    }
    if ($found) { $found } else { "python" }
}
Write-Host "(backend) using python: $Python" -ForegroundColor DarkGray

# ---- 运行模式: 默认 mock(演示版依赖 mock 即可跑通);-UseRealModel 切真实 LLM ----
if (-not $UseRealModel) {
    $env:AEGIS_USE_MOCK = "true"
    Write-Host "(mode) forcing mock provider (use -UseRealModel to switch)" -ForegroundColor DarkGray
} else {
    Remove-Item Env:AEGIS_USE_MOCK -ErrorAction SilentlyContinue
    Write-Host "(mode) using real LLM provider (requires OPENAI_API_KEY)" -ForegroundColor DarkGray
}

function Test-BackendHealth {
    try {
        $resp = Invoke-WebRequest -Uri "$BaseUrl/health" -UseBasicParsing -TimeoutSec 3
        return $resp.StatusCode -eq 200
    } catch {
        return $false
    }
}

function Start-BackendIfNeeded {
    if (Test-BackendHealth) {
        Write-Host "(backend) already running at $BaseUrl" -ForegroundColor Green
        return
    }
    if ($SkipBackendStart) {
        Write-Host "(backend) not running and -SkipBackendStart given - abort" -ForegroundColor Yellow
        exit 2
    }
    Write-Host "(backend) starting uvicorn on :$Port ..." -ForegroundColor Cyan
    $logOut = Join-Path $PSScriptRoot ".drill_backend.out.log"
    $logErr = Join-Path $PSScriptRoot ".drill_backend.err.log"
    $script:BackendProc = Start-Process -FilePath $Python `
        -ArgumentList "-m", "uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "$Port" `
        -WorkingDirectory $ProjectRoot -PassThru -NoNewWindow `
        -RedirectStandardOutput $logOut -RedirectStandardError $logErr
    $ready = $false
    for ($i = 0; $i -lt 20; $i++) {
        Start-Sleep -Seconds 1
        if (Test-BackendHealth) { $ready = $true; break }
    }
    if (-not $ready) {
        Write-Host "(backend) failed to start within 20s" -ForegroundColor Red
        if ($script:BackendProc) { Stop-Process -Id $script:BackendProc.Id -Force -ErrorAction SilentlyContinue }
        exit 1
    }
    Write-Host "(backend) ready" -ForegroundColor Green
}

function Stop-BackendIfStarted {
    if ($script:BackendProc -and -not $KeepRunning) {
        Stop-Process -Id $script:BackendProc.Id -Force -ErrorAction SilentlyContinue
        Write-Host "(backend) stopped (auto-started by demo)" -ForegroundColor DarkGray
    }
}

# ---- 1) 后端就绪 ------------------------------------------
Start-BackendIfNeeded

# ---- 2) 发起演练 ------------------------------------------
Write-Host ""
Write-Host "(drill) starting drill target=$TargetRange max_rounds=$MaxRounds ..." -ForegroundColor Cyan
$body = @{ target_range = $TargetRange; max_rounds = $MaxRounds } | ConvertTo-Json
$start = Invoke-RestMethod -Method Post -Uri "$BaseUrl/drill/start" -Headers $Headers -Body $body -ContentType "application/json"
$drillId = $start.drill_id
Write-Host "(drill) drill_id=$drillId" -ForegroundColor Green

# ---- 3) 轮询至收敛(无人干预) ------------------------------
$deadline = (Get-Date).AddSeconds(120)
$status = "running"
while ((Get-Date) -lt $deadline) {
    Start-Sleep -Seconds 1
    $state = Invoke-RestMethod -Method Get -Uri "$BaseUrl/drill/$drillId" -Headers $Headers
    Write-Host "  [poll] status=$($state.status) rounds=$($state.rounds_executed)" -ForegroundColor DarkGray
    if ($state.status -eq "done" -or $state.status -eq "aborted") {
        $status = $state.status
        break
    }
}
if ($status -ne "done" -and $status -ne "aborted") {
    Write-Host "(drill) timeout waiting for completion" -ForegroundColor Red
    Stop-BackendIfStarted
    exit 1
}

# ---- 4) 输出结果 ------------------------------------------
$final = Invoke-RestMethod -Method Get -Uri "$BaseUrl/drill/$drillId" -Headers $Headers
$conclusion = if ($final.summary -and $final.summary.conclusion) { $final.summary.conclusion } else { "(none)" }
Write-Host ""
Write-Host "==========================================" -ForegroundColor White
Write-Host "   Drill Result (无人干预全自动完成)" -ForegroundColor White
Write-Host "==========================================" -ForegroundColor White
Write-Host "  drill_id:        $drillId"
Write-Host "  target_range:    $($final.target_range)"
Write-Host "  rounds_executed: $($final.rounds_executed)"
Write-Host "  convergence:     $($final.convergence_code)"
Write-Host "  summary:         $conclusion"
if ($final.summary -and $final.summary.memory_trace) {
    Write-Host "  memory_trace:    $($final.summary.memory_trace.Count) rounds of cross-round memory"
}
$recordPath = Join-Path $ProjectRoot "data\drills\$drillId.json"
if (Test-Path $recordPath) {
    Write-Host "  record file:     $recordPath"
}
Write-Host ""
Write-Host "  Live event stream: GET $BaseUrl/events?stream=drill.round  (SSE during drill)"
Write-Host "==========================================" -ForegroundColor White

Stop-BackendIfStarted
Write-Host "(drill) demo finished - exit 0" -ForegroundColor Green
exit 0
