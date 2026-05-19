param(
    [string]$FletExe = ".\venv\Scripts\flet.exe"
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path $FletExe)) {
    Write-Error "Flet executable niet gevonden: $FletExe"
}

& ".\venv\Scripts\python.exe" -m pip install -r requirements.txt

# '--yes' accepteert install prompts voor Android toolchain dependencies.
& $FletExe build apk . --module-name app_flet --project dakinspecties --product "Dakinspecties" --org "nl.dakinspecties" --yes

Write-Host "APK build voltooid. Controleer de build output map voor het .apk bestand." -ForegroundColor Green
