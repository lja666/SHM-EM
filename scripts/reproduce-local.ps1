param(
  [string]$MySqlExe = "mysql",
  [string]$HostName = "127.0.0.1",
  [int]$Port = 3306,
  [string]$AdminUser = "root",
  [string]$AdminPassword = $env:DB_ADMIN_PASSWORD,
  [string]$AppUser = "shm_em_reproduce",
  [string]$AppPassword = $env:MYSQL_PASSWORD,
  [string]$DataSqlPath = $env:SHM_EM_RESTRICTED_DATA_SQL,
  [string]$ConversionSqlPath = $env:SHM_EM_RESTRICTED_CONVERSION_SQL,
  [string]$ValidationSqlPath = $env:SHM_EM_RESTRICTED_VALIDATION_SQL,
  [string]$Database = "shm_em_reproduce_local",
  [string]$PythonExe = "python",
  [string]$MavenExe = "mvn",
  [string]$NpmExe = "npm",
  [string]$JavaExe = "java",
  [string]$ProjectCode = "SHM_EM_PUBLIC_SAMPLE",
  [int]$BackendPort = 5111,
  [string]$ResultPath = "",
  [switch]$ForceReset,
  [switch]$SkipDependencyInstall,
  [switch]$SkipBuildChecks,
  [switch]$KeepBuildOutputs
)

$ErrorActionPreference = "Stop"
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$BackendRoot = Join-Path $RepoRoot "src\backend"
$FrontendRoot = Join-Path $RepoRoot "src\frontend"
$PredictionRoot = Join-Path $RepoRoot "src\pit_pre"
$BaseUrl = "http://127.0.0.1:$BackendPort"
$ResultPath = if ([string]::IsNullOrWhiteSpace($ResultPath)) {
  Join-Path $RepoRoot "artifacts\reproduction-windows.json"
} elseif ([IO.Path]::IsPathRooted($ResultPath)) {
  [IO.Path]::GetFullPath($ResultPath)
} else {
  [IO.Path]::GetFullPath((Join-Path $RepoRoot $ResultPath))
}
$BackendProcess = $null
$RuntimeRoot = Join-Path ([IO.Path]::GetTempPath()) ("shm-em-reproduce-" + [Guid]::NewGuid().ToString("N"))
$EnvironmentKeys = @(
  "DB_URL", "DB_USERNAME", "DB_PASSWORD", "SERVER_PORT", "SPRING_PROFILES_ACTIVE",
  "SHM_EM_NOTIFICATION_SCHEDULER_ENABLED", "SHM_EM_NOTIFICATION_MAIL_SEND_ENABLED",
  "SHM_EM_RESPONSE_AUTOMATION_ENABLED", "SHM_EM_REPORT_OUTPUT_DIR"
)
$PreviousEnvironment = @{}

function Resolve-Executable {
  param([string]$Command, [string]$Label)
  if (Test-Path -LiteralPath $Command) {
    return (Resolve-Path -LiteralPath $Command).Path
  }
  $resolved = Get-Command $Command -ErrorAction SilentlyContinue
  if (-not $resolved) {
    throw "$Label executable was not found: $Command"
  }
  return $resolved.Source
}

function Invoke-Checked {
  param([string]$FilePath, [string[]]$Arguments)
  & $FilePath @Arguments
  if ($LASTEXITCODE -ne 0) {
    throw "Command failed with exit code ${LASTEXITCODE}: $FilePath $($Arguments -join ' ')"
  }
}

function Remove-ReleaseBuildOutputs {
  foreach ($path in @((Join-Path $BackendRoot "target"), (Join-Path $FrontendRoot "dist"))) {
    $full = [IO.Path]::GetFullPath($path)
    if (Test-Path -LiteralPath $full) {
      if (-not $full.StartsWith($RepoRoot + [IO.Path]::DirectorySeparatorChar, [StringComparison]::OrdinalIgnoreCase)) {
        throw "Refusing to remove build output outside the repository: $full"
      }
      [IO.Directory]::Delete($full, $true)
    }
  }
  Get-ChildItem -LiteralPath $PredictionRoot -Directory -Filter "__pycache__" -Recurse -Force -ErrorAction SilentlyContinue | ForEach-Object {
    $full = [IO.Path]::GetFullPath($_.FullName)
    if ($full.StartsWith($PredictionRoot + [IO.Path]::DirectorySeparatorChar, [StringComparison]::OrdinalIgnoreCase)) {
      [IO.Directory]::Delete($full, $true)
    }
  }
}

