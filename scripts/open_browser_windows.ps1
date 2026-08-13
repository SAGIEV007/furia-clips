[CmdletBinding()]
param(
    [string]$Url = "http://127.0.0.1:3001",
    [string]$LogFile = ""
)

$ErrorActionPreference = "Stop"
$utf8NoBom = New-Object System.Text.UTF8Encoding($false)

function Write-LogLine([string]$Message) {
    $stamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $line = "[$stamp] [Browser] $Message"
    Write-Output $line
    if ($LogFile) {
        $parent = Split-Path -Parent $LogFile
        if ($parent -and -not (Test-Path $parent)) { New-Item -ItemType Directory -Path $parent -Force | Out-Null }
        [System.IO.File]::AppendAllText($LogFile, $line + [Environment]::NewLine, $utf8NoBom)
    }
}

function Test-Server([string]$TargetUrl) {
    try {
        $response = Invoke-WebRequest -Uri $TargetUrl -UseBasicParsing -TimeoutSec 2
        return ($response.StatusCode -ge 200 -and $response.StatusCode -lt 500)
    } catch {
        return $false
    }
}

$ready = $false
for ($attempt = 1; $attempt -le 60; $attempt++) {
    if (Test-Server $Url) {
        $ready = $true
        Write-LogLine "Servidor respondeu na tentativa $attempt: $Url"
        break
    }
    Start-Sleep -Seconds 1
}

if (-not $ready) {
    Write-LogLine "Servidor não respondeu após 60 tentativas; não abrirei uma aba falsa. URL: $Url"
    exit 2
}

$operaCandidates = @(
    "$env:LOCALAPPDATA\Programs\Opera GX\opera.exe",
    "$env:LOCALAPPDATA\Programs\Opera GX\launcher.exe",
    "$env:PROGRAMFILES\Opera GX\opera.exe",
    "$env:PROGRAMFILES\Opera GX\launcher.exe",
    "$env:PROGRAMFILES(X86)\Opera GX\opera.exe",
    "$env:PROGRAMFILES(X86)\Opera GX\launcher.exe"
) | Where-Object { $_ -and (Test-Path $_) } | Select-Object -Unique

try {
    if ($operaCandidates.Count -gt 0) {
        $opera = $operaCandidates[0]
        Start-Process -FilePath $opera -ArgumentList @("--new-tab", $Url)
        Write-LogLine "Opera GX encontrado e acionado: $opera"
        exit 0
    }

    Start-Process $Url
    Write-LogLine "Opera GX não encontrado; URL aberta no navegador padrão do Windows."
    exit 0
} catch {
    Write-LogLine "Falha ao abrir navegador: $($_.Exception.Message)"
    exit 3
}
