# PowerShell script to run Home Assistant for EnergyMe development
# Usage: .\run-ha-dev.ps1

$ErrorActionPreference = 'Stop'

# Paths
$repoRoot = (Get-Location).Path
$configDir = Join-Path $repoRoot 'config'
$ccDir = Join-Path $repoRoot 'custom_components\energyme'
$yamlFile = Join-Path $configDir 'configuration.yaml'
$containerName = 'ha-energyme-dev'

# Ensure Docker is available
if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    Write-Host "Docker is not installed or not in PATH." -ForegroundColor Red
    exit 1
}

# Ensure config directory exists
if (-not (Test-Path $configDir)) {
    Write-Host "Creating config directory..." -ForegroundColor Yellow
    New-Item -ItemType Directory -Path $configDir | Out-Null
}

# Ensure configuration.yaml exists
if (-not (Test-Path $yamlFile)) {
    Write-Host "Creating configuration.yaml..." -ForegroundColor Yellow
    Set-Content -Path $yamlFile -Value "# Home Assistant configuration for EnergyMe dev\n"
}

# Add debug logger config if not present
$loggerBlock = @"
logger:
  default: warning
  logs:
    custom_components.energyme: debug
"@
$yamlContent = Get-Content $yamlFile -Raw
if ($yamlContent -notmatch 'custom_components.energyme: debug') {
    Write-Host "Adding debug logger config to configuration.yaml..." -ForegroundColor Yellow
    Add-Content -Path $yamlFile -Value $loggerBlock
}

# Stop and remove any existing container
if ((docker ps -a --format '{{.Names}}' | Select-String -Pattern "^$containerName$").Length -gt 0) {
    Write-Host "Stopping and removing existing container..." -ForegroundColor Yellow
    docker stop $containerName | Out-Null
    docker rm $containerName | Out-Null
}

# Start Home Assistant container
Write-Host "Starting Home Assistant dev container..." -ForegroundColor Cyan

docker run -d `
  --name $containerName `
  --restart unless-stopped `
  -p 8123:8123 `
  -e TZ=Etc/UTC `
    -v "${configDir}:/config" `
    -v "${ccDir}:/config/custom_components/energyme" `
  ghcr.io/home-assistant/home-assistant:stable

Write-Host "\nHome Assistant is starting. Access it at: http://localhost:8123" -ForegroundColor Green
Write-Host "If you edit your integration, restart the container with: docker restart $containerName" -ForegroundColor Green
Write-Host "To view logs: docker logs -f $containerName" -ForegroundColor Green
