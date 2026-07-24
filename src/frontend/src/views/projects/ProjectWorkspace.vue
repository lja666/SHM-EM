<template>
  <section class="em-page workbench-page">
    <el-alert
      v-if="errorMessage"
      type="error"
      show-icon
      :closable="false"
      :title="errorMessage"
    />

    <section class="workbench-kpis">
      <RiskIndicator label="Current Observed Risk" :value="observedRiskName" :meta="`${futureState?.openObservedEventCount ?? observedEvents.length} open observed events`" :tone="riskTone(observedRiskLevel)" interactive @activate="openEvents('OBSERVATION')" />
      <RiskIndicator label="Forecast Risk (Next 2 h)" :value="forecastRiskName" :meta="forecastAssessmentMeta" :tone="forecastRiskLevel === 'normal' ? 'success' : 'forecast'" icon="forecast" interactive @activate="openPredictionRuns" />
      <RiskIndicator label="Earliest Predicted Exceedance" :value="earliestExceedanceText" :meta="earliestLeadText" :tone="futureState?.earliestExceedanceTime ? 'forecast' : 'neutral'" icon="time" interactive @activate="openPredictionRuns" />
      <RiskIndicator label="Latest Prediction Batch" :value="latestBatchTime" :meta="latestBatchMeta" :tone="futureState?.executionEligible ? 'success' : 'warning'" icon="batch" interactive @activate="openPredictionRuns" />
    </section>

    <section class="workbench-grid">
      <main class="shm-card plan-card">
        <div class="card-head">
          <div>
            <h2>Project Plan / Monitoring Points</h2>
          </div>
          <div class="head-actions">
            <el-button size="small" @click="router.push(`/projects/${projectId}/topology`)">Object Topology</el-button>
          </div>
        </div>
        <div class="plan-surface point-layout-map">
          <img
            class="point-layout-image"
            src="/pit-point-layout.png"
            alt="Project Monitoring Point Layout"
            @error="imageReady = false"
            @load="imageReady = true"
          />
          <div v-if="!imageReady" class="map-fallback">
            <div class="fallback-block block-a">Zone A</div>
            <div class="fallback-block block-b">Zone B</div>
            <div class="fallback-lab">Integrated Laboratory</div>
          </div>
          <button
            v-for="site in sitePoints"
            :key="site.siteNo"
            type="button"
            class="site-zone"
            :class="[site.levelClass, { selected: site.selected }]"
            :style="{ left: `${site.x}%`, top: `${site.y}%`, width: `${siteBoxWidth}%`, height: `${siteBoxHeight}%` }"
            :title="site.title"
            @click="selectSite(site)"
          >
            <span v-if="site.forecastLevel !== 'normal'" :class="['forecast-ring', site.forecastLevel]" />
          </button>
        </div>
        <div class="map-legend">
          <span><i class="normal"></i>Normal</span>
          <span><i class="yellow"></i>Level-3 Warning</span>
          <span><i class="orange"></i>Level-2 Warning</span>
          <span><i class="red"></i>Level-1 Warning</span>
          <span><i class="forecast"></i>Forecast Risk</span>
        </div>
      </main>

      <aside class="shm-card site-card">
        <div class="card-head">
          <div>
            <h2>Current Point Overview</h2>
          </div>
          <span :class="['risk-badge', siteRiskBadgeClass]">{{ levelName(selectedSitePoint.level) }}</span>
        </div>
        <div class="site-overview-grid">
          <article>
            <span>Latest Observed Value</span>
            <strong>{{ selectedTrendLatest }} {{ selectedTrendUnit }}</strong>
          </article>
          <article>
            <span>Delta</span>
            <strong :class="{ up: selectedTrendDelta >= 0, down: selectedTrendDelta < 0 }">{{ selectedTrendDeltaText }} {{ selectedTrendUnit }}</strong>
          </article>
          <article>
            <span>Threshold Status</span>
            <strong>{{ selectedThresholdText }}</strong>
          </article>
          <article>
            <span>Forecast Peak</span>
            <strong>{{ selectedForecastPeak }} {{ selectedTrendUnit }}</strong>
          </article>
          <article>
            <span>Monitoring Devices</span>
            <strong>{{ selectedDeviceHint }}</strong>
          </article>
          <article>
            <span>Data Entry</span>
            <el-button text type="primary" @click="openObservationPrediction">Open Analysis</el-button>
          </article>
        </div>
        <div class="site-source">
          <span>Feature</span><strong>{{ selectedFeature?.featureLabel || 'No mapped forecast feature' }}</strong>
          <span>Model / Batch</span><strong>{{ selectedPredictionSource }}</strong>
        </div>
      </aside>

      <section class="shm-card trend-card">
        <div class="card-head">
          <div>
            <h2>Observed & Forecast Trend</h2>
          </div>
          <div class="trend-actions">
            <PredictionBatchBadge :batch="latestBatch" :completeness="latestCompleteness" />
            <el-button text type="primary" @click="openObservationPrediction">Open Analysis</el-button>
          </div>
        </div>
        <div v-loading="seriesLoading" class="trend-linked-panel">
          <div class="trend-summary">
            <div>
              <span>Current Value</span>
              <strong>{{ selectedTrendLatest }} {{ selectedTrendUnit }}</strong>
            </div>
            <div>
              <span>Delta</span>
              <strong :class="{ up: selectedTrendDelta >= 0, down: selectedTrendDelta < 0 }">{{ selectedTrendDeltaText }} {{ selectedTrendUnit }}</strong>
            </div>
            <div>
              <span>Forecast Peak</span>
              <strong class="forecast-value">{{ selectedForecastPeak }} {{ selectedTrendUnit }}</strong>
            </div>
            <div>
              <span>Lead Time</span>
              <strong>{{ selectedLeadTime }}</strong>
            </div>
          </div>
          <div class="trend-chart-kpi">
            <UnifiedSeriesChart
              :points="selectedSeries"
              :unit="selectedTrendUnit"
              :warning-threshold="selectedTrendWarning"
              :first-exceedance-time="selectedFirstExceedanceTime"
            />
          </div>
        </div>
      </section>

      <section class="shm-card response-card">
        <div class="card-head">
          <div>
            <h2>Events and Response</h2>
          </div>
          <el-link type="primary" @click="router.push(`/projects/${projectId}/response/workflows`)">Response and Evidence</el-link>
        </div>
        <div class="response-layout">
          <div class="selected-event-list">
            <button
              v-for="event in selectedSiteEvents.slice(0, 3)"
              :key="event.id || event.eventCode"
              type="button"
              @click="openEvent(event)"
            >
              <el-tag size="small" :type="isForecastEvent(event) ? 'warning' : 'info'">{{ isForecastEvent(event) ? 'Forecast' : 'Observed' }}</el-tag>
              <span :class="['risk-badge', eventRiskClass(event.eventLevel)]">{{ levelName(event.eventLevel) }}</span>
              <strong>{{ eventTitle(event) }}</strong>
              <small>{{ event.metricCode || '-' }} · {{ formatTime(event.detectedAt) }}</small>
            </button>
            <el-empty v-if="!selectedSiteEvents.length && !loading" description="No events for the current point" />
          </div>
          <div class="response-actions">
            <button type="button" @click="router.push({ path: `/projects/${projectId}/response/workflows`, query: { tab: 'evidence' } })">
              <span class="doc-thumb">PDF</span>
              <strong>Report Instance</strong>
              <small>{{ numberOf(summary.reportInstanceCount) }} reports</small>
            </button>
            <button type="button" @click="router.push({ path: `/projects/${projectId}/response/workflows`, query: { tab: 'tasks' } })">
              <span class="doc-thumb mail">MSG</span>
              <strong>Notification Task</strong>
              <small>{{ numberOf(summary.notificationTaskCount) }} records</small>
            </button>
          </div>
        </div>
      </section>
    </section>
  </section>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useProjectContext } from '../../composables/useProjectContext'
