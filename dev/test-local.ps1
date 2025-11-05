# Local testing script for Home Assistant integration

$hassfestPassed = $true
$lintPassed = $true

# Check if ruff is installed
Write-Host "Checking dependencies..." -ForegroundColor Cyan
try {
    python -m ruff --version | Out-Null
    Write-Host "✅ Ruff is installed" -ForegroundColor Green
} catch {
    Write-Host "⚠️  Installing ruff..." -ForegroundColor Yellow
    pip install ruff==0.6.4
    if ($LASTEXITCODE -ne 0) {
        Write-Host "❌ Failed to install ruff" -ForegroundColor Red
        $lintPassed = $false
    } else {
        Write-Host "✅ Ruff installed successfully" -ForegroundColor Green
    }
}

# Run linting validation
if ($lintPassed) {
    Write-Host "`nRunning lint validation..." -ForegroundColor Green
    python -m ruff check .
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✅ Lint validation PASSED" -ForegroundColor Green
    } else {
        Write-Host "❌ Lint validation FAILED" -ForegroundColor Red
        Write-Host "💡 Try running: python -m ruff check . --fix" -ForegroundColor Yellow
        $lintPassed = $false
    }
}

# Run hassfest validation
Write-Host "`nRunning hassfest validation..." -ForegroundColor Green
docker run --rm -v "${PWD}:/github/workspace" ghcr.io/home-assistant/hassfest

if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ Hassfest validation PASSED" -ForegroundColor Green
} else {
    Write-Host "❌ Hassfest validation FAILED" -ForegroundColor Red
    $hassfestPassed = $false
}

Write-Host "`nHACS validation requires GitHub token and is best tested via GitHub Actions." -ForegroundColor Yellow
Write-Host "You can check the HACS validation results in your GitHub Actions logs." -ForegroundColor Yellow

# Summary
Write-Host "`n=== SUMMARY ===" -ForegroundColor Cyan
if ($lintPassed) {
    Write-Host "✅ Lint validation PASSED" -ForegroundColor Green
} else {
    Write-Host "❌ Lint validation FAILED" -ForegroundColor Red
}

if ($hassfestPassed) {
    Write-Host "✅ Hassfest validation PASSED" -ForegroundColor Green
} else {
    Write-Host "❌ Hassfest validation FAILED" -ForegroundColor Red
}

Write-Host "⚠️  HACS validation requires GitHub API access (GitHub token)" -ForegroundColor Yellow
Write-Host "🚀 Push to GitHub to run full validation suite" -ForegroundColor Blue

if ($lintPassed -and $hassfestPassed) {
    Write-Host "`n🎉 All local validations PASSED!" -ForegroundColor Green
    exit 0
} else {
    Write-Host "`n❌ Some validations FAILED. Please fix the issues above." -ForegroundColor Red
    exit 1
}
