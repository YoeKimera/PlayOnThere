$ErrorActionPreference = 'Stop'

Set-Location $PSScriptRoot

if (Test-Path '.\build') {
    Remove-Item '.\build' -Recurse -Force
}

if (Test-Path '.\dist\PlayOnThere') {
    Remove-Item '.\dist\PlayOnThere' -Recurse -Force
}

if (Test-Path '.\dist\PlayOnThere.exe') {
    Remove-Item '.\dist\PlayOnThere.exe' -Force
}

if (Test-Path '.\dist\PlayOnThere-portable.zip') {
    Remove-Item '.\dist\PlayOnThere-portable.zip' -Force
}

if (Test-Path '.\build\portable-stage') {
    Remove-Item '.\build\portable-stage' -Recurse -Force
}

& '.\.venv\Scripts\pyinstaller.exe' --noconfirm '.\PlayOnThere.spec'

New-Item -ItemType Directory -Path '.\build\portable-stage' | Out-Null
Copy-Item '.\dist\PlayOnThere\*' '.\build\portable-stage' -Recurse
Compress-Archive -Path '.\build\portable-stage\*' -DestinationPath '.\dist\PlayOnThere-portable.zip'
Remove-Item '.\build\portable-stage' -Recurse -Force

Write-Host ''
Write-Host 'Build portable generado en dist\PlayOnThere\PlayOnThere.exe'
Write-Host 'ZIP portable generado en dist\PlayOnThere-portable.zip'