import { getProjectContext, getProjectFutureState } from '../../api/modules/project'
import { listEvents } from '../../api/modules/event'
import { getPredictionBatchDetail, getPredictionEventTrace, listPredictionBatches, listPredictionFeatures, listUnifiedSeries } from '../../api/modules/prediction'
import RiskIndicator from '../../components/RiskIndicator.vue'
import PredictionBatchBadge from '../../components/PredictionBatchBadge.vue'
import UnifiedSeriesChart from '../../components/UnifiedSeriesChart.vue'
import type { EventPredictionTrace, MetricSeriesPoint, MonitoringEvent, PredictionBatch, PredictionCompleteness, PredictionFeatureMapping, ProjectCard, ProjectContext as ProjectContextPayload, ProjectFutureState } from '../../types/engineering'

const router = useRouter()
const { projectId, app } = useProjectContext()
const loading = ref(false)
const errorMessage = ref('')
const context = ref<ProjectContextPayload>({})
const events = ref<MonitoringEvent[]>([])
const predictionBatches = ref<PredictionBatch[]>([])
const predictionFeatures = ref<PredictionFeatureMapping[]>([])
const selectedSeries = ref<MetricSeriesPoint[]>([])
const predictionTraces = ref<Record<number, EventPredictionTrace>>({})
const latestCompleteness = ref<PredictionCompleteness>()
const futureState = ref<ProjectFutureState>()
const seriesLoading = ref(false)
const imageReady = ref(true)
const siteBoxWidth = 7.2
const siteBoxHeight = 10.2
const siteCoordinates = [
  { siteNo: '1', x: 3.7, y: 37.5 },
  { siteNo: '2', x: 15.7, y: 8.7 },
  { siteNo: '3', x: 37.0, y: 8.8 },
  { siteNo: '4', x: 50.7, y: 8.5 },
  { siteNo: '5', x: 75.1, y: 8.7 },
  { siteNo: '6', x: 80.6, y: 37.3 },
  { siteNo: '7', x: 76.2, y: 64.7 },
  { siteNo: '8', x: 37.4, y: 64.1 },
  { siteNo: '9', x: 10.1, y: 65.0 }
]
const levelRank: Record<string, number> = { normal: 0, yellow: 1, orange: 2, red: 3 }
const selectedSiteNo = ref(siteCoordinates[0].siteNo)