if ($Database -notmatch '^shm_em_reproduce_[A-Za-z0-9_]+$') {
  throw "Local reproduction requires an isolated shm_em_reproduce_* database."
}
if ([string]::IsNullOrWhiteSpace($AdminPassword)) {
  throw "Set DB_ADMIN_PASSWORD or pass -AdminPassword."
}
if ([string]::IsNullOrWhiteSpace($AppPassword)) {
  throw "Set MYSQL_PASSWORD or pass -AppPassword."
}

$MySqlExe = Resolve-Executable $MySqlExe "MySQL client"
$PythonExe = Resolve-Executable $PythonExe "Python"
$MavenExe = Resolve-Executable $MavenExe "Maven"
$NpmExe = Resolve-Executable $NpmExe "npm"
$JavaExe = Resolve-Executable $JavaExe "Java"

$PythonVersion = (& $PythonExe --version 2>&1 | Out-String).Trim()
if ($PythonVersion -notmatch '^Python 3\.10(\.|$)') {
  throw "PIT_PRE requires Python 3.10; found $PythonVersion."
}
Invoke-Checked $MavenExe @("--version")
Invoke-Checked $NpmExe @("--version")
Invoke-Checked $JavaExe @("-version")

$PortBusy = Get-NetTCPConnection -LocalPort $BackendPort -State Listen -ErrorAction SilentlyContinue
if ($PortBusy) {
  throw "Backend port $BackendPort is already in use. Pass a different -BackendPort."
}

