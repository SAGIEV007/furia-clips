$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$RuntimeDir = Join-Path $Root ".runtime"
$LogDir = Join-Path $Root "logs"
$LogPath = Join-Path $LogDir "bootstrap-latest.log"
New-Item -ItemType Directory -Force -Path $RuntimeDir | Out-Null
New-Item -ItemType Directory -Force -Path $LogDir | Out-Null

$TranscriptStarted = $false
$ExitCode = 0

function Write-Status([string]$Message) {
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    Write-Host "[$timestamp] [Bootstrap] $Message"
}

function Write-Section([string]$Title) {
    Write-Host ""
    Write-Host ("=" * 72)
    Write-Status $Title
    Write-Host ("=" * 72)
}

function Find-Python {
    $candidates = New-Object System.Collections.Generic.List[string]

    foreach ($name in @("python.exe", "py.exe")) {
        try {
            $command = Get-Command $name -ErrorAction SilentlyContinue
            if ($command.Source -and ($command.Source -notmatch "WindowsApps")) {
                $candidates.Add($command.Source)
            }
        } catch { }
    }

    $roots = @(
        (Join-Path $env:LocalAppData "Programs\Python"),
        (Join-Path $env:LocalAppData "Python"),
        (Join-Path $env:ProgramFiles "Python312"),
        (Join-Path ${env:ProgramFiles(x86)} "Python312")
    )

    foreach ($root in $roots) {
        if (Test-Path $root) {
            try {
                Get-ChildItem -Path $root -Filter "python.exe" -File -Recurse -ErrorAction SilentlyContinue |
                    ForEach-Object { $candidates.Add($_.FullName) }
            } catch { }
        }
    }

    foreach ($candidate in ($candidates | Select-Object -Unique)) {
        try {
            $version = & $candidate -c "import sys; print(f'{sys.version_info[0]}.{sys.version_info[1]}')" 2>$null
            if ($LASTEXITCODE -eq 0 -and $version -match "^3\.(1[0-9])$") {
                Write-Status "Python compativel encontrado: $candidate (versao $version)"
                return $candidate
            }
        } catch { }
    }

    return $null
}

function Find-Binary([string]$Name) {
    try {
        $command = Get-Command $Name -ErrorAction SilentlyContinue
        if ($command.Source) { return $command.Source }
    } catch { }

    $roots = @(
        (Join-Path $env:LOCALAPPDATA "Microsoft\WinGet\Packages"),
        (Join-Path $env:LOCALAPPDATA "Programs"),
        (Join-Path $env:ProgramFiles "ffmpeg"),
        (Join-Path ${env:ProgramFiles(x86)} "ffmpeg")
    )

    foreach ($root in $roots) {
        if (Test-Path $root) {
            try {
                $found = Get-ChildItem -Path $root -Filter $Name -File -Recurse -ErrorAction SilentlyContinue | Select-Object -First 1
                if ($found) { return $found.FullName }
            } catch { }
        }
    }

    return $null
}

function Invoke-WingetInstall([string]$Id) {
    try {
        $winget = Get-Command winget.exe -ErrorAction Stop
        Write-Status "Instalando $Id via WinGet..."
        & $winget.Source install --id $Id --exact --silent --accept-source-agreements --accept-package-agreements --disable-interactivity
        $code = $LASTEXITCODE
        Write-Status "WinGet terminou para $Id com codigo $code."
        return ($code -eq 0)
    } catch {
        Write-Status "WinGet indisponivel ou falhou para ${Id}: $($_.Exception.Message)"
        return $false
    }
}

function Ensure-Python {
    Write-Section "Etapa 1/2 - verificando Python"
    $python = Find-Python
    if ($python) { return $python }

    Write-Status "Python 3.10+ nao foi encontrado. Iniciando instalacao automatica."
    if (Invoke-WingetInstall "Python.Python.3.12") {
        Start-Sleep -Seconds 2
        $python = Find-Python
        if ($python) { return $python }
        Write-Status "WinGet concluiu, mas o executavel ainda nao apareceu; tentando o fallback oficial."
    }

    $installer = Join-Path $RuntimeDir "python-3.12.10-amd64.exe"
    Write-Status "Baixando o instalador oficial do Python 3.12 para: $installer"
    Invoke-WebRequest -UseBasicParsing -Uri "https://www.python.org/ftp/python/3.12.10/python-3.12.10-amd64.exe" -OutFile $installer
    Write-Status "Instalando Python para o usuario atual com PATH habilitado."
    $process = Start-Process -FilePath $installer -ArgumentList @("/quiet", "InstallAllUsers=0", "PrependPath=1", "Include_test=0") -Wait -PassThru
    Write-Status "Instalador do Python terminou com codigo $($process.ExitCode)."
    if ($process.ExitCode -ne 0) { throw "O instalador do Python retornou o codigo $($process.ExitCode)." }

    Start-Sleep -Seconds 2
    $python = Find-Python
    if (-not $python) { throw "Python foi instalado, mas o executavel nao pode ser localizado." }
    return $python
}

