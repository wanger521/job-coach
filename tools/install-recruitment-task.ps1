[CmdletBinding()]
param([switch]$Remove)
$ErrorActionPreference = 'Stop'
$repo = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path
# Scope the task name to this checkout so another copy of the app is independent.
$sha = [System.Security.Cryptography.SHA256]::Create()
try { $digest = $sha.ComputeHash([Text.Encoding]::UTF8.GetBytes($repo.ToLowerInvariant())) } finally { $sha.Dispose() }
$name = 'CareerAtlas-Recruitment-' + [BitConverter]::ToString($digest,0,5).Replace('-','')
if ($Remove) {
    Unregister-ScheduledTask -TaskName $name -Confirm:$false
    return
}
$python = (& python -c 'import sys; print(sys.executable)').Trim()
if ($LASTEXITCODE -ne 0 -or -not (Test-Path -LiteralPath $python -PathType Leaf)) { throw 'Python 3.10+ required' }
# pythonw avoids flashing a console on the desktop during a scheduled run.
$pythonw = Join-Path (Split-Path -Parent $python) 'pythonw.exe'
if (Test-Path -LiteralPath $pythonw) { $python = $pythonw }
$action = New-ScheduledTaskAction -Execute $python -Argument ('-X utf8 "' + (Join-Path $repo 'tools\update_recruitment.py') + '" --scheduled') -WorkingDirectory $repo
$trigger = New-ScheduledTaskTrigger -Daily -At '08:30'
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -MultipleInstances IgnoreNew -ExecutionTimeLimit (New-TimeSpan -Minutes 45)
$user = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name
$principal = New-ScheduledTaskPrincipal -UserId $user -LogonType Interactive -RunLevel Limited
Register-ScheduledTask -TaskName $name -Description 'Update public job and school notices using the local Career Atlas script.' -Action $action -Trigger $trigger -Settings $settings -Principal $principal -Force | Out-Null
Get-ScheduledTaskInfo -TaskName $name | Select-Object TaskName,NextRunTime,LastTaskResult
