# OmniVerse Wealth — Deployment Script (Windows PowerShell)
# Usage: .\deploy.ps1 [-Stage prod]

param(
    [string]$Stage = "prod"
)

$ErrorActionPreference = "Stop"
$InfraDir = $PSScriptRoot
$ProjectRoot = Split-Path $InfraDir -Parent

Write-Host "🌌 OmniVerse Wealth — Deploying to $Stage" -ForegroundColor Cyan
Write-Host "================================================"

# Step 1: Build frontend
Write-Host "📦 Building frontend..." -ForegroundColor Yellow
Set-Location "$ProjectRoot\frontend"
npm run build

# Step 2: Package Lambda layer
Write-Host "📦 Packaging Lambda dependencies layer..." -ForegroundColor Yellow
Set-Location $InfraDir
if (-not (Test-Path "lambda\layers\deps\python")) {
    New-Item -ItemType Directory -Path "lambda\layers\deps\python" -Force | Out-Null
}
pip install -r lambda\layers\deps\requirements.txt -t lambda\layers\deps\python --quiet

# Step 3: CDK Deploy
Write-Host "☁️  Deploying AWS infrastructure..." -ForegroundColor Yellow
Set-Location $InfraDir
pip install -r requirements.txt --quiet

cdk bootstrap 2>$null
cdk deploy --all --require-approval never

Write-Host ""
Write-Host "✅ Deployment complete!" -ForegroundColor Green
Write-Host "================================================"
Write-Host "Check the CloudFormation outputs for URLs."