const projectDisplay = computed<ProjectCard>(() => context.value.projectDisplay || {})
const summary = computed<ProjectCard>(() => context.value.summary || context.value.projectDisplay || {})
const observedEvents = computed(() => events.value.filter(event => !isForecastEvent(event)))
const forecastEvents = computed(() => events.value.filter(isForecastEvent))
const observedRiskLevel = computed(() => futureState.value?.observedRiskLevel ? levelClassOf(futureState.value.observedRiskLevel) : highestLevel(observedEvents.value))
const forecastRiskLevel = computed(() => levelClassOf(futureState.value?.forecastRiskLevel))
const observedRiskName = computed(() => levelName(observedRiskLevel.value))
const forecastRiskName = computed(() => futureState.value ? levelName(forecastRiskLevel.value) : 'Unavailable')
const latestBatch = computed(() => predictionBatches.value[0])
const latestBatchTime = computed(() => futureState.value?.baseTime ? formatTime(futureState.value.baseTime).slice(5, 16) : 'No Batch')
const latestBatchMeta = computed(() => {
  if (!futureState.value) return 'Prediction has not run'
  const gate = futureState.value.executionGate
  return futureState.value.executionEligible
    ? `${gate?.actualPointCount || 0}/${gate?.expectedPointCount || 0} outputs · executable`
    : `${gate?.actualPointCount || 0}/${gate?.expectedPointCount || 0} outputs · execution blocked`
})
const forecastAssessmentMeta = computed(() => futureState.value
  ? `${futureState.value.assessedFeatureCount || 0} assessed · ${futureState.value.unassessedFeatureCount || 0} unassessed`
  : 'Future state unavailable')
