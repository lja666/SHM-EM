param(
  [string]$BaseUrl = "http://localhost:5101",
  [long]$ProjectId = 1,
  [string]$MySqlExe = "mysql",
  [string]$HostName = "localhost",
  [int]$Port = 3306,
  [string]$User = "shm_em",
  [string]$Password = $env:DB_PASSWORD,
  [string]$Database = "shm_em",
  [bool]$ReproductionExecute = $true
)

$ErrorActionPreference = "Stop"
if ([string]::IsNullOrWhiteSpace($Password)) {
  throw "Database password is required. Pass -Password or set DB_PASSWORD."
}
if ($ReproductionExecute -and $Database -notmatch '^shm_em_reproduce_[A-Za-z0-9_]+$') {
  throw "Formal reproduction execution requires an isolated shm_em_reproduce_* database."
}

function Invoke-ShmEmApi {
  param([string]$Path)
  Invoke-RestMethod -Method "GET" -Uri "$BaseUrl$Path" -TimeoutSec 30
}

function Invoke-ShmEmPost {
  param([string]$Path, [hashtable]$Body)
  Invoke-RestMethod -Method "POST" -Uri "$BaseUrl$Path" -ContentType "application/json" `
    -Body ($Body | ConvertTo-Json -Depth 8 -Compress) -TimeoutSec 60
}

function Invoke-ShmEmSqlScalar {
  param([string]$Sql)
  $value = & $MySqlExe "--host=$HostName" "--port=$Port" "--user=$User" "--password=$Password" `
    --default-character-set=utf8mb4 --skip-column-names --batch "--database=$Database" "--execute=$Sql"
  if ($LASTEXITCODE -ne 0) {
    throw "mysql query failed: $Sql"
  }
  return [string]($value | Select-Object -First 1)
}

$project = Invoke-ShmEmApi "/api/em/projects/$ProjectId"
$events = Invoke-ShmEmApi "/api/em/projects/$ProjectId/events?limit=100"
$latestBatchId = Invoke-ShmEmSqlScalar "SELECT id FROM em_prediction_batch WHERE project_id=$ProjectId AND status='success' ORDER BY base_time DESC, id DESC LIMIT 1;"
if ([string]::IsNullOrWhiteSpace($latestBatchId)) {
  throw "No successful prediction batch found."
}

$batch = Invoke-ShmEmApi "/api/em/predictions/batches/$latestBatchId"
$gate = Invoke-ShmEmApi "/api/em/predictions/batches/$latestBatchId/execution-gate?mode=REPLAY"
$futureState = Invoke-ShmEmApi "/api/em/projects/$ProjectId/future-state?batchId=$latestBatchId&executionMode=REPLAY"

$predictionRuleId = Invoke-ShmEmSqlScalar "SELECT id FROM em_event_rule WHERE project_id=$ProjectId AND UPPER(input_source)='PREDICTION' AND enabled=1 ORDER BY id LIMIT 1;"
if ([string]::IsNullOrWhiteSpace($predictionRuleId)) {
  throw "No enabled prediction rule found."
}

$before = [ordered]@{
  events = [int](Invoke-ShmEmSqlScalar "SELECT COUNT(*) FROM em_monitoring_event WHERE project_id=$ProjectId;")
  notifications = [int](Invoke-ShmEmSqlScalar "SELECT COUNT(*) FROM em_notification_task WHERE project_id=$ProjectId;")
  responses = [int](Invoke-ShmEmSqlScalar "SELECT COUNT(*) FROM em_event_response_workflow WHERE project_id=$ProjectId;")
  reports = [int](Invoke-ShmEmSqlScalar "SELECT COUNT(*) FROM em_report_instance WHERE project_id=$ProjectId;")
  links = [int](Invoke-ShmEmSqlScalar "SELECT COUNT(*) FROM em_event_prediction_link l JOIN em_monitoring_event e ON e.id=l.event_id WHERE e.project_id=$ProjectId;")
}
$evaluate = Invoke-ShmEmPost "/api/em/projects/$ProjectId/rules/$predictionRuleId/evaluate" @{
  inputSource = "PREDICTION"
  predictionBatchId = [long]$latestBatchId
  predictionExecutionMode = "REPLAY"
  seriesQualityFilter = "normal"
}
$afterEvaluate = [ordered]@{
  events = [int](Invoke-ShmEmSqlScalar "SELECT COUNT(*) FROM em_monitoring_event WHERE project_id=$ProjectId;")
  notifications = [int](Invoke-ShmEmSqlScalar "SELECT COUNT(*) FROM em_notification_task WHERE project_id=$ProjectId;")
  responses = [int](Invoke-ShmEmSqlScalar "SELECT COUNT(*) FROM em_event_response_workflow WHERE project_id=$ProjectId;")
  reports = [int](Invoke-ShmEmSqlScalar "SELECT COUNT(*) FROM em_report_instance WHERE project_id=$ProjectId;")
  links = [int](Invoke-ShmEmSqlScalar "SELECT COUNT(*) FROM em_event_prediction_link l JOIN em_monitoring_event e ON e.id=l.event_id WHERE e.project_id=$ProjectId;")
}
$evaluateSideEffectFree = @($before.Keys | Where-Object { $before[$_] -ne $afterEvaluate[$_] }).Count -eq 0

