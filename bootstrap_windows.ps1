$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$RuntimeDir = Join-Path $Root ".runtime"
New-Item -ItemType Directory -Force -Path $RuntimeDir | Out-Null

function Write-Status([string]$Message) {
    Write-Host "[Bootstrap] $Message"
}

function Find-Python {
    $candidates = New-Object System.Collections.Generic.List[string]

    foreach ($name in @("python.exe", "py.exe")) {
        try {
            $command = Get-Command $name -ErrorAction Stop
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
                return $candidate
            }
        } catch { }
    }

    return $null
}

function Find-Binary([string]$Name) {
    try {
        $command = Get-Command $Name -ErrorAction Stop
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
        return ($LASTEXITCODE -eq 0)
    } catch {
        Write-Status "WinGet indisponível ou falhou para $Id. Usando fallback oficial."
        return $false
    }
}

function Ensure-Python {
    $python = Find-Python
    if ($python) { return $python }

    if (Invoke-WingetInstall "Python.Python.3.12") {
        Start-Sleep -Seconds 2
        $python = Find-Python
        if ($python) { return $python }
    }

    $installer = Join-Path $RuntimeDir "python-3.12.10-amd64.exe"
    Write-Status "Baixando o instalador oficial do Python 3.12..."
    Invoke-WebRequest -UseBasicParsing -Uri "https://www.python.org/ftp/python/3.12.10/python-3.12.10-amd64.exe" -OutFile $installer
    Write-Status "Instalando Python para o usuário atual..."
    $process = Start-Process -FilePath $installer -ArgumentList @("/quiet", "InstallAllUsers=0", "PrependPath=1", "Include_test=0") -Wait -PassThru
    if ($process.ExitCode -ne 0) { throw "O instalador do Python retornou o código $($process.ExitCode)." }

    Start-Sleep -Seconds 2
    $python = Find-Python
    if (-not $python) { throw "Python foi instalado, mas o executável não pôde ser localizado." }
    return $python
}

function Ensure-FFmpeg {
    $ffmpeg = Find-Binary "ffmpeg.exe"
    $ffprobe = Find-Binary "ffprobe.exe"
    if ($ffmpeg -and $ffprobe) { return (Split-Path -Parent $ffmpeg) }

    if (Invoke-WingetInstall "Gyan.FFmpeg") {
        Start-Sleep -Seconds 2
        $ffmpeg = Find-Binary "ffmpeg.exe"
        $ffprobe = Find-Binary "ffprobe.exe"
        if ($ffmpeg -and $ffprobe) { return (Split-Path -Parent $ffmpeg) }
    }

    $archive = Join-Path $RuntimeDir "ffmpeg-release-essentials.zip"
    $extract = Join-Path $RuntimeDir "ffmpeg"
    Write-Status "Baixando um build oficial para Windows referenciado pelo projeto FFmpeg..."
    Invoke-WebRequest -UseBasicParsing -Uri "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip" -OutFile $archive
    if (Test-Path $extract) { Remove-Item -Recurse -Force $extract }
    Expand-Archive -Path $archive -DestinationPath $extract -Force

    $ffmpeg = Get-ChildItem -Path $extract -Filter "ffmpeg.exe" -File -Recurse | Select-Object -First 1
    $ffprobe = Get-ChildItem -Path $extract -Filter "ffprobe.exe" -File -Recurse | Select-Object -First 1
    if (-not $ffmpeg -or -not $ffprobe) { throw "O pacote baixado não contém ffmpeg.exe e ffprobe.exe." }
    return (Split-Path -Parent $ffmpeg.FullName)
}

try {
    $pythonPath = Ensure-Python
    $ffmpegDir = Ensure-FFmpeg

    Set-Content -Path (Join-Path $RuntimeDir "python_path.txt") -Value $pythonPath -Encoding UTF8
    Set-Content -Path (Join-Path $RuntimeDir "ffmpeg_path.txt") -Value $ffmpegDir -Encoding UTF8

    Write-Status "Python pronto: $pythonPath"
    Write-Status "FFmpeg pronto: $ffmpegDir"
    Write-Status "Dependências de sistema concluídas."
    exit 0
} catch {
    Write-Host "[ERRO] Bootstrap automático falhou: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}
