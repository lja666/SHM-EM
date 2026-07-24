export interface ApiEnvelope<T> {
  code?: number
  message?: string
  data?: T
  rows?: T
  success?: boolean
}

export interface Project {
  id?: number
  projectCode?: string
  projectName?: string
  infrastructureType?: string
  scenarioLabel?: string
  locationText?: string
  longitude?: number
  latitude?: number
  coordinateSystem?: string
  coordinateSource?: string
  coordinateQuality?: string
  mapProvider?: string
  spatialContextJson?: string
  description?: string
  status?: string
  startTime?: string
  endTime?: string
  [key: string]: unknown
}

export interface ProjectCard {
  projectId?: number
  id?: number
  projectCode?: string
  projectName?: string
  displayName?: string
  infrastructureType?: string
  projectStatus?: string
  status?: string
  locationText?: string
  longitude?: number
  latitude?: number
  siteCount?: number
  stationCount?: number
  stationRecordCount?: number
  instrumentCount?: number
  acquisitionModuleCount?: number
  dtuCount?: number
  stationMetricCount?: number
  registryCount?: number
  eventCount?: number
  openEventCount?: number
  latestEventTime?: string
  latestObservationTime?: string
  lowFrequencyObservationCount?: number
  accelerationSampleCount?: number
  notificationTaskCount?: number
  reportInstanceCount?: number
  [key: string]: unknown
}

export interface CountItem {
  itemCode?: string
  itemCount?: number
  [key: string]: unknown
}

export interface DatasetManifest {
  datasetCode?: string
  datasetName?: string
  scenarioType?: string
  inputDescription?: string
  datasetUri?: string
  timeStart?: string
  timeEnd?: string
  expectedResultHash?: string
  license?: string
  citation?: string
  reproducibilityLevel?: string
  [key: string]: unknown
}

export interface ProjectOverview {
  projects: ProjectCard[]
  projectCount?: number
  message?: string
  [key: string]: unknown
}

export interface ProjectContext {
  project?: Project
  projectDisplay?: ProjectCard
  summary?: ProjectCard
  stationTypeCounts?: CountItem[]
  instrumentTypeCounts?: CountItem[]
  metricCounts?: CountItem[]
  eventLevelCounts?: CountItem[]
  dataset?: DatasetManifest | null
  objectTreeUrl?: string
  [key: string]: unknown
}

export interface RegistryNode {
  type?: string
  id?: number
  code?: string
  name?: string
  storageBackend?: string
  storageMode?: string
  sampleFrequencyHz?: number
  enabled?: number
  queryable?: number
  eventSource?: number
  [key: string]: unknown
}

export interface MetricNode {
  type?: string
  id?: number
  code?: string
  name?: string
  metricUnit?: string
  baselineValue?: number
  warningEnabled?: number
  registries?: RegistryNode[]
  [key: string]: unknown
}

export interface InstrumentNode {
  type?: string
  id?: number
  code?: string
  name?: string
  instrumentType?: string
  samplingMode?: string
  samplingFrequency?: number
  status?: string
  metrics?: MetricNode[]
  [key: string]: unknown
}

export interface StationNode {
  type?: string
  id?: number
  code?: string
  name?: string
  siteNo?: string
  siteName?: string
  stationType?: string
  status?: string
  instruments?: InstrumentNode[]
  [key: string]: unknown
}

export interface ProjectObjectTree {
  project?: ProjectCard
  treeRole?: string
  stations: StationNode[]
  siteCount?: number
  stationCount?: number
  stationRecordCount?: number
  instrumentCount?: number
  acquisitionModuleCount?: number
  dtuCount?: number
  stationMetricCount?: number
  registryCount?: number
  [key: string]: unknown
}

export interface Station {
  id?: number
  projectId?: number
  stationCode?: string
  stationName?: string
  stationType?: string
  positionDesc?: string
  longitude?: number
  latitude?: number
  x?: number
  y?: number
  z?: number
  layoutX?: number
  layoutY?: number
  elevation?: number
  installationTime?: string
  status?: string
  metadataJson?: string
  enabled?: number
  [key: string]: unknown
}

