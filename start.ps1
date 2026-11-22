# KPSS Radar - Tek Tıkla Windows Başlatıcı
$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$RootDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$BackendDir = Join-Path $RootDir "backend"
$FrontendDir = Join-Path $RootDir "frontend"
$VenvDir = Join-Path $BackendDir ".venv"
$VenvPython = Join-Path $VenvDir "Scripts\python.exe"
$VenvPip = Join-Path $VenvDir "Scripts\pip.exe"
$FrontendDistIndex = Join-Path $FrontendDir "dist\index.html"
$AppUrl = "http://127.0.0.1:8000"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  KPSS Radar - Kamu Alım Takip Sistemi  " -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# 1. Backend sanal ortam kontrolü
if (-not (Test-Path $VenvPython)) {
    Write-Host "[1/3] Python sanal ortamı (backend\.venv) oluşturuluyor..." -ForegroundColor Yellow
    $PythonCmd = $null
    if (Get-Command python -ErrorAction SilentlyContinue) {
        $PythonCmd = "python"
    } elseif (Get-Command py -ErrorAction SilentlyContinue) {
        $PythonCmd = "py"
    } else {
        Write-Host "HATA: Sistemde Python bulunamadı. Lütfen Python 3.11+ kurun." -ForegroundColor Red
        exit 1
    }

    if ($PythonCmd -eq "py") {
        & py -3 -m venv $VenvDir
    } else {
        & python -m venv $VenvDir
    }

    Write-Host "[1/3] Python bağımlılıkları kuruluyor (requirements.txt)..." -ForegroundColor Yellow
    & $VenvPython -m pip install --upgrade pip
    & $VenvPip install -r (Join-Path $BackendDir "requirements.txt")
} else {
    Write-Host "[1/3] Python sanal ortamı hazır." -ForegroundColor Green
}

# 2. Frontend üretim derlemesi kontrolü
if (-not (Test-Path $FrontendDistIndex)) {
    Write-Host "[2/3] Frontend derleniyor (frontend\dist bulunamadı)..." -ForegroundColor Yellow
    if (-not (Get-Command npm.cmd -ErrorAction SilentlyContinue)) {
        Write-Host "HATA: npm.cmd bulunamadı. Lütfen Node.js (LTS) kurun." -ForegroundColor Red
        exit 1
    }
    Push-Location $FrontendDir
    try {
        & npm.cmd install
        if ($LASTEXITCODE -ne 0) { throw "npm.cmd install başarısız oldu." }
        & npm.cmd run build
        if ($LASTEXITCODE -ne 0) { throw "npm.cmd run build başarısız oldu." }
    } finally {
        Pop-Location
    }
} else {
    Write-Host "[2/3] Frontend derlemesi (frontend\dist) hazır." -ForegroundColor Green
}

# 3. Tarayıcıyı 2 saniye sonra aç ve Uvicorn sunucusunu başlat
Write-Host "[3/3] Sunucu başlatılıyor: $AppUrl" -ForegroundColor Green
Write-Host "Durdurmak için bu pencerede Ctrl+C tuşlarına basın." -ForegroundColor DarkGray
Write-Host ""

Start-Process powershell -WindowStyle Hidden -ArgumentList @(
    "-NoProfile",
    "-Command",
    "Start-Sleep -Seconds 2; Start-Process '$AppUrl'"
)

Push-Location $BackendDir
try {
    & $VenvPython -m uvicorn app.main:app --host 127.0.0.1 --port 8000
} finally {
    Pop-Location
}
