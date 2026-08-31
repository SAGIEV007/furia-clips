param(
    [Parameter(Mandatory = $false)]
    [string]$ProjectRoot = ""
)

$ErrorActionPreference = "Stop"

# Blindagem de caminho (bug real reportado 31/08).
#
# O run.bat passa -ProjectRoot "%~dp0". Quando a pasta do projeto contém
# caracteres não-ASCII (ex.: "C:\Users\nandi\OneDrive\Área de Trabalho\..."),
# o cmd.exe entrega o argumento no code page OEM e o PowerShell recebe o
# caminho CORROMPIDO ("Área" chega como "µrea"). O script então falhava com
# "Caracteres inválidos no caminho", nunca baixava o modelo facial, e como
# consequência TODOS os cortes saíam em 16:9 em vez de 9:16 (Instagram) —
# porque sem modelo facial o plan_layout devolve family=unknown e bloqueia o
# reframe vertical.
#
# $PSScriptRoot é resolvido pelo próprio PowerShell e por isso é imune a essa
# corrupção. Usamos o argumento apenas quando ele aponta para um caminho que
# realmente existe; caso contrário caímos no caminho derivado do script.
$scriptRoot = Split-Path -Parent $PSScriptRoot
if ([string]::IsNullOrWhiteSpace($ProjectRoot) -or -not (Test-Path -LiteralPath $ProjectRoot)) {
    $ProjectRoot = $scriptRoot
}

$modelRelativePath = "models\blaze_face_short_range.tflite"
$modelPath = Join-Path $ProjectRoot $modelRelativePath
$modelUrl = "https://storage.googleapis.com/mediapipe-models/face_detector/blaze_face_short_range/float16/1/blaze_face_short_range.tflite"
$expectedSha256 = "b4578f35940bf5a1a655214a1cce5cab13eba73c1297cd78e1a04c2380b0152f"
$logPath = Join-Path $ProjectRoot "logs\face-model-bootstrap.log"

function Write-ModelLog([string]$Message) {
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $line = "[$timestamp] $Message"
    Write-Host "[Face Model] $Message"
    try {
        $logDir = Split-Path -Parent $logPath
        if (-not (Test-Path $logDir)) { New-Item -ItemType Directory -Path $logDir -Force | Out-Null }
        Add-Content -LiteralPath $logPath -Value $line -Encoding UTF8
    } catch {
        # O modelo continua utilizável mesmo quando a pasta de logs não pode ser gravada.
    }
}

function Test-ModelHash([string]$Path) {
    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) { return $false }
    try {
        $actual = (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToLowerInvariant()
        return $actual -eq $expectedSha256
    } catch {
        return $false
    }
}

try {
    $modelDir = Split-Path -Parent $modelPath
    if (-not (Test-Path $modelDir)) { New-Item -ItemType Directory -Path $modelDir -Force | Out-Null }

    if (Test-ModelHash $modelPath) {
        Write-ModelLog "Modelo facial presente e íntegro: $modelRelativePath"
        exit 0
    }

    if (Test-Path -LiteralPath $modelPath -PathType Leaf) {
        Remove-Item -LiteralPath $modelPath -Force
        Write-ModelLog "Modelo facial existente estava inválido; será baixado novamente."
    }

    Write-ModelLog "Baixando modelo oficial do MediaPipe..."
    $temporaryPath = "$modelPath.download"
    if (Test-Path -LiteralPath $temporaryPath) { Remove-Item -LiteralPath $temporaryPath -Force }
    Invoke-WebRequest -Uri $modelUrl -OutFile $temporaryPath -UseBasicParsing

    if (-not (Test-ModelHash $temporaryPath)) {
        Remove-Item -LiteralPath $temporaryPath -Force -ErrorAction SilentlyContinue
        throw "SHA-256 do modelo baixado não corresponde ao esperado."
    }

    Move-Item -LiteralPath $temporaryPath -Destination $modelPath -Force
    Write-ModelLog "Modelo facial baixado e validado com sucesso."
    exit 0
} catch {
    Write-ModelLog "Não foi possível preparar o modelo facial: $($_.Exception.Message)"
    Write-ModelLog "O aplicativo continuará com composição original quando o facetracking não estiver disponível."
    exit 0
}
