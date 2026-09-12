# AegisOS 沙箱靶场编排脚本
# 用法：.\tooling\scripts\sandbox.ps1 -Action config

param(
    [ValidateSet("config", "up", "down")]
    [string]$Action = "config",
    [string]$ComposeFile = "infrastructure/delivery/deployment/docker/sandbox/docker-compose.yml"
)

$ErrorActionPreference = "Stop"
$composeArgs = @("compose", "-f", $ComposeFile)

switch ($Action) {
    "config" {
        & docker @composeArgs "config"
    }
    "up" {
        & docker @composeArgs "--profile" "tools" "up" "-d"
    }
    "down" {
        & docker @composeArgs "down" "--remove-orphans"
    }
}

if ($LASTEXITCODE -ne 0) {
    throw "sandbox action '$Action' failed with exit code $LASTEXITCODE"
}