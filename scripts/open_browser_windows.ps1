[CmdletBinding()]
param(
    [string]$Url = "http://127.0.0.1:3001",
    [string]$LogFile = "",
    [int]$TimeoutSeconds = 120
)

$ErrorActionPreference = "Stop"
$utf8NoBom = New-Object System.Text.UTF8Encoding($false)

function Write-LogLine([string]$Message) {
    $stamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $line = "[$stamp] [Browser] $Message"
    Write-Output $line
    if ($LogFile) {
        $parent = Split-Path -Parent $LogFile
        if ($parent -and -not (Test-Path -LiteralPath $parent)) {
            New-Item -ItemType Directory -Path $parent -Force | Out-Null
        }
        [System.IO.File]::AppendAllText($LogFile, $line + [Environment]::NewLine, $utf8NoBom)
    }
}

function Test-Server([string]$TargetUrl) {
    try {
        $response = Invoke-WebRequest -Uri $TargetUrl -UseBasicParsing -TimeoutSec 3
        return ($response.StatusCode -ge 200 -and $response.StatusCode -lt 500)
    } catch {
        return $false
    }
}

function Add-ExecutableCandidate([System.Collections.Generic.List[string]]$List, [string]$Candidate) {
    if ([string]::IsNullOrWhiteSpace($Candidate)) { return }
    try {
        $expanded = [Environment]::ExpandEnvironmentVariables($Candidate.Trim().Trim('"'))
        if ((Test-Path -LiteralPath $expanded -PathType Leaf) -and -not $List.Contains($expanded)) {
            [void]$List.Add($expanded)
        }
    } catch {
        Write-LogLine "Caminho de navegador ignorado: $Candidate"
    }
}

function Get-RegistryExecutable([string]$RegistryPath) {
    try {
        $property = Get-ItemProperty -LiteralPath $RegistryPath -Name "(default)" -ErrorAction Stop
        $command = [string]$property."(default)"
        if ($command -match '^(?:"(?<quoted>[^"]+\.exe)"|(?<plain>[^\s]+\.exe))') {
            if ($Matches.quoted) { return $Matches.quoted }
            return $Matches.plain
        }
    } catch {
        return $null
    }
    return $null
}

$ready = $false
$attemptLimit = [Math]::Max(15, $TimeoutSeconds)
for ($attempt = 1; $attempt -le $attemptLimit; $attempt++) {
    if (Test-Server $Url) {
        $ready = $true
        Write-LogLine "Servidor respondeu na tentativa $attempt de ${attemptLimit}: $Url"
        break
    }
    Start-Sleep -Seconds 1
}

if (-not $ready) {
    Write-LogLine "Servidor não respondeu após $attemptLimit tentativas; nenhum navegador será acionado. URL: $Url"
    exit 2
}

$operaCandidates = New-Object 'System.Collections.Generic.List[string]'
$programFilesX86 = [Environment]::GetEnvironmentVariable("ProgramFiles(x86)")
$directCandidates = @(
    "$env:LOCALAPPDATA\Programs\Opera GX\launcher.exe",
    "$env:LOCALAPPDATA\Programs\Opera GX\opera.exe",
    "$env:APPDATA\Opera Software\Opera GX Stable\opera.exe",
    "$env:PROGRAMFILES\Opera GX\launcher.exe",
    "$env:PROGRAMFILES\Opera GX\opera.exe",
    "$programFilesX86\Opera GX\launcher.exe",
    "$programFilesX86\Opera GX\opera.exe"
)
foreach ($candidate in $directCandidates) {
    Add-ExecutableCandidate $operaCandidates $candidate
}

foreach ($commandName in @("opera.exe", "launcher.exe")) {
    try {
        $command = Get-Command $commandName -ErrorAction Stop
        if ($command.Source -match "(?i)Opera GX|Opera Software") {
            Add-ExecutableCandidate $operaCandidates $command.Source
        }
    } catch {
        # O executável não está no PATH; os caminhos conhecidos continuam válidos.
    }
}

foreach ($registryPath in @(
    "HKCU:\Software\Classes\http\shell\open\command",
    "HKCU:\Software\Classes\https\shell\open\command",
    "HKCU:\Software\Classes\Applications\launcher.exe\shell\open\command",
    "HKCU:\Software\Classes\Applications\opera.exe\shell\open\command"
)) {
    $registryExecutable = Get-RegistryExecutable $registryPath
    if ($registryExecutable -and $registryExecutable -match "(?i)Opera GX|Opera Software") {
        Add-ExecutableCandidate $operaCandidates $registryExecutable
    }
}

try {
    if ($operaCandidates.Count -gt 0) {
        $opera = $operaCandidates[0]
        Start-Process -FilePath $opera -ArgumentList @($Url) -WorkingDirectory (Split-Path -Parent $opera) | Out-Null
        Write-LogLine "Opera GX encontrado e acionado: $opera | URL: $Url"
        exit 0
    }

    Start-Process -FilePath $Url | Out-Null
    Write-LogLine "Opera GX não foi localizado nos caminhos conhecidos; URL aberta no navegador padrão do Windows: $Url"
    exit 0
} catch {
    Write-LogLine "Falha ao abrir navegador: $($_.Exception.Message)"
    exit 3
}
