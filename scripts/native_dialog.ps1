[CmdletBinding()]
param(
    [ValidateSet("folder", "file")]
    [string]$Mode = "folder",
    [string]$InitialPath = "",
    [string]$Title = "Selecionar"
)

$ErrorActionPreference = "Stop"
Add-Type -AssemblyName System.Windows.Forms
[System.Windows.Forms.Application]::EnableVisualStyles()

if ($Mode -eq "folder") {
    $dialog = New-Object System.Windows.Forms.FolderBrowserDialog
    $dialog.Description = $Title
    $dialog.ShowNewFolderButton = $true
    if ($InitialPath -and (Test-Path $InitialPath -PathType Container)) { $dialog.SelectedPath = $InitialPath }
} else {
    $dialog = New-Object System.Windows.Forms.OpenFileDialog
    $dialog.Title = $Title
    $dialog.Filter = "Vídeos e transcrições|*.mp4;*.mkv;*.avi;*.mov;*.webm;*.flv;*.wmv;*.txt;*.srt;*.vtt|Todos os arquivos|*.*"
    $dialog.Multiselect = $false
    if ($InitialPath -and (Test-Path $InitialPath -PathType Container)) { $dialog.InitialDirectory = $InitialPath }
}

$result = $dialog.ShowDialog()
if ($result -eq [System.Windows.Forms.DialogResult]::OK) {
    if ($Mode -eq "folder") { Write-Output $dialog.SelectedPath }
    else { Write-Output $dialog.FileName }
}
