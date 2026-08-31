param(
    [Parameter(Mandatory=$true)]
    [ValidatePattern('^[A-Za-z]:$')]
    [string]$Drive,

    [string]$OllamaBundle = ""
)

$ErrorActionPreference = 'Stop'
$driveLetter = $Drive.Substring(0,1).ToUpper()
$systemDrive = $env:SystemDrive.Substring(0,1).ToUpper()
if ($driveLetter -eq $systemDrive) {
    throw "Refusing to use the Windows system drive. Choose the removable QUANTIC-DATA volume."
}

$vol = Get-Volume -DriveLetter $driveLetter -ErrorAction Stop
if ($vol.DriveType -ne 'Removable') {
    throw "Refusing non-removable volume $Drive. Quantic persistence must live on removable USB media."
}
if ($vol.FileSystemLabel -ne 'QUANTIC-DATA') {
    throw "Volume label must already be QUANTIC-DATA. This script intentionally does not format or repartition disks."
}

$root = "$Drive\quantic-state"
$dirs = @(
    'models', 'models\ollama', 'memory', 'index', 'skills', 'connectors',
    'tasks', 'simulations', 'audit', 'vault', 'users'
)
foreach ($dir in $dirs) {
    New-Item -ItemType Directory -Force -Path (Join-Path $root $dir) | Out-Null
}

$manifest = @{
    schema = 1
    label = 'QUANTIC-DATA'
    created_utc = (Get-Date).ToUniversalTime().ToString('o')
    model_store = 'quantic-state/models/ollama'
    note = 'Prepared without formatting or repartitioning.'
} | ConvertTo-Json -Depth 4
Set-Content -Path (Join-Path $root 'quantic-data.json') -Value $manifest -Encoding UTF8

if ($OllamaBundle) {
    $src = (Resolve-Path $OllamaBundle).Path
    $dst = Join-Path $root 'models\ollama'
    Write-Host "Copying supplied Ollama model bundle to $dst"
    Copy-Item -Path (Join-Path $src '*') -Destination $dst -Recurse -Force
}

Write-Host "QUANTIC-DATA prepared safely on $Drive"
Write-Host "No disk was formatted or repartitioned."
Write-Host "Model store: $root\models\ollama"
