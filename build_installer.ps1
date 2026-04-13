$ErrorActionPreference = 'Stop'

Set-Location $PSScriptRoot

if (-not (Test-Path '.\dist\PlayOnThere\PlayOnThere.exe')) {
    throw 'No existe el build portable en dist\PlayOnThere\PlayOnThere.exe. Ejecuta antes build_dist.ps1.'
}

if (Test-Path '.\installer') {
    Remove-Item '.\installer' -Recurse -Force
}

$candidates = @(
    'C:\Program Files (x86)\Inno Setup 6\ISCC.exe',
    'C:\Program Files\Inno Setup 6\ISCC.exe',
    "$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe"
)

$iscc = $candidates | Where-Object { Test-Path $_ } | Select-Object -First 1

if (-not (Test-Path $iscc)) {
    throw 'No se encontró ISCC.exe de Inno Setup.'
}

& $iscc '.\PlayOnThere.iss'

Write-Host ''
Write-Host 'Instalador generado en installer\PlayOnThere-Setup.exe'