export interface Instrument {
  id?: number
  projectId?: number
  stationId?: number
  instrumentCode?: string
  instrumentName?: string
  instrumentType?: string
  vendor?: string
  model?: string
  serialNo?: string
  dtuCode?: string
  moduleNo?: string
  moduleName?: string
  channelNo?: string
  samplingMode?: string
  rawUnitDesc?: string
  communicationMode?: string
  protocolCode?: string
  installLocation?: string
  installationTime?: string
  calibrationJson?: string
  status?: string
  samplingFrequency?: number
  enabled?: number
  [key: string]: unknown
}

export interface Metric {
  id?: number
  metricCode?: string
  metricName?: string
  metricCategory?: string
  valueType?: string
  defaultUnit?: string
  riskDirection?: string
  enabled?: number
  [key: string]: unknown
}

export interface StationMetric {
  id?: number
  projectId?: number
  stationId?: number
  instrumentId?: number
  metricCode?: string
  displayName?: string
  metricUnit?: string
  baselineValue?: number
  baselineTime?: string
  warningEnabled?: number
  displayOrder?: number
  metadataJson?: string
  enabled?: number
  [key: string]: unknown
}

export interface ObservationQuery {
  registryCode?: string
  projectId?: number
  stationId?: number
  instrumentId?: number
  instrumentType?: string
  sensorNo?: string
  metricCode?: string
  startTime?: string
  endTime?: string
  limit?: number
}

export interface LowFrequencyObservation {
  id?: number
  projectId?: number
  stationId?: number
  instrumentId?: number
  metricCode?: string
  engineeringMetricCode?: string
  observedAt?: string
  rawValue?: number
  rawUnit?: string
  metricValue?: number
  metricUnit?: string
  engineeringValue?: number
  engineeringUnit?: string
  conversionOperatorCode?: string
  conversionVersion?: string
  conversionStatus?: string
  conversionRemark?: string
  qualityFlag?: string
  [key: string]: unknown
}

export interface PredictionQuery {
  valueMode?: 'RAW' | 'ENGINEERING' | string
  projectId?: number
  modelCode?: string
  targetType?: string
  featureCode?: string
  batchCode?: string
  batchId?: number
  runId?: number
  stationId?: number
  stationIds?: number[]
  instrumentId?: number
  instrumentIds?: number[]
  instrumentType?: string
  metricCode?: string
  registryCode?: string
  status?: string
  maxHorizonMinutes?: number
  qualityFilter?: string
  includeObserved?: boolean
  startTime?: string
  endTime?: string
  limit?: number
}

export interface PredictionBatch {
  id?: number
  batchCode?: string
  projectId?: number
  baseTime?: string
  timeStepMinutes?: number
  horizonMinutes?: number
  rollingSteps?: number
  modelCount?: number
  featureCount?: number
  pipelineVersion?: string
  featureMappingVersion?: string
  inputHash?: string
  outputHash?: string
  status?: string
  message?: string
  startedAt?: string
  finishedAt?: string
  createdAt?: string
  updatedAt?: string
  [key: string]: unknown
}

export interface PredictionModel {
  id?: number
  projectId?: number
  modelCode?: string
  modelName?: string
  modelType?: string
  targetType?: string
  targetMetricCode?: string
  inputMetricsJson?: string
  artifactUri?: string
  artifactHash?: string
  preprocessorUri?: string
  preprocessorHash?: string
  inferenceScriptHash?: string
  bestParamsHash?: string
  runtimeManifestHash?: string
  environmentDigest?: string
  artifactBundleHash?: string
  modelVersion?: string
  runtimeConfigJson?: string
  requiredHistoryRows?: number
  status?: string
  createdAt?: string
  updatedAt?: string
  [key: string]: unknown
}

