param(
    [string]$PythonExe = ".\venv\Scripts\python.exe"
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path $PythonExe)) {
    Write-Error "Python executable niet gevonden: $PythonExe"
}

& $PythonExe -m pip install -r requirements.txt
& $PythonExe .\app_flet.py