const earliestExceedanceText = computed(() => futureState.value?.earliestExceedanceTime ? formatTime(futureState.value.earliestExceedanceTime).slice(5, 16) : 'None')
const earliestLeadText = computed(() => {
  if (!futureState.value?.earliestExceedanceTime || !futureState.value.baseTime) return 'No forecast threshold crossing'
  const lead = Math.round((new Date(futureState.value.earliestExceedanceTime).getTime() - new Date(futureState.value.baseTime).getTime()) / 60000)
  return `Lead time ${lead} min`
})
const stationSiteMap = computed(() => {
  const map = new Map<number, string>()
  predictionFeatures.value.forEach(feature => {
    const siteNo = featureSiteNo(feature)
    if (feature.stationId && siteNo) map.set(Number(feature.stationId), siteNo)
  })
  return map
})
function levelMap(rows: MonitoringEvent[]) {
  const map = new Map<string, keyof typeof levelRank>()
  rows.forEach(event => {
    const siteNo = siteNoOf(event)
    if (!siteNo) return
    const level = levelClassOf(event.eventLevel)
    const current = map.get(siteNo) || 'normal'
    if (levelRank[level] > levelRank[current]) map.set(siteNo, level)
  })
  return map
}
const observedSiteLevelMap = computed(() => levelMap(observedEvents.value))
const forecastSiteLevelMap = computed(() => {
  const map = new Map<string, keyof typeof levelRank>()
  ;(futureState.value?.stations || []).forEach(station => {
    const siteNo = station.stationId ? stationSiteMap.value.get(Number(station.stationId)) : undefined
    if (!siteNo) return
    const level = levelClassOf(station.riskLevel)
    const current = map.get(siteNo) || 'normal'
    if (levelRank[level] > levelRank[current]) map.set(siteNo, level)
  })
  return map
})
const sitePoints = computed(() => siteCoordinates.map(site => {
  const observedLevel = observedSiteLevelMap.value.get(site.siteNo) || 'normal'
  const forecastLevel = forecastSiteLevelMap.value.get(site.siteNo) || 'normal'
  const level = levelRank[forecastLevel] > levelRank[observedLevel] ? forecastLevel : observedLevel
  return {
    ...site,
    level,
    observedLevel,
    forecastLevel,
    selected: selectedSiteNo.value === site.siteNo,
    levelClass: observedLevel,
    title: `Point No. ${site.siteNo} · observed ${levelName(observedLevel)} · forecast ${levelName(forecastLevel)}`
  }
}))
const selectedSitePoint = computed(() => sitePoints.value.find(site => site.siteNo === selectedSiteNo.value) || sitePoints.value[0])
const selectedSiteEvents = computed(() => events.value.filter(event => siteNoOf(event) === selectedSiteNo.value))
const siteRiskBadgeClass = computed(() => eventRiskClass(selectedSitePoint.value.level))
const selectedFeature = computed(() => {
  const siteFeatures = predictionFeatures.value.filter(feature => featureSiteNo(feature) === selectedSiteNo.value)
  const eventStationIds = new Set(selectedSiteEvents.value.map(event => Number(event.stationId)).filter(Boolean))
  return siteFeatures.find(feature => eventStationIds.has(Number(feature.stationId)) && String(feature.targetType).toLowerCase() === 'settlement')
    || siteFeatures.find(feature => eventStationIds.has(Number(feature.stationId)))
    || siteFeatures.find(feature => String(feature.targetType).toLowerCase() === 'settlement')
    || siteFeatures[0]
})
const observedSeries = computed(() => selectedSeries.value.filter(point => point.sourceType === 'OBSERVATION'))
const forecastSeries = computed(() => selectedSeries.value.filter(point => point.sourceType === 'PREDICTION'))
const selectedTrendUnit = computed(() => String(selectedSeries.value.find(point => point.unit)?.unit || ''))
const selectedTrendLatest = computed(() => numberText(observedSeries.value[observedSeries.value.length - 1]?.value))
const selectedTrendDelta = computed(() => {
  if (observedSeries.value.length < 2) return 0
  return Number((Number(observedSeries.value[observedSeries.value.length - 1]?.value) - Number(observedSeries.value[0]?.value)).toFixed(2))
})
const selectedTrendDeltaText = computed(() => `${selectedTrendDelta.value >= 0 ? '+' : ''}${selectedTrendDelta.value.toFixed(1)}`)
const selectedForecastPeak = computed(() => numberText(forecastSeries.value.reduce((peak, point) => Math.max(peak, Number(point.value)), Number.NEGATIVE_INFINITY)))
const selectedTrendWarning = computed(() => selectedSiteEvents.value.find(event => Number(event.thresholdValue) > 0)?.thresholdValue)
const selectedThresholdText = computed(() => {
  if (selectedTrendWarning.value === undefined) return 'No active threshold'
  return Number(selectedTrendLatest.value) >= Number(selectedTrendWarning.value) ? 'Exceeds threshold' : 'Within threshold'
})
const selectedDeviceHint = computed(() => {
  const target = String(selectedFeature.value?.targetType || '')
  return target ? target.replace(/_/g, ' ') : 'No mapped device'
})
const selectedTrace = computed(() => selectedSiteEvents.value.map(event => event.id ? predictionTraces.value[event.id] : undefined).find(Boolean))
const selectedFutureContributors = computed(() => (futureState.value?.stations || [])
  .filter(station => station.stationId && stationSiteMap.value.get(Number(station.stationId)) === selectedSiteNo.value)
  .flatMap(station => station.contributors || []))
const selectedFirstExceedanceTime = computed(() => selectedFutureContributors.value
  .map(item => item.firstExceedanceTime)
  .filter((value): value is string => Boolean(value))
  .sort()[0] || selectedTrace.value?.firstExceedanceTime)
