param(
  [string]$DbUrl = "jdbc:mysql://localhost:3306/shm_em?useUnicode=true&characterEncoding=utf8&zeroDateTimeBehavior=convertToNull&serverTimezone=Asia/Shanghai",
  [string]$DbUsername = "shm_em",
  [string]$DbPassword = $env:DB_PASSWORD,
  [int]$BackendPort = 5101,
  [string]$FrontendApiBaseUrl = "http://localhost:5101",
  [string]$SpringProfilesActive = ""
)

$ErrorActionPreference = "Stop"
if ([string]::IsNullOrWhiteSpace($DbPassword)) {
  throw "Database password is required. Pass -DbPassword or set DB_PASSWORD."
}
$RepoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$LogDir = Join-Path $RepoRoot ".shm-em-run"
New-Item -ItemType Directory -Force -Path $LogDir | Out-Null
$Stamp = Get-Date -Format "yyyyMMdd-HHmmss"

$BackendOut = Join-Path $LogDir "backend-dev-$Stamp.out.log"
$BackendErr = Join-Path $LogDir "backend-dev-$Stamp.err.log"
$FrontendOut = Join-Path $LogDir "frontend-dev-$Stamp.out.log"
$FrontendErr = Join-Path $LogDir "frontend-dev-$Stamp.err.log"

$BackendCommand = @"
`$env:DB_URL='$DbUrl'
`$env:DB_USERNAME='$DbUsername'
`$env:DB_PASSWORD='$DbPassword'
`$env:SERVER_PORT='$BackendPort'
`$env:SPRING_PROFILES_ACTIVE='$SpringProfilesActive'
`$env:SHM_EM_NOTIFICATION_SCHEDULER_ENABLED='false'
mvn spring-boot:run
"@

$FrontendCommand = @"
`$env:VITE_API_BASE_URL='$FrontendApiBaseUrl'
npm run dev
"@

$Backend = Start-Process -FilePath (Get-Command pwsh).Source -ArgumentList @("-NoProfile", "-Command", $BackendCommand) -WorkingDirectory (Join-Path $RepoRoot "src\backend") -RedirectStandardOutput $BackendOut -RedirectStandardError $BackendErr -WindowStyle Hidden -PassThru
$Frontend = Start-Process -FilePath (Get-Command pwsh).Source -ArgumentList @("-NoProfile", "-Command", $FrontendCommand) -WorkingDirectory (Join-Path $RepoRoot "src\frontend") -RedirectStandardOutput $FrontendOut -RedirectStandardError $FrontendErr -WindowStyle Hidden -PassThru

[ordered]@{
  backendPid = $Backend.Id
  backendUrl = "http://localhost:$BackendPort"
  backendLog = $BackendOut
  frontendPid = $Frontend.Id
  frontendUrl = "http://localhost:5173"
  frontendLog = $FrontendOut
} | ConvertTo-Json -Depth 4
