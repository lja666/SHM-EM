param(
  [string]$MySqlExe = "mysql",
  [string]$HostName = "localhost",
  [int]$Port = 3306,
  [string]$User = "root",
  [string]$Password = "",
  [string]$Database = "shm_em",
  [string]$AppUser = "shm_em_reproduce",
  [string]$AppPassword = $env:MYSQL_PASSWORD,
  [string]$DataSqlPath = $env:SHM_EM_RESTRICTED_DATA_SQL,
  [string]$ConversionSqlPath = $env:SHM_EM_RESTRICTED_CONVERSION_SQL,
  [string]$ValidationSqlPath = $env:SHM_EM_RESTRICTED_VALIDATION_SQL,
  [switch]$ForceReset,
  [switch]$SkipValidation
)

$ErrorActionPreference = "Stop"
if ([string]::IsNullOrWhiteSpace($Password)) {
  throw "MySQL administrator password is required. Pass -Password explicitly."
}
if ([string]::IsNullOrWhiteSpace($AppPassword)) {
  throw "Application database password is required. Pass -AppPassword or set MYSQL_PASSWORD."
}
if ($Database -notmatch '^[A-Za-z0-9_]+$' -or $AppUser -notmatch '^[A-Za-z0-9_]+$') {
  throw "Database and application-user names may contain only letters, numbers, and underscores."
}
$RepoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$SqlRoot = Join-Path $RepoRoot "sql\shm_em_database"

function Resolve-RestrictedSql {
  param([string]$Path, [string]$Label)
  if ([string]::IsNullOrWhiteSpace($Path)) {
    throw "$Label is required and is not distributed with the public repository."
  }
  $resolved = (Resolve-Path -LiteralPath $Path).Path
  if ($resolved.StartsWith($RepoRoot.Path + [IO.Path]::DirectorySeparatorChar, [StringComparison]::OrdinalIgnoreCase)) {
    throw "$Label must remain outside the public repository: $resolved"
  }
  return $resolved
}

$UsingPublicSample = [string]::IsNullOrWhiteSpace($DataSqlPath)
if ($UsingPublicSample) {
  $DataSqlPath = Join-Path $SqlRoot "02_SHM_EM_public_sample.sql"
  if (-not $SkipValidation) {
    $ValidationSqlPath = Join-Path $SqlRoot "03_SHM_EM_public_validation.sql"
  }
} else {
  $DataSqlPath = Resolve-RestrictedSql $DataSqlPath "Restricted data SQL"
  $ConversionSqlPath = Resolve-RestrictedSql $ConversionSqlPath "Restricted conversion SQL"
  if (-not $SkipValidation) {
    $ValidationSqlPath = Resolve-RestrictedSql $ValidationSqlPath "Restricted validation SQL"
  }
}

function Invoke-MysqlCommand {
  param([string]$Command)
  & $MySqlExe -h $HostName -P $Port -u $User "-p$Password" --default-character-set=utf8mb4 -e $Command
  if ($LASTEXITCODE -ne 0) {
    throw "mysql command failed: $Command"
  }
}

function Invoke-SqlFile {
  param([string]$Path)
  $sourcePath = (Resolve-Path $Path).Path.Replace("\", "/")
  Write-Host "SOURCE $sourcePath"
  & $MySqlExe -h $HostName -P $Port -u $User "-p$Password" --default-character-set=utf8mb4 $Database -e "SOURCE $sourcePath"
  if ($LASTEXITCODE -ne 0) {
    throw "mysql source failed: $Path"
  }
}

Invoke-MysqlCommand "CREATE DATABASE IF NOT EXISTS $Database CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
$ExistingTables = & $MySqlExe -h $HostName -P $Port -u $User "-p$Password" --default-character-set=utf8mb4 -N -B -e "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='$Database';"
if ($LASTEXITCODE -ne 0) {
  throw "Unable to inspect database $Database."
}
if ([int]$ExistingTables -gt 0 -and -not $ForceReset) {
  throw "Database $Database is not empty. Use -ForceReset only after backing it up and confirming a full release rebuild."
}
if ([int]$ExistingTables -gt 0 -and $ForceReset) {
  if ($Database -notmatch '^shm_em_reproduce_[A-Za-z0-9_]+$') {
    throw "ForceReset is restricted to isolated shm_em_reproduce_* databases."
  }
  Invoke-MysqlCommand "DROP DATABASE $Database; CREATE DATABASE $Database CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
}
$EscapedAppPassword = $AppPassword.Replace("'", "''")
Invoke-MysqlCommand "CREATE USER IF NOT EXISTS '$AppUser'@'localhost' IDENTIFIED BY '$EscapedAppPassword'; ALTER USER '$AppUser'@'localhost' IDENTIFIED BY '$EscapedAppPassword'; GRANT ALL PRIVILEGES ON $Database.* TO '$AppUser'@'localhost'; CREATE USER IF NOT EXISTS '$AppUser'@'%' IDENTIFIED BY '$EscapedAppPassword'; ALTER USER '$AppUser'@'%' IDENTIFIED BY '$EscapedAppPassword'; GRANT ALL PRIVILEGES ON $Database.* TO '$AppUser'@'%'; FLUSH PRIVILEGES;"
Invoke-SqlFile (Join-Path $SqlRoot "00_SHM_EM_complete_schema.sql")
if ($UsingPublicSample) {
  Invoke-SqlFile (Join-Path $SqlRoot "01_SHM_EM_conversion_operators.sql")
  Invoke-SqlFile $DataSqlPath
} else {
  Invoke-SqlFile $DataSqlPath
  Invoke-SqlFile (Join-Path $SqlRoot "01_SHM_EM_conversion_operators.sql")
  Invoke-SqlFile $ConversionSqlPath
}

if (-not $SkipValidation) {
  Invoke-SqlFile $ValidationSqlPath
}

[ordered]@{
  database = $Database
  datasetMode = if ($UsingPublicSample) { "public_deidentified_sample" } else { "authorized_restricted_case" }
  schema = "00_SHM_EM_complete_schema.sql"
  data = [IO.Path]::GetFileName($DataSqlPath)
  conversionOperators = "01_SHM_EM_conversion_operators.sql"
  restrictedConversion = if ($UsingPublicSample) { $null } else { [IO.Path]::GetFileName($ConversionSqlPath) }
  validation = if ($SkipValidation) { $null } else { [IO.Path]::GetFileName($ValidationSqlPath) }
  appUser = $AppUser
  forcedReset = [bool]$ForceReset
  skipValidation = [bool]$SkipValidation
} | ConvertTo-Json -Depth 4
