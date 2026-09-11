# date: 2026-09-11
# dev: AegisOS
# change: add Docker Desktop deployment orchestration for app and sandbox

param(
    [ValidateSet("config", "build", "up", "status", "down")]
    [string]$Action = "config",
    [switch]$Sandbox,
    [switch]$UseDemoSecrets
)

$ErrorActionPreference = "Stop"
$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..\")).Path
$ComposeFile = Join-Path $ProjectRoot "infrastructure\delivery\deployment\docker\docker-compose.yml"
$SandboxComposeFile = Join-Path $ProjectRoot "infrastructure\delivery\deployment\docker\sandbox\docker-compose.yml"

function Assert-DockerReady {
    docker version *> $null
    if ($LASTEXITCODE -ne 0) {
        throw "Docker Desktop Engine is unavailable. Start Docker Desktop first."
    }
    docker compose version *> $null
    if ($LASTEXITCODE -ne 0) {
        throw "Docker Compose is unavailable. Update Docker Desktop."
    }
}

function Set-DeploymentSecrets {
    if ($UseDemoSecrets) {
        if (-not $env:AEGIS_AUTH_DEFAULT_KEY) {
            $env:AEGIS_AUTH_DEFAULT_KEY = "aegis-local-demo-key-2026"
        }
        if (-not $env:SPLUNK_PASSWORD) {
            $env:SPLUNK_PASSWORD = "AegisSandbox-2026!"
        }
    }
    if (-not $env:AEGIS_AUTH_DEFAULT_KEY) {
        throw "AEGIS_AUTH_DEFAULT_KEY is missing. Set it or use -UseDemoSecrets."
    }
    if ($Sandbox -and -not $env:SPLUNK_PASSWORD) {
        throw "SPLUNK_PASSWORD is missing. Set it or use -UseDemoSecrets."
    }
}

function Invoke-Compose([string]$File, [string[]]$Arguments) {
    & docker compose -f $File @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "Compose operation failed: $($Arguments -join ' ')"
    }
}

Set-Location $ProjectRoot
Assert-DockerReady
Set-DeploymentSecrets

$files = @($ComposeFile)
if ($Sandbox) {
    $files += $SandboxComposeFile
}

foreach ($file in $files) {
    switch ($Action) {
        "config" { Invoke-Compose $file @("config") }
        "build" {
            if ($file -eq $ComposeFile) { Invoke-Compose $file @("build") }
        }
        "up" {
            if ($file -eq $ComposeFile) { Invoke-Compose $file @("up", "-d") }
            else { Invoke-Compose $file @("--profile", "tools", "up", "-d") }
        }
        "status" { Invoke-Compose $file @("ps") }
        "down" { Invoke-Compose $file @("down", "--remove-orphans") }
    }
}

if ($Action -eq "up") {
    Write-Host "AegisOS Docker deployment started: http://localhost:8080" -ForegroundColor Green
    if ($Sandbox) {
        Write-Host "Sandbox started: aegisos-sandbox-range" -ForegroundColor Green
    }
}