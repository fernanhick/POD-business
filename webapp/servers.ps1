param(
    [Parameter(Mandatory = $true)]
    [ValidateSet("start", "stop", "status")]
    [string]$Action
)

$ErrorActionPreference = "Stop"

$Root = $PSScriptRoot
$BackendDir = Join-Path $Root "backend"
$FrontendDir = Join-Path $Root "frontend"
$BackendPython = Join-Path $BackendDir ".venv313\Scripts\python.exe"

$RuntimeDir = Join-Path $Root ".runtime"
$BackendPidFile = Join-Path $RuntimeDir "backend.pid"
$FrontendPidFile = Join-Path $RuntimeDir "frontend.pid"
$BackendLog = Join-Path $RuntimeDir "backend.out.log"
$BackendErrLog = Join-Path $RuntimeDir "backend.err.log"
$FrontendLog = Join-Path $RuntimeDir "frontend.out.log"
$FrontendErrLog = Join-Path $RuntimeDir "frontend.err.log"

function Ensure-RuntimeDir {
    if (-not (Test-Path $RuntimeDir)) {
        New-Item -Path $RuntimeDir -ItemType Directory | Out-Null
    }
}

function Read-Pid([string]$pidFile) {
    if (-not (Test-Path $pidFile)) {
        return $null
    }

    $raw = (Get-Content $pidFile -ErrorAction SilentlyContinue | Select-Object -First 1).Trim()
    if (-not $raw) {
        return $null
    }

    [int]$procId = 0
    if ([int]::TryParse($raw, [ref]$procId)) {
        return $procId
    }

    return $null
}

function Write-Pid([string]$pidFile, [int]$procId) {
    Set-Content -Path $pidFile -Value $procId -Encoding ascii
}

function Remove-Pid([string]$pidFile) {
    if (Test-Path $pidFile) {
        Remove-Item $pidFile -Force
    }
}

function Is-ProcessRunning([int]$procId) {
    if (-not $procId) {
        return $false
    }

    $process = Get-Process -Id $procId -ErrorAction SilentlyContinue
    return $null -ne $process
}

function Test-Url([string]$url) {
    try {
        $response = Invoke-WebRequest -UseBasicParsing -Uri $url -TimeoutSec 2
        return $response.StatusCode -ge 200
    }
    catch {
        return $false
    }
}

function Get-LanIPv4 {
    try {
        $ips = [System.Net.Dns]::GetHostAddresses([System.Net.Dns]::GetHostName()) |
            Where-Object {
                $_.AddressFamily -eq [System.Net.Sockets.AddressFamily]::InterNetwork -and
                -not $_.IPAddressToString.StartsWith("127.") -and
                -not $_.IPAddressToString.StartsWith("169.254.")
            }
        if ($ips -and $ips.Count -gt 0) {
            return $ips[0].IPAddressToString
        }
    }
    catch {
    }
    return $null
}

function Start-Backend {
    if (-not (Test-Path $BackendPython)) {
        throw "Backend Python not found at $BackendPython. Create it with: py -3.13 -m venv webapp\\backend\\.venv313"
    }

    $existingPid = Read-Pid $BackendPidFile
    if ($existingPid -and (Is-ProcessRunning $existingPid)) {
        Write-Output "Backend already running (PID $existingPid) at http://127.0.0.1:8000"
        return
    }

    if (Test-Url "http://127.0.0.1:8000/docs") {
        Write-Output "Backend appears to already be running on http://127.0.0.1:8000 (no managed PID)."
        return
    }

    $proc = Start-Process -FilePath $BackendPython `
        -ArgumentList "-m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload" `
        -WorkingDirectory $BackendDir `
        -RedirectStandardOutput $BackendLog `
        -RedirectStandardError $BackendErrLog `
        -WindowStyle Hidden `
        -PassThru

    Write-Pid $BackendPidFile $proc.Id
    Start-Sleep -Seconds 2
    if (Is-ProcessRunning $proc.Id) {
        $lanIp = Get-LanIPv4
        if ($lanIp) {
            Write-Output "Backend started (PID $($proc.Id)) at http://127.0.0.1:8000 and http://$lanIp`:8000"
        }
        else {
            Write-Output "Backend started (PID $($proc.Id)) at http://127.0.0.1:8000"
        }
    }
    else {
        Remove-Pid $BackendPidFile
        throw "Backend process exited immediately. Check log: $BackendLog"
    }
}