function Ensure-FFmpeg {
    Write-Section "Etapa 2/2 - verificando FFmpeg e ffprobe"
    $ffmpeg = Find-Binary "ffmpeg.exe"
    $ffprobe = Find-Binary "ffprobe.exe"
    if ($ffmpeg -and $ffprobe) {
        Write-Status "FFmpeg encontrado: $ffmpeg"
        Write-Status "ffprobe encontrado: $ffprobe"
        return @{
            ffmpeg = Split-Path -Parent $ffmpeg
            ffprobe = $ffprobe
        }
    }

    Write-Status "FFmpeg ou ffprobe nao foi encontrado. Iniciando instalacao automatica."
    if (Invoke-WingetInstall "Gyan.FFmpeg") {
        Start-Sleep -Seconds 2
        $ffmpeg = Find-Binary "ffmpeg.exe"
        $ffprobe = Find-Binary "ffprobe.exe"
        if ($ffmpeg -and $ffprobe) {
            Write-Status "FFmpeg instalado: $ffmpeg"
            Write-Status "ffprobe instalado: $ffprobe"
            return @{
                ffmpeg = $ffmpeg
                ffprobe = $ffprobe
            }
        }
        Write-Status "WinGet concluiu, mas os executaveis ainda nao foram localizados; tentando o fallback."
    }

    $archive = Join-Path $RuntimeDir "ffmpeg-release-essentials.zip"
    $extract = Join-Path $RuntimeDir "ffmpeg"
    Write-Status "Baixando build Windows de FFmpeg para: $archive"
    Invoke-WebRequest -UseBasicParsing -Uri "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip" -OutFile $archive
    if (Test-Path $extract) { Remove-Item -Recurse -Force $extract }
    Write-Status "Extraindo FFmpeg para: $extract"
    Expand-Archive -Path $archive -DestinationPath $extract -Force

    $ffmpeg = Get-ChildItem -Path $extract -Filter "ffmpeg.exe" -File -Recurse | Select-Object -First 1
    $ffprobe = Get-ChildItem -Path $extract -Filter "ffprobe.exe" -File -Recurse | Select-Object -First 1
    if (-not $ffmpeg -or -not $ffprobe) { throw "O pacote baixado nao contem ffmpeg.exe e ffprobe.exe." }
    Write-Status "FFmpeg pronto: $($ffmpeg.FullName)"
    Write-Status "ffprobe pronto: $($ffprobe.FullName)"
    return @{
        ffmpeg = Split-Path -Parent $ffmpeg.FullName
        ffprobe = $ffprobe.FullName
    }
}

try {
    Start-Transcript -Path $LogPath -Force | Out-Null
    $TranscriptStarted = $true
    Write-Section "Furia Clips - bootstrap automatico do Windows"
    Write-Status "Pasta do projeto: $Root"
    Write-Status "Log detalhado: $LogPath"

    $pythonPath = Ensure-Python
    $ffmpegDir = Ensure-FFmpeg

    # File.WriteAllText com UTF-8 sem BOM evita que o for /f do CMD leia o BOM
    # como parte do primeiro caractere do caminho executavel.
    $utf8NoBom = New-Object System.Text.UTF8Encoding($false)
    [System.IO.File]::WriteAllText((Join-Path $RuntimeDir "python_path.txt"), [string]$pythonPath, $utf8NoBom)
    [System.IO.File]::WriteAllText((Join-Path $RuntimeDir "ffmpeg_path.txt"), [string]$ffmpegDir.ffmpeg, $utf8NoBom)
    [System.IO.File]::WriteAllText((Join-Path $RuntimeDir "ffprobe_path.txt"), [string]$ffmpegDir.ffprobe, $utf8NoBom)

    Write-Status "Python pronto: $pythonPath"
    Write-Status "FFmpeg pronto: $($ffmpegDir.ffmpeg)"
    Write-Status "ffprobe pronto: $($ffmpegDir.ffprobe)"
    Write-Status "Dependencias de sistema concluidas."
} catch {
    $ExitCode = 1
    Write-Host ""
    Write-Host ("!" * 72) -ForegroundColor Red
    Write-Host "[ERRO] Bootstrap automatico falhou." -ForegroundColor Red
    Write-Host "[ERRO] Mensagem: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host "[ERRO] Tipo: $($_.Exception.GetType().FullName)" -ForegroundColor Red
    if ($_.InvocationInfo) {
        Write-Host "[ERRO] Linha: $($_.InvocationInfo.ScriptLineNumber)" -ForegroundColor Red
        Write-Host "[ERRO] Comando: $($_.InvocationInfo.Line.Trim())" -ForegroundColor Red
    }
    Write-Host "[ERRO] Log completo: $LogPath" -ForegroundColor Red
    Write-Host ("!" * 72) -ForegroundColor Red
} finally {
    if ($TranscriptStarted) {
        # O Stop-Transcript imprime uma confirmação localizada (por exemplo,
        # “Transcrição interrompida...”) que parece erro no console do .bat.
        # O log já foi gravado; suprima somente essa saída redundante.
        Stop-Transcript | Out-Null
    }
}

exit $ExitCode
