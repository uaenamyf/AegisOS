# AegisOS 边缘服务一键部署脚本 (PowerShell)
# 用法: .\deploy_edge.ps1 [-Server user@host] [-Port 8900] [-Model qwen2.5:7b]
#       不传 -Server 则仅本地启动（用于开发调试）

param(
    [string]$Server = "",
    [string]$EdgeScript = "tooling/scripts/edge_server.py",
    [int]$Port = 8900,
    [string]$Model = ""
)

$ErrorActionPreference = "Stop"

$remotePath = "/tmp/aegis_edge_server.py"

# ---- 本地启动（无 -Server）----
if (-not $Server) {
    Write-Host "[deploy_edge] 本地启动模式（端口 $Port）" -ForegroundColor Cyan
    $args = @("tooling/scripts/edge_server.py", "--port", $Port)
    if ($Model) {
        $args += "--ollama-model", $Model
    }
    Write-Host "[deploy_edge] 启动命令: python $args" -ForegroundColor Green
    & python $args
    exit 0
}

# ---- 远程部署 ----
Write-Host "[deploy_edge] 部署到 $Server`:$Port" -ForegroundColor Cyan

# 1. 上传脚本
Write-Host "[deploy_edge] (1/3) 上传 edge_server.py ..." -ForegroundColor Yellow
scp $EdgeScript "${Server}:${remotePath}"
if ($LASTEXITCODE -ne 0) {
    Write-Host "[deploy_edge] SCP 失败。请检查服务器是否可达: $Server" -ForegroundColor Red
    Write-Host "[deploy_edge] 提示：手动确认 ssh $Server 可连通后再试。" -ForegroundColor Red
    exit 1
}

# 2. 杀掉旧进程
Write-Host "[deploy_edge] (2/3) 清理旧进程 ..." -ForegroundColor Yellow
ssh $Server "pkill -f aegis_edge_server.py 2>/dev/null; echo ok" | Out-Null

# 3. 启动新进程
$modelArg = if ($Model) { "--ollama-model $Model" } else { "" }
Write-Host "[deploy_edge] (3/3) 启动边缘服务 ..." -ForegroundColor Yellow
ssh $Server "nohup python3 $remotePath --port $Port $modelArg > /tmp/aegis_edge.log 2>&1 &"

# 4. 探活
Start-Sleep -Seconds 2
Write-Host "[deploy_edge] 探活中..." -ForegroundColor Yellow
$result = ssh $Server "curl -s http://localhost:$Port/health"
if ($result -match '"status":\s*"ok"') {
    Write-Host "[deploy_edge] 部署成功！$Server :$Port 已就绪" -ForegroundColor Green
    Write-Host "[deploy_edge] 健康检查: $result" -ForegroundColor Green
} else {
    Write-Host "[deploy_edge] 部署可能未就绪，请手动检查: ssh $Server 'cat /tmp/aegis_edge.log'" -ForegroundColor Yellow
}