export interface PredictionFeatureMapping {
  id?: number
  projectId?: number
  modelId?: number
  featureCode?: string
  featureName?: string
  featureLabel?: string
  trainingFeatureCode?: string
  featureGroup?: string
  targetType?: string
  featureRole?: string
  stationId?: number
  instrumentId?: number
  sourceMetricCode?: string
  sourceRegistryCode?: string
  sourceField?: string
  sourceValueColumn?: string
  inputValueMode?: string
  schemaVersion?: string
  featureOperatorCode?: string
  outputConversionOperatorCode?: string
  outputConversionVersion?: string
  windowType?: string
  windowSizeSeconds?: number
  featureOrder?: number
  required?: number
  predictionTarget?: number
  transformJson?: string
  metadataJson?: string
  enabled?: number
  createdAt?: string
  updatedAt?: string
  [key: string]: unknown
}

export interface PredictionDisplay {
  id?: number
  projectId?: number
  batchId?: number
  batchCode?: string
  runId?: number
  modelId?: number
  modelCode?: string
  modelVersion?: string
  targetType?: string
  featureCode?: string
  featureLabel?: string
  stationId?: number
  stationName?: string
  instrumentId?: number
  instrumentCode?: string
  metricCode?: string
  engineeringMetricCode?: string
  step?: number
  horizonMinutes?: number
  baseTime?: string
  futureTime?: string
  predictedValue?: number
  predictedUnit?: string
  rawPredictedValue?: number
  rawPredictedUnit?: string
  engineeringValue?: number
  engineeringUnit?: string
  rawLowerBound?: number
  rawUpperBound?: number
  conversionOperatorCode?: string
  conversionVersion?: string
  conversionStatus?: string
  conversionRemark?: string
  lowerBound?: number
  upperBound?: number
  confidence?: number
  qualityFlag?: string
  sourceRecordKey?: string
  createdAt?: string
  [key: string]: unknown
}

export interface PredictionRun {
  id?: number
  projectId?: number
  batchId?: number
  modelId?: number
  modelCode?: string
  modelVersion?: string
  targetType?: string
  artifactHash?: string
  preprocessorHash?: string
  inferenceScriptHash?: string
  bestParamsHash?: string
  runtimeManifestHash?: string
  environmentDigest?: string
  artifactBundleHash?: string
  inputSchemaHash?: string
  requiredHistoryRows?: number
  metricCode?: string
  inputWindowStart?: string
  inputWindowEnd?: string
  horizonMinutes?: number
  rollingSteps?: number
  inputSnapshotJson?: string
  status?: string
  message?: string
  resultHash?: string
  runtimeSeconds?: number
  startedAt?: string
  finishedAt?: string
  createdAt?: string
}

export interface PredictionTargetCompleteness {
  targetType?: string
  featureCount?: number
  expectedPointCount?: number
  actualPointCount?: number
  missingPointCount?: number
  completenessPercent?: number
  complete?: boolean
  coveredSteps?: number
  qualityIssueCount?: number
  missingPoints?: string[]
}

export interface PredictionCompleteness {
  gateId?: number
  batchId?: number
  batchCode?: string
  expectedModels?: number
  actualModels?: number
  successfulModels?: number
  expectedSteps?: number
  featureCount?: number
  expectedPointCount?: number
  actualPointCount?: number
  missingPointCount?: number
  completenessPercent?: number
  complete?: boolean
  batchStatus?: string
  invalidTimestampCount?: number
  qualityIssueCount?: number
  executionEligible?: boolean
  issues?: string[]
  targets?: PredictionTargetCompleteness[]
}

export interface PredictionExecutionGate {
  id?: number
  batchId?: number
  projectId?: number
  batchCode?: string
  executionMode?: 'OPERATIONAL' | 'REPLAY' | 'REPRODUCTION' | string
  referenceTime?: string
  contractVersion?: string
  contractFingerprint?: string
  expectedModelCount?: number
  actualModelCount?: number
  successfulModelCount?: number
  expectedFeatureCount?: number
  actualFeatureCount?: number
  expectedSteps?: number
  expectedPointCount?: number
  actualPointCount?: number
  missingPointCount?: number
  invalidTimestampCount?: number
  qualityIssueCount?: number
  baseTimeAgeMinutes?: number
  maxAgeMinutes?: number
  modelSetValid?: boolean
  featureSetValid?: boolean
  timelineValid?: boolean
  qualityValid?: boolean
  artifactHashValid?: boolean
  freshnessValid?: boolean
  executionEligible?: boolean
  gateHash?: string
  evaluatedAt?: string
  issues?: string[]
  missingModels?: string[]
  unexpectedModels?: string[]
  missingFeatures?: string[]
  unexpectedFeatures?: string[]
  missingTimelinePoints?: string[]
  targets?: PredictionTargetCompleteness[]
}

