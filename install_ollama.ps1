# ==============================================================================
# TAEL V2: Ollama Model Installation & Verification Script (PowerShell)
# ==============================================================================
$ErrorActionPreference = "Stop"

Write-Host "========================================================================" -ForegroundColor Cyan
Write-Host " [TAEL V2] Starting Ollama Model Deployment & Verification" -ForegroundColor Cyan
Write-Host "========================================================================" -ForegroundColor Cyan

$WorkspaceDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$GgufDir      = Join-Path $WorkspaceDir "Granite-Final-Agent-GGUF"
$GgufFile     = Join-Path $GgufDir "granite-3.1-2b-instruct.Q4_K_M.gguf"
$Modelfile    = Join-Path $GgufDir "Modelfile"
$ModelName    = "tael-agent"

# 1. Check Ollama CLI
Write-Host "`n[1/4] Checking Ollama CLI installation..." -ForegroundColor Yellow
if (-not (Get-Command "ollama" -ErrorAction SilentlyContinue)) {
    Write-Error "Ollama CLI is not installed or not in PATH. Download from https://ollama.com/download"
    exit 1
}
$OllamaVersion = ollama --version
Write-Host "  [OK] $OllamaVersion" -ForegroundColor Green

# 2. Validate GGUF & Modelfile existence
Write-Host "`n[2/4] Validating GGUF & Modelfile..." -ForegroundColor Yellow
if (-not (Test-Path $GgufFile)) {
    Write-Error "GGUF model file not found at: $GgufFile"
    exit 1
}
if (-not (Test-Path $Modelfile)) {
    Write-Error "Modelfile not found at: $Modelfile"
    exit 1
}
$SizeMB = [math]::Round((Get-Item $GgufFile).Length / 1MB, 2)
Write-Host "  [OK] GGUF Verified ($SizeMB MB)" -ForegroundColor Green
Write-Host "  [OK] Modelfile Verified ($Modelfile)" -ForegroundColor Green

# 3. Create Model in Ollama
Write-Host "`n[3/4] Creating '$ModelName' in Ollama..." -ForegroundColor Yellow
Push-Location $GgufDir
try {
    ollama create $ModelName -f "Modelfile"
    if ($LASTEXITCODE -ne 0) {
        throw "ollama create exited with code $LASTEXITCODE"
    }
    Write-Host "  [OK] Successfully registered '$ModelName' in Ollama" -ForegroundColor Green
} finally {
    Pop-Location
}

# 4. Verify Model Execution
Write-Host "`n[4/4] Verifying '$ModelName' execution..." -ForegroundColor Yellow
$TestResponse = $null | ollama run $ModelName "State your name and primary role in one concise sentence."
Write-Host "  [RESPONSE]: $TestResponse" -ForegroundColor White

Write-Host "`n========================================================================" -ForegroundColor Cyan
Write-Host " [DEPLOYMENT COMPLETE] Run 'ollama run tael-agent' or 'python tael_agent_runtime.py'" -ForegroundColor Green
Write-Host "========================================================================" -ForegroundColor Cyan
