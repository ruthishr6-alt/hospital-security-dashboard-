Write-Host "=========================================================================" -ForegroundColor Cyan
Write-Host "   CRITICAL HEART PATIENT CYBER SECURITY SYSTEM" -ForegroundColor White
Write-Host "   Starting Flask Cyber-Defense Server..." -ForegroundColor Green
Write-Host "=========================================================================" -ForegroundColor Cyan

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

if (Test-Path "$scriptDir\python.bat") {
    & "$scriptDir\python.bat" "$scriptDir\app.py"
} else {
    python "$scriptDir\app.py"
}
