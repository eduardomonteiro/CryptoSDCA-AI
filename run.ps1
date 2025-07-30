<#
run.ps1 - Launcher corrigido para CryptoSDCA-AI
Resolve problemas de ativação do conda e imports
#>

[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$ErrorActionPreference = 'Continue'  # Changed to Continue to not stop on warnings

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "CryptoSDCA-AI - Launcher Corrigido" -ForegroundColor Cyan  
Write-Host "============================================================" -ForegroundColor Cyan

# Navegar para diretório do projeto
Set-Location -Path $PSScriptRoot
Write-Host "📁 Diretório do projeto: $PSScriptRoot" -ForegroundColor Gray

# === FASE 1: CONFIGURAR CONDA CORRETAMENTE ===
Write-Host "`n[1] Configurando Conda..." -ForegroundColor Green

# Encontrar conda.exe
$condaExe = $null
$possiblePaths = @(
    "$env:CONDA_EXE",
    "$env:USERPROFILE\anaconda3\Scripts\conda.exe",
    "$env:USERPROFILE\miniconda3\Scripts\conda.exe", 
    "C:\ProgramData\Anaconda3\Scripts\conda.exe",
    "C:\ProgramData\Miniconda3\Scripts\conda.exe"
)

foreach ($path in $possiblePaths) {
    if ($path -and (Test-Path $path)) {
        $condaExe = $path
        break
    }
}

if (-not $condaExe) {
    Write-Error "❌ Conda não encontrado! Instale Anaconda ou Miniconda."
    pause
    exit 1
}

Write-Host "✅ Conda encontrado em: $condaExe" -ForegroundColor Green

# Verificar se ambiente existe
$envExists = & $condaExe env list | Select-String "cryptosdca"
if (-not $envExists) {
    Write-Host "⚠️ Criando ambiente 'cryptosdca'..." -ForegroundColor Yellow
    & $condaExe create -n cryptosdca python=3.11 -y
}

# === FASE 2: ATIVAR AMBIENTE E CONFIGURAR PATH ===
Write-Host "`n[2] Ativando ambiente..." -ForegroundColor Yellow

# Obter caminho do ambiente
$condaInfo = & $condaExe info --base
$envPath = Join-Path $condaInfo "envs\cryptosdca"

if (-not (Test-Path $envPath)) {
    Write-Error "❌ Ambiente cryptosdca não encontrado em: $envPath"
    pause
    exit 1
}

# Configurar PATH para usar o ambiente
$envScripts = Join-Path $envPath "Scripts"
$envLibrary = Join-Path $envPath "Library\bin"
$env:PATH = "$envPath;$envScripts;$envLibrary;$env:PATH"

# Configurar PYTHONPATH
$env:PYTHONPATH = "$PSScriptRoot;$env:PYTHONPATH"

Write-Host "✅ Ambiente ativado: $envPath" -ForegroundColor Green
Write-Host "✅ PYTHONPATH configurado: $PSScriptRoot" -ForegroundColor Green

# === FASE 3: VERIFICAR PYTHON ===
Write-Host "`n[3] Verificando Python..." -ForegroundColor Yellow

$pythonExe = Join-Path $envPath "python.exe"
if (-not (Test-Path $pythonExe)) {
    Write-Error "❌ Python não encontrado em: $pythonExe"
    pause
    exit 1
}

$pythonVersion = & $pythonExe --version
Write-Host "✅ Python ativo: $pythonVersion" -ForegroundColor Green
Write-Host "✅ Localização: $pythonExe" -ForegroundColor Gray

# === FASE 4: INSTALAR DEPENDÊNCIAS ===
Write-Host "`n[4] Instalando dependências..." -ForegroundColor Yellow

$pipExe = Join-Path $envScripts "pip.exe"

# Atualizar pip
Write-Host "Atualizando pip..." -ForegroundColor Gray
& $pythonExe -m pip install --upgrade pip --quiet

# Instalar dependências essenciais
$essentialPackages = @(
    "pydantic-settings==2.1.0",
    "pydantic==2.5.0", 
    "fastapi==0.104.1",
    "uvicorn[standard]==0.24.0",
    "itsdangerous==2.1.2",
    "starlette==0.27.0",
    "python-multipart==0.0.6",
    "jinja2==3.1.2",
    "sqlalchemy==2.0.23",
    "python-dotenv==1.0.0",
    "loguru==0.7.2"
)

foreach ($package in $essentialPackages) {
    Write-Host "Instalando $package..." -ForegroundColor Gray
    & $pythonExe -m pip install $package --quiet --no-warn-script-location
}

# === FASE 5: TESTAR IMPORTS ===
Write-Host "`n[5] Testando imports..." -ForegroundColor Yellow

$importTests = @{
    "Pydantic v2" = "import pydantic; print('v' + pydantic.VERSION)"
    "Pydantic Settings" = "import pydantic_settings; print('OK')"
    "FastAPI" = "import fastapi; print('v' + fastapi.__version__)"
    "SQLAlchemy" = "import sqlalchemy; print('v' + sqlalchemy.__version__)"
    "Uvicorn" = "import uvicorn; print('OK')"
}

$allPassed = $true
foreach ($testName in $importTests.Keys) {
    try {
        $result = & $pythonExe -c $importTests[$testName] 2>$null
        if ($result) {
            Write-Host "✅ $testName : $result" -ForegroundColor Green
        } else {
            Write-Host "❌ $testName : Falhou" -ForegroundColor Red
            $allPassed = $false
        }
    } catch {
        Write-Host "❌ $testName : Erro" -ForegroundColor Red
        $allPassed = $false
    }
}

if (-not $allPassed) {
    Write-Host "`n⚠️ Alguns imports falharam, mas continuando..." -ForegroundColor Yellow
}

# === FASE 6: CRIAR ESTRUTURA ===
Write-Host "`n[6] Verificando estrutura do projeto..." -ForegroundColor Yellow

$directories = @("data", "api", "api/routes", "src", "src/core", "src/models", "templates", "static", "scripts", "logs")
foreach ($dir in $directories) {
    if (-not (Test-Path $dir)) {
        New-Item -Path $dir -ItemType Directory -Force | Out-Null
        Write-Host "Criado: $dir" -ForegroundColor Gray
    }
}

# Criar __init__.py files
$initFiles = @(
    "api/__init__.py",
    "api/routes/__init__.py",
    "src/__init__.py", 
    "src/core/__init__.py",
    "src/models/__init__.py"
)

foreach ($initFile in $initFiles) {
    if (-not (Test-Path $initFile)) {
        '"""Package initialization"""' | Out-File -FilePath $initFile -Encoding UTF8
        Write-Host "Criado: $initFile" -ForegroundColor Gray
    }
}

# === FASE 7: INICIALIZAR BANCO ===
Write-Host "`n[7] Inicializando banco de dados..." -ForegroundColor Cyan

if (Test-Path "scripts/init_db.py") {
    try {
        & $pythonExe scripts/init_db.py
        Write-Host "✅ Banco inicializado!" -ForegroundColor Green
    } catch {
        Write-Host "⚠️ Erro ao inicializar banco: $($_.Exception.Message)" -ForegroundColor Yellow
    }
} else {
    Write-Host "⚠️ scripts/init_db.py não encontrado" -ForegroundColor Yellow
}

# === FASE 8: INICIAR SERVIDOR ===
Write-Host "`n============================================================" -ForegroundColor Magenta
Write-Host "Iniciando CryptoSDCA-AI" -ForegroundColor Magenta
Write-Host "============================================================" -ForegroundColor Magenta
Write-Host "🌐 Dashboard: http://127.0.0.1:8000" -ForegroundColor Green
Write-Host "📖 API Docs: http://127.0.0.1:8000/docs" -ForegroundColor Green
Write-Host "🔐 Login: http://127.0.0.1:8000/auth/login" -ForegroundColor Green
Write-Host "`n💡 Credenciais: admin / bot123" -ForegroundColor Yellow
Write-Host "🛑 Pressione Ctrl+C para parar" -ForegroundColor Yellow
Write-Host "============================================================" -ForegroundColor Magenta

# Iniciar servidor usando o python do ambiente
try {
    & $pythonExe -m uvicorn api.main:app --reload --host 127.0.0.1 --port 8000
} catch {
    Write-Host "`n❌ Erro ao iniciar servidor:" -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
    
    # Tentar diagnóstico
    Write-Host "`n🔍 Diagnóstico:" -ForegroundColor Yellow
    Write-Host "Python: $pythonExe" -ForegroundColor Gray
    Write-Host "PATH: $($env:PATH.Split(';')[0..2] -join ';')..." -ForegroundColor Gray
    
    pause
}

Write-Host "`nServidor encerrado." -ForegroundColor Yellow