export interface ProjectFutureTargetState {
  targetType?: string
  featureCount?: number
  assessedFeatureCount?: number
  warningCount?: number
  alarmCount?: number
  riskLevel?: string
  peakValue?: number
  unit?: string
  firstExceedanceTime?: string
}

export interface ProjectFutureContributor {
  featureCode?: string
  featureLabel?: string
  targetType?: string
  metricCode?: string
  predictedValue?: number
  unit?: string
  thresholdValue?: number
  operator?: string
  riskLevel?: string
  riskRank?: number
  firstExceedanceTime?: string
  ruleCode?: string
}

export interface ProjectFutureStationState {
  stationId?: number
  stationName?: string
  riskLevel?: string
  contributors?: ProjectFutureContributor[]
}

export interface ProjectFutureTimelineState {
  step?: number
  horizonMinutes?: number
  futureTime?: string
  riskLevel?: string
  exceedingFeatureCount?: number
}

export interface ProjectFutureState {
  projectId?: number
  batchId?: number
  batchCode?: string
  baseTime?: string
  horizonMinutes?: number
  executionMode?: string
  gateId?: number
  executionEligible?: boolean
  executionBlockers?: string[]
  aggregationPolicyVersion?: string
  aggregationPolicyCode?: string
  aggregationPolicyHash?: string
  stateHash?: string
  observedRiskLevel?: string
  openObservedEventCount?: number
  forecastRiskLevel?: string
  overallRiskLevel?: string
  earliestExceedanceTime?: string
  assessedFeatureCount?: number
  unassessedFeatureCount?: number
  executionGate?: PredictionExecutionGate
  targets?: ProjectFutureTargetState[]
  stations?: ProjectFutureStationState[]
  timeline?: ProjectFutureTimelineState[]
}

export interface PredictionBatchDetail {
  batch?: PredictionBatch
  runs?: PredictionRun[]
  completeness?: PredictionCompleteness
  linkedEventCount?: number
}

export interface MetricSeriesPoint {
  projectId?: number
  stationId?: number
  instrumentId?: number
  metricCode?: string
  engineeringMetricCode?: string
  timestamp?: string
  value?: number
  unit?: string
  rawValue?: number
  rawUnit?: string
  engineeringValue?: number
  engineeringUnit?: string
  valueMode?: 'RAW' | 'ENGINEERING' | string
  baselineValue?: number
  qualityFlag?: string
  conversionOperatorCode?: string
  conversionVersion?: string
  conversionStatus?: string
  conversionRemark?: string
  sourceType?: 'OBSERVATION' | 'PREDICTION' | string
  sourceRegistryCode?: string
  sourceRecordKey?: string
  sourceBatchId?: number
  sourceBatchCode?: string
  sourceRunId?: number
  sourceModelId?: number
  sourceModelCode?: string
  sourceModelVersion?: string
  targetType?: string
  featureCode?: string
  featureLabel?: string
  step?: number
  horizonMinutes?: number
  originTime?: string
  lowerBound?: number
  upperBound?: number
  confidence?: number
  resultHash?: string
}

export interface EventPredictionTrace {
  id?: number
  eventId?: number
  eventCode?: string
  eventSource?: string
  predictionBatchId?: number
  batchCode?: string
  baseTime?: string
  horizonMinutes?: number
  batchStatus?: string
  pipelineVersion?: string
  featureMappingVersion?: string
  inputHash?: string
  outputHash?: string
  predictionRunId?: number
  predictionGateId?: number
  modelId?: number
  modelCode?: string
  modelVersion?: string
  targetType?: string
  inputWindowStart?: string
  inputWindowEnd?: string
  artifactHash?: string
  inputSchemaHash?: string
  runResultHash?: string
  firstExceedanceTime?: string
  leadTimeMinutes?: number
  peakPredictedValue?: number
  consecutiveExceedanceSteps?: number
  forecastSnapshotJson?: string
  resultHash?: string
  gateExecutionMode?: string
  gateExecutionEligible?: boolean
  gateHash?: string
  gateIssuesJson?: string
  gateEvaluatedAt?: string
  createdAt?: string
}