const selectedLeadTime = computed(() => {
  if (!selectedFirstExceedanceTime.value || !futureState.value?.baseTime) return '-'
  return `${Math.round((new Date(selectedFirstExceedanceTime.value).getTime() - new Date(futureState.value.baseTime).getTime()) / 60000)} min`
})
const selectedPredictionSource = computed(() => {
  const forecast = forecastSeries.value[0]
  return forecast ? `${forecast.sourceModelCode || '-'} / ${forecast.sourceBatchCode || '-'}` : 'No forecast series'
})
async function load() {
  if (!projectId.value) return
  loading.value = true
  errorMessage.value = ''
  try {
    const [projectContext, eventRows, batches, features, projectFutureState] = await Promise.all([
      getProjectContext(projectId.value),
      listEvents({ projectId: projectId.value, limit: 100 }),
      listPredictionBatches({ projectId: projectId.value, limit: 10 }),
      listPredictionFeatures({ projectId: projectId.value, limit: 500 }),
      getProjectFutureState(projectId.value, { horizonMinutes: 120, executionMode: 'OPERATIONAL' })
    ])
    context.value = projectContext
    events.value = eventRows
    predictionBatches.value = batches
    predictionFeatures.value = features
    futureState.value = projectFutureState
    if (batches[0]?.id) {
      const detail = await getPredictionBatchDetail(batches[0].id)
      latestCompleteness.value = detail.completeness
    }
    await loadPredictionTraces()
    await loadSiteSeries()
    app.setCurrentProject(projectId.value, String(projectDisplay.value.displayName || projectDisplay.value.projectName || summary.value.projectName || 'Project Workspace'))
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : 'Project workspace API request failed'
    context.value = {}
    events.value = []
    predictionBatches.value = []
    predictionFeatures.value = []
    selectedSeries.value = []
    predictionTraces.value = {}
    latestCompleteness.value = undefined
    futureState.value = undefined
  } finally {
    loading.value = false
  }
}

async function loadPredictionTraces() {
  const rows = await Promise.all(forecastEvents.value
    .filter(event => event.id)
    .slice(0, 10)
    .map(async event => {
      try {
        return [Number(event.id), await getPredictionEventTrace(Number(event.id))] as const
      } catch {
        return undefined
      }
    }))
  predictionTraces.value = Object.fromEntries(rows.filter((row): row is readonly [number, EventPredictionTrace] => Boolean(row)))
}

async function loadSiteSeries() {
  if (!projectId.value || !latestBatch.value?.id || !selectedFeature.value?.featureCode) {
    selectedSeries.value = []
    return
  }
  seriesLoading.value = true
  try {
    selectedSeries.value = await listUnifiedSeries({
      projectId: projectId.value,
      batchId: latestBatch.value.id,
      featureCode: selectedFeature.value.featureCode,
      includeObserved: true,
      maxHorizonMinutes: 120,
      limit: 160
    })
  } finally {
    seriesLoading.value = false
  }
}

function numberOf(value: unknown) {
  const number = Number(value)
  return Number.isFinite(number) ? number : 0
}

function formatTime(value?: unknown) {
  if (!value) return '-'
  return String(value).replace('T', ' ').slice(0, 19)
}

function numberText(value?: unknown) {
  const number = Number(value)
  return Number.isFinite(number) ? number.toFixed(2) : '-'
}

async function selectSite(site: { siteNo: string }) {
  selectedSiteNo.value = site.siteNo
  await loadSiteSeries()
}

function eventTitle(event: MonitoringEvent) {
  if (isForecastEvent(event)) return `Forecast threshold exceeded · ${String(event.metricCode || 'Metric').replace(/_/g, ' ')}`
  return String(event.triggerReason || event.eventType || event.eventCode || 'Monitoring Event')
}

function featureSiteNo(feature: PredictionFeatureMapping) {
  const match = String(feature.featureCode || feature.trainingFeatureCode || '').match(/point([1-9])(?:[^0-9]|$)/i)
  return match?.[1]
}