function Start-Frontend {
    $existingPid = Read-Pid $FrontendPidFile
    if ($existingPid -and (Is-ProcessRunning $existingPid)) {
        Write-Output "Frontend already running (PID $existingPid) at http://127.0.0.1:5173"
        return
    }

    if (Test-Url "http://127.0.0.1:5173") {
        Write-Output "Frontend appears to already be running on http://127.0.0.1:5173 (no managed PID)."
        return
    }

    $npmCmd = "npm run dev -- --host 0.0.0.0 --port 5173"
    $proc = Start-Process -FilePath "powershell.exe" `
        -ArgumentList "-NoProfile -ExecutionPolicy Bypass -Command $npmCmd" `
        -WorkingDirectory $FrontendDir `
        -RedirectStandardOutput $FrontendLog `
        -RedirectStandardError $FrontendErrLog `
        -WindowStyle Hidden `
        -PassThru

    Write-Pid $FrontendPidFile $proc.Id
    Start-Sleep -Seconds 2
    if (Is-ProcessRunning $proc.Id) {
        $lanIp = Get-LanIPv4
        if ($lanIp) {
            Write-Output "Frontend started (PID $($proc.Id)) at http://127.0.0.1:5173 and http://$lanIp`:5173"
        }
        else {
            Write-Output "Frontend started (PID $($proc.Id)) at http://127.0.0.1:5173"
        }
    }
    else {
        Remove-Pid $FrontendPidFile
        throw "Frontend process exited immediately. Check log: $FrontendLog"
    }
}

function Stop-Service([string]$name, [string]$pidFile) {
    $procId = Read-Pid $pidFile
    if (-not $procId) {
        Write-Output "$name is not running (no PID file)."
        return
    }

    if (Is-ProcessRunning $procId) {
        Stop-Process -Id $procId -Force
        Write-Output "$name stopped (PID $procId)."
    }
    else {
        Write-Output "$name already stopped (stale PID $procId)."
    }

    Remove-Pid $pidFile
}

function Show-Status {
    $backendPid = Read-Pid $BackendPidFile
    $frontendPid = Read-Pid $FrontendPidFile

    $backendRunning = $backendPid -and (Is-ProcessRunning $backendPid)
    $frontendRunning = $frontendPid -and (Is-ProcessRunning $frontendPid)

    $lanIp = Get-LanIPv4
    $backendLanUrl = if ($lanIp) { " (LAN: http://$lanIp`:8000)" } else { "" }
    $frontendLanUrl = if ($lanIp) { " (LAN: http://$lanIp`:5173)" } else { "" }

    if ($backendRunning) {
        Write-Output "Backend: running (PID $backendPid) -> http://127.0.0.1:8000$backendLanUrl"
    }
    elseif (Test-Url "http://127.0.0.1:8000/docs") {
        Write-Output "Backend: running (unmanaged PID) -> http://127.0.0.1:8000$backendLanUrl"
    }
    else {
        Write-Output "Backend: stopped"
    }

    if ($frontendRunning) {
        Write-Output "Frontend: running (PID $frontendPid) -> http://127.0.0.1:5173$frontendLanUrl"
    }
    elseif (Test-Url "http://127.0.0.1:5173") {
        Write-Output "Frontend: running (unmanaged PID) -> http://127.0.0.1:5173$frontendLanUrl"
    }
    else {
        Write-Output "Frontend: stopped"
    }
}

Ensure-RuntimeDir

switch ($Action) {
    "start" {
        Start-Backend
        Start-Frontend
    }
    "stop" {
        Stop-Service -name "Backend" -pidFile $BackendPidFile
        Stop-Service -name "Frontend" -pidFile $FrontendPidFile
    }
    "status" {
        Show-Status
    }
}