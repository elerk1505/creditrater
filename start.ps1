$ErrorActionPreference = "Stop"

# Locate repo root
$HERE = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $HERE

Write-Host "Starting CreditRater (auto-clean backend)…"

# Kill anything on 5051
try {
    $conns = Get-NetTCPConnection -LocalPort 5051 -State Listen -ErrorAction SilentlyContinue
    if ($conns) {
        foreach ($c in $conns) {
            $pid = $c.OwningProcess
            if ($pid) {
                Write-Host "Killing existing backend on port 5051 (PID: $pid)…"
                Stop-Process -Id $pid -Force -ErrorAction SilentlyContinue
            }
        }
        Start-Sleep -Milliseconds 500
    }
} catch { }

# Setup venv & deps
Set-Location "$HERE\backend"
if (!(Test-Path ".venv")) {
    Write-Host "Creating Python venv…"
    python -m venv .venv
}
& ".\.venv\Scripts\Activate.ps1"

Write-Host "Installing/validating Python dependencies…"
python -m pip install --upgrade pip | Out-Null
pip install -r requirements.txt | Out-Null

# Launch backend (non-blocking)
Write-Host "Launching backend on http://127.0.0.1:5051 …"
Start-Process -NoNewWindow -FilePath "python" -ArgumentList "-m","uvicorn","server:app","--host","127.0.0.1","--port","5051","--reload"

Start-Sleep -Seconds 1
Start-Process "http://127.0.0.1:5051/app"

Write-Host "If the browser doesn't open, visit http://127.0.0.1:5051/app"