function siteNoOf(item: { stationId?: number; metricCode?: string; eventCode?: string; eventType?: string; triggerReason?: string }) {
  if (item.stationId && stationSiteMap.value.has(Number(item.stationId))) return stationSiteMap.value.get(Number(item.stationId))
  const text = `${item.metricCode || ''} ${item.eventCode || ''} ${item.eventType || ''} ${item.triggerReason || ''}`
  const match = text.match(/(?:ST[-_ ]?|station|Point|point)?([1-9])(?:No.|#|points|[^0-9]|$)/i)
  return match?.[1]
}

function levelClassOf(level?: unknown): keyof typeof levelRank {
  const key = String(level || '').toLowerCase()
  if (key.includes('red') || key.includes('critical') || key.includes('danger') || key.includes('level 1')) return 'red'
  if (key.includes('orange') || key.includes('warning') || key.includes('level 2')) return 'orange'
  if (key.includes('yellow') || key.includes('notice') || key.includes('level 3')) return 'yellow'
  return 'normal'
}

function eventRiskClass(level?: unknown) {
  const key = String(level || '').toLowerCase()
  if (key.includes('red') || key.includes('critical') || key.includes('danger')) return 'danger'
  if (key.includes('orange') || key.includes('warning')) return 'warning'
  if (key.includes('yellow') || key.includes('notice')) return 'notice'
  return 'success'
}

function levelName(level?: unknown) {
  const key = String(level || '').toLowerCase()
  const map: Record<string, string> = { red: 'Severe', orange: 'High Risk', yellow: 'Medium Risk', blue: 'Low Risk', normal: 'Normal' }
  return map[key] || String(level || 'Event')
}

function highestLevel(rows: MonitoringEvent[]): keyof typeof levelRank {
  return rows.reduce<keyof typeof levelRank>((highest, event) => {
    const level = levelClassOf(event.eventLevel)
    return levelRank[level] > levelRank[highest] ? level : highest
  }, 'normal')
}

function isForecastEvent(event: MonitoringEvent) {
  const source = String(event.sourceType || '').toUpperCase()
  return source === 'FORECAST' || source === 'PREDICTION'
}

function riskTone(level: keyof typeof levelRank): 'danger' | 'warning' | 'success' {
  if (level === 'red') return 'danger'
  if (level === 'orange' || level === 'yellow') return 'warning'
  return 'success'
}

function openEvents(source?: string) {
  router.push({ path: `/projects/${projectId.value}/events`, query: source ? { source } : {} })
}

function openEvent(event: MonitoringEvent) {
  router.push({ path: `/projects/${projectId.value}/events`, query: event.id ? { eventId: String(event.id) } : {} })
}

function openPredictionRuns() {
  router.push(`/projects/${projectId.value}/predictions`)
}

function openObservationPrediction() {
  router.push({
    path: `/projects/${projectId.value}/data/low-frequency`,
    query: {
      station: selectedSiteNo.value,
      featureCode: selectedFeature.value?.featureCode || undefined,
      batchId: latestBatch.value?.id ? String(latestBatch.value.id) : undefined
    }
  })
}

watch(projectId, load, { immediate: true })
</script>

<style scoped>
.workbench-page { gap: 18px; }
.workbench-kpis {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: clamp(10px, 1vw, 16px) !important;
}
.workbench-grid {
  display: grid;
  grid-template-columns: minmax(600px, 1.55fr) minmax(360px, .75fr) !important;
  gap: clamp(10px, 1vw, 16px);
  align-items: stretch;
  min-width: 980px;
}
.shm-card {
  min-width: 0;
  padding: 20px;
  border: 1px solid var(--shm-border);
  border-radius: var(--shm-card-radius);
  background: #fff;
  box-shadow: var(--shm-card-shadow);
}
.plan-card,
.site-card {
  grid-column: auto;
  min-height: 288px;
  padding: 14px;
}
.plan-card { grid-column: 1; }
.site-card { grid-column: 2; }
.trend-card { grid-column: 1; min-height: 390px; }
.response-card { grid-column: 2; min-height: 390px; }
.plan-card,
.site-card,
.trend-card,
.response-card {
  display: flex;
  flex-direction: column;
}
.card-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 14px;
  margin-bottom: 8px;
}
.card-head h2 { margin: 0; color: var(--shm-text-title); font-size: 16px; font-weight: 750; }
.plan-surface {
  container-type: inline-size;
  flex: 1;
  position: relative;
  width: 100%;
  min-height: 0;
  overflow: hidden;
  border: 1px solid var(--shm-border);
  border-radius: 12px;
  background: #fff;
  aspect-ratio: 1672 / 941;
}
:global(.shm-shell .workbench-page .plan-surface) {
  min-height: 0 !important;
}
.point-layout-image {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  object-fit: contain;
  background: #fff;
}
.map-fallback { position: absolute; inset: 0; background: #fff; }
.fallback-block { position: absolute; display: grid; place-items: center; border: 2px solid #8ea6c8; background: repeating-linear-gradient(45deg, #edf2f7, #edf2f7 10px, #e2e8f0 10px, #e2e8f0 20px); color: #334155; font-size: clamp(16px, 1.7vw, 24px); font-weight: 750; }
.block-a { left: 10%; top: 20%; width: 26%; height: 34%; }
.block-b { left: 38%; top: 18%; width: 42%; height: 36%; }
.fallback-lab { position: absolute; right: 5%; top: 26%; writing-mode: vertical-rl; color: #334155; font-weight: 750; }
.site-zone {
  position: absolute;
  z-index: 2;
  padding: 0;
  border: clamp(1px, .14vw, 2px) solid var(--zone-color);
  border-radius: clamp(4px, .5vw, 7px);
  background: var(--zone-bg);
  box-shadow: 0 8px 18px rgba(15,23,42,.12);
  cursor: pointer;
  transition: transform .16s ease, box-shadow .16s ease, background .16s ease;
}
.site-zone::before {
  content: "";
  position: absolute;
  inset: clamp(2px, .28vw, 3px);
  border: 1px solid rgba(255,255,255,.78);
  border-radius: clamp(3px, .35vw, 4px);
  pointer-events: none;
}
.site-zone.normal { --zone-color: #1677ff; --zone-bg: rgba(22,119,255,.1); }
.site-zone.yellow { --zone-color: #d4a300; --zone-bg: rgba(250,204,21,.22); }
.site-zone.orange { --zone-color: #f59e0b; --zone-bg: rgba(245,158,11,.2); }
.site-zone.red { --zone-color: #ef4444; --zone-bg: rgba(239,68,68,.18); }
.site-zone:hover { z-index: 4; transform: scale(1.03); box-shadow: 0 14px 28px rgba(15,23,42,.18); }
.site-zone.selected {
  z-index: 5;
  transform: scale(1.08);
  box-shadow: 0 0 0 3px rgba(22,119,255,.22), 0 16px 30px rgba(15,23,42,.2);
}
.site-zone.selected::after {
  content: "";
  position: absolute;
  left: 50%;
  top: 50%;
  width: 34%;
  height: 34%;
  border-radius: 999px;
  background: var(--zone-color);
  transform: translate(-50%, -50%);
}
.forecast-ring {
  position: absolute;
  z-index: 3;
  inset: -7px;
  border: 3px dashed #7c3aed;
  border-radius: 10px;
  pointer-events: none;
}
.forecast-ring.yellow { border-color: #8b5cf6; }
.forecast-ring.orange { border-color: #7c3aed; }
.forecast-ring.red { border-color: #dc2626; }
.map-legend {
  display: flex;
  flex-wrap: wrap;
  gap: 18px;
  margin-top: 6px;
  color: var(--shm-text-secondary);
  font-size: 16px;
}
.map-legend span { display: inline-flex; align-items: center; gap: 6px; }
.map-legend i { width: 9px; height: 9px; border-radius: 999px; background: var(--shm-success); }
.map-legend i.normal { background: #1677ff; }
.map-legend i.yellow { background: #facc15; }
.map-legend i.orange { background: #f59e0b; }
.map-legend i.red { background: #ef4444; }
.map-legend i.forecast { background: transparent; border: 2px dashed #7c3aed; }
.site-overview-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 6px;
}
.site-overview-grid article {
  min-width: 0;
  min-height: 48px;
  padding: 7px 9px;
  border: 1px solid #e8eef7;
  border-radius: 10px;
  background: #f8fafc;
}
.site-overview-grid span,
.site-overview-grid strong {
  display: block;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.site-overview-grid span {
  margin-bottom: 3px;
  color: var(--shm-text-secondary);
  font-size: 13px;
}
.site-overview-grid strong {
  color: var(--shm-text-title);
  font-size: clamp(16px, 1.25vw, 20px);
  font-weight: 800;
}
.site-overview-grid strong.up { color: var(--shm-danger); }
.site-overview-grid strong.down { color: var(--shm-success); }
.site-overview-grid :deep(.el-button) {
  height: auto;
  min-height: 24px;
  padding: 0;
  font-weight: 750;
}
.site-source {
  display: grid;
  grid-template-columns: 92px minmax(0, 1fr);
  gap: 7px 10px;
  padding: 12px;
  border-top: 1px solid var(--shm-border);
}
.site-source span { color: var(--shm-text-secondary); font-size: 12px; }
.site-source strong { min-width: 0; overflow: hidden; color: var(--shm-text-main); font-size: 12px; text-overflow: ellipsis; white-space: nowrap; }
.trend-actions { min-width: 0; display: flex; align-items: center; gap: 8px; }
.trend-actions :deep(.batch-badge) { width: min(340px, 32vw); }
.forecast-value { color: #7c3aed !important; }
.risk-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 54px;
  height: 26px;
  padding: 0 9px;
  border: 1px solid transparent;
  border-radius: 999px;
  font-size: 16px;
  font-weight: 750;
}
.risk-badge.success { color: var(--shm-success); background: #ecfdf3; border-color: #bbf7d0; }
.risk-badge.notice { color: #ca8a04; background: #fefce8; border-color: #fde68a; }
.risk-badge.warning { color: var(--shm-orange); background: #fff7ed; border-color: #fed7aa; }
.risk-badge.danger { color: var(--shm-danger); background: #fef2f2; border-color: #fecaca; }
.trend-linked-panel {
  flex: 1;
  display: grid;
  grid-template-rows: auto minmax(0, 1fr);
  gap: 10px;
  min-height: 260px;
  padding: 14px;
  border: 1px solid var(--shm-border);
  border-radius: 12px;
  background: linear-gradient(180deg, #fff, #f8fafc);
}
.trend-summary {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 10px;
}
.trend-summary div {
  min-width: 0;
  min-height: 68px;
  padding: 11px 12px;
  border: 1px solid #e8eef7;
  border-radius: 10px;
  background: #fff;
}
.trend-summary span {
  display: block;
  margin-bottom: 6px;
  color: var(--shm-text-secondary);
  font-size: 16px;
}
.trend-summary strong {
  display: block;
  overflow: hidden;
  color: var(--shm-text-title);
  font-size: clamp(15px, 1.2vw, 19px);
  font-weight: 800;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.trend-summary strong.up { color: var(--shm-danger); }
.trend-summary strong.down { color: var(--shm-success); }
.trend-chart-kpi {
  display: block;
  min-height: 0;
  padding: 8px 10px;
  border: 1px solid #e8eef7;
  border-radius: 12px;
  background: #fff;
}
.response-layout {
  flex: 1;
  display: grid;
  grid-template-rows: minmax(0, 1fr) auto;
  gap: 12px;
  min-height: 0;
}
.selected-event-list {
  display: grid;
  align-content: start;
  gap: 10px;
  min-height: 0;
  overflow-y: auto;
  padding-right: 4px;
}
.selected-event-list button,
.response-actions button {
  min-width: 0;
  border: 1px solid var(--shm-border);
  border-radius: 10px;
  background: #f8fafc;
  text-align: left;
  cursor: pointer;
}
.selected-event-list button {
  display: grid;
  grid-template-columns: 74px minmax(0, 1fr);
  gap: 8px 12px;
  padding: 12px;
}
.selected-event-list strong,
.selected-event-list small,
.response-actions strong,
.response-actions small {
  display: block;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.selected-event-list small {
  grid-column: 2;
  color: var(--shm-text-secondary);
}
.response-actions {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
  width: 100%;
}
.response-actions button {
  display: grid;
  gap: 8px;
  padding: 10px;
  background: #fff;
}
.selected-event-list::-webkit-scrollbar {
  width: 8px;
  height: 8px;
}
.selected-event-list::-webkit-scrollbar-track {
  border-radius: 999px;
  background: #eef3f9;
}
.selected-event-list::-webkit-scrollbar-thumb {
  border: 2px solid #eef3f9;
  border-radius: 999px;
  background: #b8c6d8;
}
.selected-event-list::-webkit-scrollbar-thumb:hover {
  background: #94a3b8;
}
.doc-thumb {
  display: grid;
  place-items: center;
  width: 100%;
  height: 56px;
  border-radius: 8px;
  background: #eef4ff;
  color: var(--shm-primary);
  font-weight: 800;
}
.doc-thumb.image { background: #f0fdf4; color: var(--shm-success); }
.doc-thumb.mail { background: #fff7ed; color: var(--shm-orange); }
.response-actions strong { color: var(--shm-text-main); }
.response-actions small { color: var(--shm-text-secondary); }
</style>