$reproductionEventId = $null
$reproductionHash = $null
$reproductionExecuteOk = $false
$reproductionResponseCount = 0
$reproductionStepCount = 0
$reproductionReportCount = 0
$reproductionNotificationCount = 0
if ($ReproductionExecute) {
  $execute = Invoke-ShmEmPost "/api/em/projects/$ProjectId/rules/$predictionRuleId/execute" @{
    inputSource = "PREDICTION"
    predictionBatchId = [long]$latestBatchId
    predictionExecutionMode = "REPRODUCTION"
    seriesQualityFilter = "normal"
  }
  $reproductionEventId = [long]$execute.data.event.id
  $eventLinkCountForBatch = [int](Invoke-ShmEmSqlScalar "SELECT COUNT(*) FROM em_event_prediction_link l JOIN em_monitoring_event e ON e.id=l.event_id WHERE l.prediction_batch_id=$latestBatchId AND e.id=$reproductionEventId AND e.run_type='reproduction';")
  $reproductionGateCount = [int](Invoke-ShmEmSqlScalar "SELECT COUNT(*) FROM em_event_prediction_link l JOIN em_prediction_execution_gate g ON g.id=l.prediction_gate_id WHERE l.event_id=$reproductionEventId AND g.execution_mode='REPRODUCTION' AND g.execution_eligible=1;")
  $reproductionResponseCount = [int](Invoke-ShmEmSqlScalar "SELECT COUNT(*) FROM em_event_response_workflow WHERE event_id=$reproductionEventId;")
  $reproductionStepCount = [int](Invoke-ShmEmSqlScalar "SELECT COUNT(*) FROM em_event_response_step s JOIN em_event_response_workflow w ON w.id=s.workflow_id WHERE w.event_id=$reproductionEventId;")
  $reproductionReportCount = [int](Invoke-ShmEmSqlScalar "SELECT COUNT(*) FROM em_report_instance WHERE event_id=$reproductionEventId;")
  $reproductionNotificationCount = [int](Invoke-ShmEmSqlScalar "SELECT COUNT(*) FROM em_notification_task WHERE event_id=$reproductionEventId;")
  $reproductionHash = Invoke-ShmEmSqlScalar "SELECT SHA2(CONCAT_WS('|',b.batch_code,b.output_hash,e.event_code,e.run_type,g.gate_hash,l.result_hash,w.workflow_code,COALESCE(r.source_record_key,''),COUNT(DISTINCT s.id)),256) FROM em_event_prediction_link l JOIN em_monitoring_event e ON e.id=l.event_id JOIN em_prediction_batch b ON b.id=l.prediction_batch_id JOIN em_prediction_execution_gate g ON g.id=l.prediction_gate_id JOIN em_event_response_workflow w ON w.event_id=e.id LEFT JOIN em_event_response_step s ON s.workflow_id=w.id LEFT JOIN em_report_instance r ON r.event_id=e.id WHERE e.id=$reproductionEventId GROUP BY b.batch_code,b.output_hash,e.event_code,e.run_type,g.gate_hash,l.result_hash,w.workflow_code,r.source_record_key;"
  $reproductionExecuteOk = $eventLinkCountForBatch -eq 1 -and $reproductionGateCount -eq 1 `
    -and $reproductionResponseCount -eq 1 -and $reproductionStepCount -ge 4 `
    -and $reproductionReportCount -eq 1 -and $reproductionNotificationCount -eq 0 `
    -and $reproductionHash.Length -eq 64
}

$datasetCount = [int](Invoke-ShmEmSqlScalar "SELECT COUNT(*) FROM em_dataset_manifest WHERE project_id=$ProjectId;")
$modelCount = [int](Invoke-ShmEmSqlScalar "SELECT COUNT(*) FROM em_prediction_run WHERE batch_id=$latestBatchId AND status='success';")
$resultCount = [int](Invoke-ShmEmSqlScalar "SELECT COUNT(*) FROM em_prediction_result WHERE batch_id=$latestBatchId;")
$targetCount = [int](Invoke-ShmEmSqlScalar "SELECT COUNT(DISTINCT feature_code) FROM em_prediction_result WHERE batch_id=$latestBatchId;")
$stepCount = [int](Invoke-ShmEmSqlScalar "SELECT COUNT(DISTINCT step) FROM em_prediction_result WHERE batch_id=$latestBatchId;")
$conversionFailures = [int](Invoke-ShmEmSqlScalar "SELECT COUNT(*) FROM em_prediction_result WHERE batch_id=$latestBatchId AND (engineering_value IS NULL OR conversion_status<>'success');")
$integrityFailures = [int](Invoke-ShmEmSqlScalar "SELECT (SELECT COUNT(*) FROM em_prediction_run r LEFT JOIN em_prediction_batch b ON b.id=r.batch_id LEFT JOIN em_prediction_model m ON m.id=r.model_id WHERE r.project_id=$ProjectId AND (b.id IS NULL OR m.id IS NULL)) + (SELECT COUNT(*) FROM em_prediction_result p LEFT JOIN em_prediction_batch b ON b.id=p.batch_id LEFT JOIN em_prediction_run r ON r.id=p.run_id LEFT JOIN em_prediction_model m ON m.id=p.model_id WHERE p.project_id=$ProjectId AND (b.id IS NULL OR r.id IS NULL OR m.id IS NULL)) + (SELECT COUNT(*) FROM em_event_prediction_link l LEFT JOIN em_monitoring_event e ON e.id=l.event_id LEFT JOIN em_prediction_batch b ON b.id=l.prediction_batch_id LEFT JOIN em_prediction_execution_gate g ON g.id=l.prediction_gate_id WHERE e.id IS NULL OR b.id IS NULL OR g.id IS NULL) AS failures;")
$eventLinkCount = [int](Invoke-ShmEmSqlScalar "SELECT COUNT(*) FROM em_event_prediction_link l JOIN em_monitoring_event e ON e.id=l.event_id WHERE e.project_id=$ProjectId;")
$batchInputHash = Invoke-ShmEmSqlScalar "SELECT input_hash FROM em_prediction_batch WHERE id=$latestBatchId;"
$expectedInputHash = Invoke-ShmEmSqlScalar "SELECT JSON_UNQUOTE(JSON_EXTRACT(expected_output_json, '$.inputHash')) FROM em_dataset_manifest WHERE project_id=$ProjectId AND enabled=1 ORDER BY id LIMIT 1;"
$batchOutputHash = Invoke-ShmEmSqlScalar "SELECT output_hash FROM em_prediction_batch WHERE id=$latestBatchId;"
$expectedOutputHash = Invoke-ShmEmSqlScalar "SELECT expected_result_hash FROM em_dataset_manifest WHERE project_id=$ProjectId AND enabled=1 ORDER BY id LIMIT 1;"
$inputHashMatched = $batchInputHash -and $expectedInputHash -and $batchInputHash.Trim().ToLowerInvariant() -eq $expectedInputHash.Trim().ToLowerInvariant()
$outputHashMatched = $batchOutputHash -and $expectedOutputHash -and $batchOutputHash.Trim().ToLowerInvariant() -eq $expectedOutputHash.Trim().ToLowerInvariant()

$checks = [ordered]@{
  projectApi = $project.code -eq 0
  eventApi = $events.code -eq 0
  dataset = $datasetCount -eq 1
  modelSet = $modelCount -eq 6
  resultCompleteness = $resultCount -eq 4960 -and $targetCount -eq 124 -and $stepCount -eq 40
  engineeringConversion = $conversionFailures -eq 0
  referentialIntegrity = $integrityFailures -eq 0
  predictionInputHash = $inputHashMatched
  predictionOutputHash = $outputHashMatched
  replayGate = $gate.code -eq 0 -and [bool]$gate.data.executionEligible
  futureState = $futureState.code -eq 0 -and [bool]$futureState.data.executionEligible `
    -and ([string]$futureState.data.stateHash).Length -eq 64 `
    -and ([string]$futureState.data.aggregationPolicyHash).Length -eq 64
  evaluateCandidate = $evaluate.code -eq 0 -and [int]$evaluate.data.eventCount -ge 1 -and [bool]$evaluate.data.executionEligible
  evaluateOperationalSideEffectFree = $evaluateSideEffectFree
  reproductionExecute = $reproductionExecuteOk
  eventTrace = $eventLinkCount -ge 1
  responseWorkflow = $reproductionResponseCount -eq 1 -and $reproductionStepCount -ge 4 `
    -and $reproductionReportCount -eq 1 -and $reproductionNotificationCount -eq 0
}

[ordered]@{
  release = "SHM-EM 1.0.1"
  projectCode = $project.data.projectCode
  predictionBatchId = [long]$latestBatchId
  batchCode = $batch.data.batch.batchCode
  modelCount = $modelCount
  targetCount = $targetCount
  predictionSteps = $stepCount
  resultCount = $resultCount
  conversionFailures = $conversionFailures
  integrityFailures = $integrityFailures
  eventLinkCount = $eventLinkCount
  reproductionEventId = $reproductionEventId
  reproductionHash = $reproductionHash
  predictionInputHash = $batchInputHash
  expectedPredictionInputHash = $expectedInputHash
  predictionOutputHash = $batchOutputHash
  expectedPredictionOutputHash = $expectedOutputHash
  checks = $checks
} | ConvertTo-Json -Depth 8

$failed = @($checks.GetEnumerator() | Where-Object { -not $_.Value })
if ($failed.Count -gt 0) {
  throw "SHM-EM reproducibility check failed: $($failed.Name -join ', ')"
}