export interface RuleEvaluationResult {
  runId?: number
  ruleId?: number
  eventCount?: number
  resultHash?: string
  ruleVersion?: string
  conversionVersion?: string
  events?: MonitoringEvent[]
  snapshots?: Record<string, unknown>[]
  inputSource?: string
  predictionGate?: PredictionExecutionGate
  executionEligible?: boolean
  executionBlockers?: string[]
  evaluation?: RuleEvaluationResult
  event?: MonitoringEvent
  responses?: Record<string, unknown>[]
  message?: string
  [key: string]: unknown
}

export interface AccelerationWaveform {
  id?: number
  projectId?: number
  stationId?: number
  instrumentId?: number
  sampleIndex?: number
  sampleOffsetMs?: number
  sampleTime?: string
  xAccel?: number
  yAccel?: number
  zAccel?: number
  accelUnit?: string
  qualityFlag?: string
  [key: string]: unknown
}

export interface EventRule {
  id?: number
  projectId?: number
  ruleCode?: string
  ruleName?: string
  metricCode?: string
  inputSource?: string
  predictionModelCode?: string
  predictionTargetType?: string
  predictionFeatureCode?: string
  forecastHorizonMinutes?: number
  minimumConsecutiveSteps?: number
  seriesQualityFilter?: string
  eventType?: string
  eventLevel?: string
  operator?: string
  thresholdValue?: number
  thresholdUnit?: string
  enabled?: number
  [key: string]: unknown
}

export interface MonitoringEvent {
  id?: number
  eventCode?: string
  projectId?: number
  stationId?: number
  instrumentId?: number
  metricCode?: string
  eventType?: string
  eventLevel?: string
  eventStatus?: string
  sourceType?: string
  sourceRegistryCode?: string
  detectedAt?: string
  triggerValue?: number
  thresholdValue?: number
  unit?: string
  triggerReason?: string
  calculationSnapshotJson?: string
  predictionBatchId?: number
  predictionRunId?: number
  predictionModelId?: number
  predictionBaseTime?: string
  firstExceedanceTime?: string
  leadTimeMinutes?: number
  peakPredictedValue?: number
  consecutiveExceedanceSteps?: number
  forecastSnapshotJson?: string
  predictionResultHash?: string
  [key: string]: unknown
}

export interface DeviceWarning {
  id?: number
  eventCode?: string
  projectId?: number
  stationId?: number
  instrumentId?: number
  metricCode?: string
  eventType?: string
  eventLevel?: string
  eventStatus?: string
  detectedAt?: string
  triggerValue?: number
  thresholdValue?: number
  unit?: string
  triggerReason?: string
  stationCode?: string
  stationName?: string
  stationType?: string
  instrumentCode?: string
  instrumentName?: string
  instrumentType?: string
  instrumentStatus?: string
  [key: string]: unknown
}

export interface ReportItem {
  id: number
  projectId: number
  eventId?: number
  reportName: string
  reportTitle?: string
  reportType: string
  contentHtml?: string
  contentText?: string
  docxUrl?: string
  pdfUrl?: string
  reportUrl?: string
  reportHash?: string
  metadataJson?: string
  generatedAt: string
  status: string
}

export interface EvidenceItem {
  id: number
  projectId: number
  eventId?: number
  stationId?: number
  evidenceCode: string
  evidenceType: string
  resourceType?: string
  resourceUrl?: string
  relatedEventCode?: string
  sourceRecordKey?: string
  hashValue?: string
  metadataJson?: string
  linkType?: string
  confidence?: string
  archivedAt?: string
  capturedAt?: string
  createdAt?: string
  status: string
}
