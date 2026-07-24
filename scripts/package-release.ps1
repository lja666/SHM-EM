param(
  [string]$Version = "1.0.0",
  [string]$OutputDirectory = "artifacts"
)

$ErrorActionPreference = "Stop"
$root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$output = [IO.Path]::GetFullPath((Join-Path $root $OutputDirectory))
$archive = Join-Path $output "SHM-EM-$Version.zip"
$tempRoot = [IO.Path]::GetFullPath([IO.Path]::GetTempPath())
$staging = Join-Path $tempRoot ("shm-em-release-" + [Guid]::NewGuid().ToString("N"))
$restrictedFileNames = @(
  "01_SHM_EM_real_data.sql",
  "02_SHM_EM_engineering_conversion.sql",
  "03_SHM_EM_validation_queries.sql"
)

$restrictedFiles = Get-ChildItem -LiteralPath $root -Recurse -File -Force -ErrorAction Stop |
  Where-Object { $restrictedFileNames -contains $_.Name }
if ($restrictedFiles) {
  throw "Restricted data files must remain outside the public repository: $($restrictedFiles.FullName -join ', ')"
}

$unsupportedShellScripts = Get-ChildItem -LiteralPath $root -Recurse -File -Filter "*.sh" -Force -ErrorAction Stop
if ($unsupportedShellScripts) {
  throw "The Windows release must not contain unsupported Bash entry points: $($unsupportedShellScripts.FullName -join ', ')"
}

New-Item -ItemType Directory -Force -Path $output | Out-Null
New-Item -ItemType Directory -Force -Path $staging | Out-Null
try {
  $destination = Join-Path $staging "SHM-EM-$Version"
  New-Item -ItemType Directory -Force -Path $destination | Out-Null
  $excludedDirectories = @(
    ".git", ".idea", ".shm-em-run", "artifacts", "node_modules", "target", "dist",
    "__pycache__", ".npm-cache", "logs", "runtime", "report-files"
  )
  $excludedFiles = @(
    ".env", ".env.local", ".env.*.local", "config.json", "*.log", "*.tmp", "*.bak",
    "*.iml", "*.pyc", ".DS_Store"
  )
  $arguments = @($root, $destination, "/E", "/NFL", "/NDL", "/NJH", "/NJS", "/NP", "/R:1", "/W:1", "/XD")
  $arguments += $excludedDirectories
  $arguments += "/XF"
  $arguments += $excludedFiles
  & robocopy @arguments | Out-Null
  if ($LASTEXITCODE -ge 8) { throw "Release staging failed with robocopy exit code $LASTEXITCODE" }

  $stagedRestrictedFiles = Get-ChildItem -LiteralPath $destination -Recurse -File -Force |
    Where-Object { $restrictedFileNames -contains $_.Name }
  if ($stagedRestrictedFiles) {
    throw "Release staging contains restricted data files: $($stagedRestrictedFiles.FullName -join ', ')"
  }

  $stagedShellScripts = Get-ChildItem -LiteralPath $destination -Recurse -File -Filter "*.sh" -Force
  if ($stagedShellScripts) {
    throw "Release staging contains unsupported Bash entry points: $($stagedShellScripts.FullName -join ', ')"
  }

  if (Test-Path -LiteralPath $archive) { Remove-Item -LiteralPath $archive -Force }
  Compress-Archive -Path $destination -DestinationPath $archive -CompressionLevel Optimal
  $hash = (Get-FileHash -Algorithm SHA256 -LiteralPath $archive).Hash.ToLowerInvariant()
  $checksumFile = "$archive.sha256"
  [IO.File]::WriteAllText($checksumFile, "$hash  $([IO.Path]::GetFileName($archive))`n", [Text.Encoding]::ASCII)
  [ordered]@{ archive = $archive; checksumFile = $checksumFile; sha256 = $hash } | ConvertTo-Json
}
finally {
  $resolvedStaging = [IO.Path]::GetFullPath($staging)
  if ($resolvedStaging.StartsWith($tempRoot, [StringComparison]::OrdinalIgnoreCase) -and
      [IO.Path]::GetFileName($resolvedStaging).StartsWith("shm-em-release-")) {
    Remove-Item -LiteralPath $resolvedStaging -Recurse -Force -ErrorAction SilentlyContinue
  }
}
