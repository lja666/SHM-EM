import { computed, ref } from 'vue'
import { listLatestPredictions, listPredictionFeatures } from '../api/modules/prediction'
import type { PredictionDisplay, PredictionFeatureMapping } from '../types/engineering'

interface PredictionContext {
  projectId: number
  stationId?: number
  instrumentId?: number
  metricCode?: string
}

export function usePredictionTrend() {
  const featureMappings = ref<PredictionFeatureMapping[]>([])
  const predictionRows = ref<PredictionDisplay[]>([])
  const selectedPredictionFeature = ref<PredictionFeatureMapping | null>(null)
  const predictionLoading = ref(false)
  const loadedProjectId = ref<number | null>(null)
  let requestVersion = 0

  const predictionReady = computed(() => predictionRows.value.length > 0)

  async function loadPredictionFeatures(projectId: number) {
    if (!projectId) {
      featureMappings.value = []
      loadedProjectId.value = null
      return
    }
    featureMappings.value = await listPredictionFeatures({ projectId, limit: 1000 })
    loadedProjectId.value = projectId
  }

  async function loadPredictionForContext(context: PredictionContext) {
    const currentRequest = ++requestVersion
    predictionRows.value = []
    selectedPredictionFeature.value = null
    if (!context.projectId) return
    predictionLoading.value = true
    try {
      if (loadedProjectId.value !== context.projectId || !featureMappings.value.length) {
        await loadPredictionFeatures(context.projectId)
      }
      if (currentRequest !== requestVersion) return
      const candidates = rankedFeatureCandidates(featureMappings.value, context).slice(0, 5)
      if (!candidates.length) return

      for (const feature of candidates) {
        if (!feature.featureCode) continue
        const rows = await listLatestPredictions({
          projectId: context.projectId,
          targetType: feature.targetType,
          featureCode: feature.featureCode,
          limit: 200
        })
        if (currentRequest !== requestVersion) return
        if (rows.length) {
          selectedPredictionFeature.value = feature
          predictionRows.value = rows.slice().sort((a, b) => timeValue(a.futureTime) - timeValue(b.futureTime))
          return
        }
      }
    } finally {
      if (currentRequest === requestVersion) predictionLoading.value = false
    }
  }

  function clearPrediction() {
    requestVersion += 1
    predictionRows.value = []
    selectedPredictionFeature.value = null
    predictionLoading.value = false
  }

  return {
    featureMappings,
    predictionRows,
    predictionReady,
    selectedPredictionFeature,
    predictionLoading,
    loadPredictionFeatures,
    loadPredictionForContext,
    clearPrediction
  }
}

function rankedFeatureCandidates(features: PredictionFeatureMapping[], context: PredictionContext) {
  return features
    .filter(feature => Number(feature.enabled ?? 1) === 1)
    .filter(isPredictedTargetFeature)
    .filter(feature => !context.metricCode || sameMetric(feature.sourceMetricCode, context.metricCode))
    .map(feature => ({ feature, score: featureScore(feature, context) }))
    .filter(item => item.score > 0)
    .sort((a, b) => b.score - a.score || Number(a.feature.featureOrder || 0) - Number(b.feature.featureOrder || 0))
    .map(item => item.feature)
}

function isPredictedTargetFeature(feature: PredictionFeatureMapping) {
  return Number(feature.predictionTarget) === 1
}

function featureScore(feature: PredictionFeatureMapping, context: PredictionContext) {
  let score = 0
  if (sameNumber(feature.instrumentId, context.instrumentId)) score += 120
  if (sameNumber(feature.stationId, context.stationId)) score += 60
  if (sameMetric(feature.sourceMetricCode, context.metricCode)) score += 45
  return score
}

function sameNumber(left?: unknown, right?: unknown) {
  const a = Number(left)
  const b = Number(right)
  return Number.isFinite(a) && Number.isFinite(b) && a === b
}

function sameMetric(left?: unknown, right?: unknown) {
  const a = normalizeMetric(left)
  const b = normalizeMetric(right)
  return Boolean(a && b && a === b)
}

function normalizeMetric(value?: unknown) {
  return String(value || '').toLowerCase().replace(/[^a-z0-9]+/g, '')
}

function timeValue(value?: unknown) {
  const time = value ? new Date(String(value)).getTime() : 0
  return Number.isFinite(time) ? time : 0
}