New-Item -ItemType Directory -Force -Path $RuntimeRoot | Out-Null
try {
  & (Join-Path $PSScriptRoot "init-mysql.ps1") -MySqlExe $MySqlExe -HostName $HostName -Port $Port `
    -User $AdminUser -Password $AdminPassword -Database $Database -AppUser $AppUser `
    -AppPassword $AppPassword -DataSqlPath $DataSqlPath -ConversionSqlPath $ConversionSqlPath `
    -ValidationSqlPath $ValidationSqlPath -ForceReset:$ForceReset

  if (-not $SkipDependencyInstall) {
    Push-Location $PredictionRoot
    try { Invoke-Checked $PythonExe @("-m", "pip", "install", "-r", "requirements.lock.txt") } finally { Pop-Location }
    Push-Location $FrontendRoot
    try { Invoke-Checked $NpmExe @("ci") } finally { Pop-Location }
  }

  if (-not $SkipBuildChecks) {
    Push-Location $PredictionRoot
    try { Invoke-Checked $PythonExe @("-m", "unittest", "discover", "-s", "tests", "-v") } finally { Pop-Location }
    Push-Location $BackendRoot
    try { Invoke-Checked $MavenExe @("-q", "test"); Invoke-Checked $MavenExe @("-q", "-DskipTests", "package") } finally { Pop-Location }
    Push-Location $FrontendRoot
    try { Invoke-Checked $NpmExe @("run", "typecheck"); Invoke-Checked $NpmExe @("run", "build") } finally { Pop-Location }
  } else {
    Push-Location $BackendRoot
    try { Invoke-Checked $MavenExe @("-q", "-DskipTests", "package") } finally { Pop-Location }
  }

  $ConfigPath = Join-Path $RuntimeRoot "pit-pre-config.json"
  [ordered]@{
    database = [ordered]@{
      host = $HostName
      port = $Port
      user = $AppUser
      password = $AppPassword
      database = $Database
      charset = "utf8mb4"
    }
    working_directory = $PredictionRoot
  } | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $ConfigPath -Encoding UTF8

  Push-Location $PredictionRoot
  try { Invoke-Checked $PythonExe @("-m", "pit_pre", "--config", $ConfigPath, "--project-code", $ProjectCode) } finally { Pop-Location }

  $Jar = Get-ChildItem -LiteralPath (Join-Path $BackendRoot "target") -Filter "*.jar" | Where-Object { $_.Name -notlike "*.original" } | Sort-Object LastWriteTime -Descending | Select-Object -First 1
  if (-not $Jar) { throw "Packaged backend jar was not found." }

  foreach ($key in $EnvironmentKeys) { $PreviousEnvironment[$key] = [Environment]::GetEnvironmentVariable($key, "Process") }
  $DbUrl = "jdbc:mysql://${HostName}:$Port/${Database}?useUnicode=true&characterEncoding=utf8&serverTimezone=Asia/Shanghai&useSSL=false&allowPublicKeyRetrieval=true"
  $RuntimeEnvironment = [ordered]@{
    DB_URL = $DbUrl
    DB_USERNAME = $AppUser
    DB_PASSWORD = $AppPassword
    SERVER_PORT = [string]$BackendPort
    SPRING_PROFILES_ACTIVE = "reproduce"
    SHM_EM_NOTIFICATION_SCHEDULER_ENABLED = "false"
    SHM_EM_NOTIFICATION_MAIL_SEND_ENABLED = "false"
    SHM_EM_RESPONSE_AUTOMATION_ENABLED = "false"
    SHM_EM_REPORT_OUTPUT_DIR = (Join-Path $RuntimeRoot "reports")
  }
  foreach ($entry in $RuntimeEnvironment.GetEnumerator()) { [Environment]::SetEnvironmentVariable($entry.Key, $entry.Value, "Process") }

  $BackendProcess = Start-Process -FilePath $JavaExe -ArgumentList @("-jar", $Jar.FullName, "--spring.profiles.active=reproduce") `
    -WorkingDirectory $RuntimeRoot -RedirectStandardOutput (Join-Path $RuntimeRoot "backend.out.log") `
    -RedirectStandardError (Join-Path $RuntimeRoot "backend.err.log") -WindowStyle Hidden -PassThru

  $Ready = $false
  $Deadline = (Get-Date).AddSeconds(120)
  while ((Get-Date) -lt $Deadline) {
    if ($BackendProcess.HasExited) { break }
    try {
      $Response = Invoke-RestMethod -Method GET -Uri "$BaseUrl/api/em/projects/1" -TimeoutSec 3
      if ($Response.code -eq 0) { $Ready = $true; break }
    } catch { Start-Sleep -Seconds 2 }
  }
  if (-not $Ready) {
    $BackendError = Get-Content -LiteralPath (Join-Path $RuntimeRoot "backend.err.log") -Raw -ErrorAction SilentlyContinue
    $BackendOutput = Get-Content -LiteralPath (Join-Path $RuntimeRoot "backend.out.log") -Raw -ErrorAction SilentlyContinue
    throw "Backend did not become ready.`n$BackendError`n$BackendOutput"
  }

  $ValidationOutput = & (Join-Path $PSScriptRoot "reproduce-softwarex-example.ps1") -BaseUrl $BaseUrl -ProjectId 1 `
    -MySqlExe $MySqlExe -HostName $HostName -Port $Port -User $AppUser -Password $AppPassword `
    -Database $Database -ReproductionExecute $true
  $ValidationJson = ($ValidationOutput | Out-String).Trim()
  [IO.Directory]::CreateDirectory([IO.Path]::GetDirectoryName($ResultPath)) | Out-Null
  [IO.File]::WriteAllText($ResultPath, $ValidationJson + [Environment]::NewLine, [Text.UTF8Encoding]::new($false))
  Write-Output $ValidationJson
  Write-Host "Acceptance result: $ResultPath"
} finally {
  if ($BackendProcess -and -not $BackendProcess.HasExited) {
    Stop-Process -Id $BackendProcess.Id -Force -ErrorAction SilentlyContinue
    $BackendProcess.WaitForExit(10000) | Out-Null
  }
  foreach ($key in $EnvironmentKeys) { [Environment]::SetEnvironmentVariable($key, $PreviousEnvironment[$key], "Process") }
  $ResolvedRuntime = [IO.Path]::GetFullPath($RuntimeRoot)
  $TempRoot = [IO.Path]::GetFullPath([IO.Path]::GetTempPath())
  if ((Test-Path -LiteralPath $ResolvedRuntime) -and $ResolvedRuntime.StartsWith($TempRoot, [StringComparison]::OrdinalIgnoreCase) -and [IO.Path]::GetFileName($ResolvedRuntime).StartsWith("shm-em-reproduce-")) {
    [IO.Directory]::Delete($ResolvedRuntime, $true)
  }
  if (-not $KeepBuildOutputs) { Remove-ReleaseBuildOutputs }
}
