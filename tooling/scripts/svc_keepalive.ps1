# AegisOS 服务守护脚本（单实例 + 正确环境）
# 用法: powershell -ExecutionPolicy Bypass -File tooling\scripts\svc_keepalive.ps1
# 功能: 确保后端(8000)与前端(5173)始终存活；崩溃自动拉起，日志写 *_live.log
#
# 2026-09-13 重写要点（修复「切走再切回状态丢失」的运维根因）：
#   1. 单实例锁：同一时间只允许一个守护进程，避免多个后端抢同一端口。
#      两个后端同时 listen 8000 时，drill runtime 存在各自进程内存里，
#      请求被哪个进程应答是随机的 → 前一次点击创建的演练下一次查不到，
#      表现为「点了没反应 / 切回来又没了」。
#   2. 后端必须注入 tooling\configs\.env：否则 real 模式拿不到 OPENAI_API_KEY，
#      演练卡在第一步死等。
#   3. 用 -EscapedAddress 检查前先确认端口归属，拉起到真正空闲的端口。
#   4. 日志轮转：超过 5MB 截断，避免无限增长。
$ErrorActionPreference = 'SilentlyContinue'
$root = Split-Path (Split-Path $PSScriptRoot -Parent) -Parent   # 仓库根目录
$py   = 'C:\Users\33307\AppData\Local\Microsoft\WindowsApps\python.exe'
$node = 'C:\Program Files\nodejs\node.exe'

# ---- 单实例锁：已有守护在跑则直接退出 ----
$lockName = 'AegisOS-SvcKeepalive-Mutex'
$mutex = New-Object System.Threading.Mutex($false, $lockName)
if (-not $mutex.WaitOne(0)) {
  Write-Host '[svc] another keepalive is already running; exit'
  exit 0
}

function Test-Port([int]$p) {
  $null -ne (Get-NetTCPConnection -State Listen -LocalPort $p -ErrorAction SilentlyContinue |
    Where-Object { $_.OwningProcess -ne 0 })
}

function Import-DotEnv {
  # 把 tooling\configs\.env 刷进当前进程环境变量（子进程继承）
  $envPath = Join-Path $root 'tooling\configs\.env'
  if (-not (Test-Path $envPath)) { return }
  foreach ($line in Get-Content $envPath -Encoding UTF8) {
    $t = $line.Trim()
    if (-not $t -or $t.StartsWith('#')) { continue }
    $i = $t.IndexOf('=')
    if ($i -lt 1) { continue }
    $k = $t.Substring(0, $i).Trim()
    $v = $t.Substring($i + 1).Trim().Trim('"').Trim("'")
    Set-Item -Path "Env:$k" -Value $v
  }
}

function Rotate-Log([string]$path) {
  if (Test-Path $path) {
    $fi = Get-Item $path
    if ($fi.Length -gt 5MB) { Set-Content -Path $path -Value '' -Encoding UTF8 }
  }
}

function Start-Backend {
  $log = Join-Path $root 'backend.live.log'
  $err = Join-Path $root 'backend.live.err.log'
  Rotate-Log $log; Rotate-Log $err
  Write-Host '[svc] starting backend on 8000 (env loaded)...'
  # 绑 0.0.0.0（与 start.ps1 一致）：vite 代理目标是 http://localhost:8000，
  # Windows 上 localhost 常先解析到 ::1，只绑 127.0.0.1 会导致代理 502。
  Start-Process -FilePath $py -ArgumentList @(
    '-X','utf8','-m','uvicorn','backend.main:app','--host','0.0.0.0','--port','8000'
  ) -WorkingDirectory $root -WindowStyle Hidden `
    -RedirectStandardOutput $log -RedirectStandardError $err
}

function Start-Frontend {
  $fe  = Join-Path $root 'frontend'
  $log = Join-Path $fe 'vite.live.log'
  $err = Join-Path $fe 'vite.live.err.log'
  Rotate-Log $log; Rotate-Log $err
  Write-Host '[svc] starting vite on 5173...'
  Start-Process -FilePath $node -ArgumentList @(
    "`"$fe\node_modules\vite\bin\vite.js`"", '--host', '127.0.0.1', '--port', '5173'
  ) -WorkingDirectory $fe -WindowStyle Hidden `
    -RedirectStandardOutput $log -RedirectStandardError $err
}

Import-DotEnv

while ($true) {
  if (-not (Test-Port 8000)) { Start-Backend; Start-Sleep -Seconds 8 }
  if (-not (Test-Port 5173)) { Start-Frontend; Start-Sleep -Seconds 4 }
  # 周期性重刷 .env（改 Key / 改模式后无需重启守护即可被下次拉起继承）
  Import-DotEnv
  Start-Sleep -Seconds 5
}
