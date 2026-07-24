<template>
  <section class="observation-workbench">
    <header class="observation-header">
      <h1>Observation & Prediction</h1>
      <el-button :icon="Coin" @click="router.push(`/projects/${projectId}/predictions`)">Prediction Runs</el-button>
    </header>
    <section class="filter-bar">
      <label>
        <span>Point</span>
        <el-select v-model="selectedSiteKey" filterable @change="onSiteChange">
          <el-option v-for="site in siteOptions" :key="site.key" :label="site.label" :value="site.key" />
        </el-select>
      </label>
      <label>
        <span>Instrument Type</span>
        <el-select v-model="selectedInstrumentType" filterable clearable @change="onInstrumentTypeChange">
          <el-option v-for="item in instrumentTypeOptions" :key="item.value" :label="item.label" :value="item.value" />
        </el-select>
      </label>
      <label>
        <span>Instrument</span>
        <el-select v-model="selectedInstrumentKey" filterable @change="onInstrumentChange">
          <el-option v-for="item in instrumentOptions" :key="item.key" :label="item.label" :value="item.key" />
        </el-select>
      </label>
      <label>
        <span>Metric</span>
        <el-select v-model="selectedMetricKey" filterable @change="onMetricChange">
          <el-option v-for="item in metricOptions" :key="item.key" :label="item.label" :value="item.key" />
        </el-select>
      </label>
      <label class="range-field">
        <span>Time Range</span>
        <el-date-picker
          v-model="range"
          type="datetimerange"
          value-format="YYYY-MM-DD HH:mm:ss"
          start-placeholder="Start Time"
          end-placeholder="End Time"
          @change="syncRange"
        />
      </label>
      <label>
        <span>Data Quality</span>
        <el-select v-model="qualityFilter">
          <el-option label="All" value="" />
          <el-option label="Good" value="OK" />
          <el-option label="Needs Review" value="BAD" />
        </el-select>
      </label>
      <el-button type="primary" :icon="Search" :loading="loading" @click="loadObservations">Query</el-button>
      <el-button :icon="Refresh" @click="resetFilters">Reset</el-button>
      <el-button :icon="Download" @click="exportRows">Export</el-button>
    </section>

    <section class="data-summary-strip">
      <article>
        <span>Current Observed</span>
        <strong>{{ latestValueText }}</strong>
      </article>
      <article>
        <span>Forecast Peak</span>
        <strong>{{ forecastPeakText }}</strong>
      </article>
      <article>
        <span>First Exceedance</span>
        <strong>{{ firstExceedanceText }}</strong>
      </article>
      <article>
        <span>Lead Time</span>
        <strong>{{ leadTimeText }}</strong>
      </article>
      <article>
        <span>Prediction Window</span>
        <strong>{{ predictionWindowText }}</strong>
      </article>
      <article>
        <span>Related Events</span>
        <strong>{{ relatedEvents.length }}</strong>
      </article>
    </section>

    <section class="main-grid">
      <aside v-loading="objectLoading" class="object-tree-card panel-card">
        <div class="panel-head">
          <div>
            <strong>Object Tree</strong>
          </div>
          <el-segmented v-model="navMode" :options="navModeOptions" size="small" />
        </div>
        <el-input v-model="keyword" placeholder="Search object tree" clearable>
          <template #prefix><el-icon><Search /></el-icon></template>
        </el-input>
        <el-tree
          v-if="objectTreeData.length"
          class="object-tree"
          :data="objectTreeData"
          node-key="id"
          :props="{ children: 'children', label: 'label' }"
          :default-expanded-keys="defaultExpandedKeys"
          :current-node-key="currentNodeKey"
          highlight-current
          @node-click="onTreeNodeClick"
        >
          <template #default="{ data }">
            <div class="tree-node" :class="{ leaf: data.kind === 'instrument' }">
              <div class="tree-node-main">
                <span class="node-label">{{ data.label }}</span>
                <small v-if="data.meta">{{ data.meta }}</small>
              </div>
              <span v-if="data.count !== undefined" class="node-count">{{ data.count }}</span>
            </div>
          </template>
        </el-tree>
        <el-empty v-else description="No Objects" />
      </aside>

      <main class="trend-card panel-card">
        <div class="trend-toolbar">
          <div class="data-tabs">
            <button type="button" :class="{ active: activeDataMode === 'low' }" :disabled="isAccelerometer" @click="setDataMode('low')">Low-Frequency Trend</button>
            <button type="button" :class="{ active: activeDataMode === 'high' }" :disabled="!isAccelerometer" @click="setDataMode('high')">High-Frequency Waveform</button>
          </div>
          <div class="chart-actions">
            <el-segmented v-if="activeDataMode === 'low'" v-model="valueMode" :options="valueModeOptions" size="small" />
            <PredictionBatchBadge v-if="activeDataMode === 'low' && predictionBatch" class="trend-batch" :batch="predictionBatch" />
            <el-tag v-if="activeDataMode === 'low'" size="small" :type="dataWindowMode === 'realtime' ? 'success' : 'warning'">{{ dataWindowLabel }}</el-tag>
          </div>
        </div>
        <template v-if="activeDataMode === 'low'">
          <div class="chart-section primary-chart">
            <div class="chart-title">
              <strong>{{ metricDisplayName }} ({{ unit || '-' }})</strong>
              <small v-if="selectedPredictionFeature">{{ predictionFeatureText }}</small>
            </div>
            <UnifiedSeriesChart
              :points="unifiedPoints"
              :unit="unit"
              :warning-threshold="warningThreshold"
              :alarm-threshold="alarmThreshold"
              :first-exceedance-time="firstExceedance?.futureTime"
            />
          </div>
          <div class="chart-section rate-chart">
            <div class="sub-chart-head">
              <strong>Change Rate ({{ rateUnit || '-' }})</strong>
              <div>
                <span>Statistics Method</span>
                <el-select v-model="rateMode" size="small">
                  <el-option label="Instant Change Rate" value="instant" />
                  <el-option label="Cumulative Change Rate" value="total" />
                </el-select>
              </div>
            </div>
            <LineChart :x-data="xData" :series="rateSeries" :y-name="rateUnit" variant="rate" />
          </div>
        </template>
        <template v-else>
          <div class="chart-section waveform-chart">
            <div class="chart-title">
              <strong>Acceleration Waveform ({{ waveformUnit }})</strong>
            </div>
            <LineChart :x-data="waveformXData" :series="waveformSeries" :y-name="waveformUnit" variant="waveform" />
          </div>
          <div class="waveform-stats">
            <article><span>PGA</span><strong>{{ waveformFeature.pga }}</strong></article>
            <article><span>RMS</span><strong>{{ waveformFeature.rms }}</strong></article>
            <article><span>Peak Axis</span><strong>{{ waveformFeature.axis }}</strong></article>
          </div>
        </template>
      </main>

      <aside class="metric-card panel-card">
        <div class="panel-head compact">
          <strong>Current Metric Status</strong>
        </div>
        <section class="metric-section metric-core">
          <div><span>Metric Name</span><strong>{{ metricDisplayName }}</strong></div>
          <div><span>Current Value</span><strong>{{ latestValueText }}</strong></div>
          <div><span>Latest Collection</span><strong>{{ latestObservationTime }}</strong></div>
        </section>
        <section class="metric-section threshold-list">
          <div><i class="warning"></i><span>Warning Threshold</span><strong>{{ thresholdText }}</strong></div>
          <div><i class="alarm"></i><span>Alarm Threshold</span><strong>{{ alarmText }}</strong></div>
        </section>
        <section class="metric-section metric-meta">
          <div><span>Value Mode</span><strong>{{ valueMode === 'ENGINEERING' ? 'Engineering' : 'Raw' }}</strong></div>
          <div><span>Conversion</span><strong>{{ conversionStatusText }}</strong></div>
          <div><span>Formula Version</span><strong>{{ conversionVersionText }}</strong></div>
          <div><span>Related Rule</span><strong>{{ selectedMetric?.code || '-' }}</strong></div>
          <div><span>Data Window</span><strong>{{ dataWindowLabel }}</strong></div>
          <div><span>Prediction Window</span><strong v-loading="predictionLoading">{{ predictionWindowText }}</strong></div>
          <div><span>Data Quality</span><strong><el-tag size="small" :type="qualityType">{{ qualitySummary }}</el-tag></strong></div>
        </section>
        <section class="metric-section forecast-insights">
          <div><span>Forecast Peak</span><strong>{{ forecastPeakText }}</strong></div>
          <div><span>First Exceedance</span><strong>{{ firstExceedanceText }}</strong></div>
          <div><span>Lead Time</span><strong>{{ leadTimeText }}</strong></div>
          <div><span>Model</span><strong>{{ predictionModelText }}</strong></div>
        </section>
        <section class="metric-section recent-stat">
          <strong>Recent Statistics</strong>
          <div><span>Minimum Value</span><b>{{ minValueText }}</b></div>
          <div><span>Max</span><b>{{ maxValueText }}</b></div>
          <div><span>Mean</span><b>{{ avgValueText }}</b></div>
          <div><span>Standard Deviation</span><b>{{ stdValueText }}</b></div>
        </section>
      </aside>

      <section class="detail-tabs-card panel-card">
        <el-tabs v-model="activeDetailTab" class="detail-tabs">
          <el-tab-pane label="Observation Details" name="records">
            <el-table v-loading="loading" :data="filteredRows" height="330" stripe>
              <el-table-column prop="observedAt" label="Time" min-width="170" />
              <el-table-column label="Point" min-width="120">
                <template #default>{{ selectedSiteLabel }}</template>
              </el-table-column>
              <el-table-column label="Instrument" min-width="130">
                <template #default>{{ selectedInstrument?.code || '-' }}</template>
              </el-table-column>
              <el-table-column label="Metric" min-width="130">
                <template #default="{ row }">{{ metricName(row.metricCode) }}</template>
              </el-table-column>
              <el-table-column label="Value" width="120">
                <template #default="{ row }">{{ valueText(observationValue(row), observationUnit(row)) }}</template>
              </el-table-column>
              <el-table-column label="Unit" width="80">
                <template #default="{ row }">{{ observationUnit(row) }}</template>
              </el-table-column>
              <el-table-column label="Quality" width="90">
                <template #default="{ row }"><el-tag size="small" :type="isGoodQuality(row) ? 'success' : 'warning'">{{ isGoodQuality(row) ? 'Good' : 'Review' }}</el-tag></template>
              </el-table-column>
              <el-table-column label="Source" width="110">
                <template #default>Automatic Collection</template>
              </el-table-column>
            </el-table>
          </el-tab-pane>
          <el-tab-pane :label="`Related Events ${relatedEvents.length}`" name="events">
            <div class="event-pane-head">
              <strong>Event Association</strong>
              <el-button text type="primary" @click="router.push(`/projects/${projectId}/events`)">View All</el-button>
            </div>
            <div class="event-list">
              <article v-for="item in relatedEvents" :key="item.id || item.eventCode">
                <el-tag size="small" :type="eventTagType(item.eventLevel)">{{ levelName(item.eventLevel) }}</el-tag>
                <div>
                  <strong>{{ item.triggerReason || item.eventType || 'Monitoring Warning' }}</strong>
                  <small>{{ item.detectedAt || '-' }} · {{ item.metricCode || '-' }}</small>
                </div>
                <span>{{ item.eventStatus || 'open' }}</span>
              </article>
              <el-empty v-if="!relatedEvents.length" description="No Related Events" />
            </div>
          </el-tab-pane>
          <el-tab-pane label="Data Sources and Rules" name="source">
            <div class="source-rule-grid">
              <article><span>Data Source Code</span><strong>{{ selectedRegistry?.code || '-' }}</strong></article>
              <article><span>Metric Code</span><strong>{{ selectedMetric?.code || '-' }}</strong></article>
              <article><span>Instrument Type</span><strong>{{ instrumentTypeName(selectedInstrument?.instrumentType) }}</strong></article>
              <article><span>Warning Threshold</span><strong>{{ thresholdText }}</strong></article>
              <article><span>Alarm Threshold</span><strong>{{ alarmText }}</strong></article>
            </div>
          </el-tab-pane>
        </el-tabs>
      </section>
    </section>
  </section>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { Coin, Download, Refresh, Search } from '@element-plus/icons-vue'
import LineChart from '../../components/LineChart.vue'
import UnifiedSeriesChart from '../../components/UnifiedSeriesChart.vue'
import PredictionBatchBadge from '../../components/PredictionBatchBadge.vue'
import { useProjectContext } from '../../composables/useProjectContext'
import { getProjectObjectTree } from '../../api/modules/project'
import { listEvents } from '../../api/modules/event'
import { listEventRules } from '../../api/modules/eventRule'
import { listLowFrequencyObservations } from '../../api/modules/observation'
import { listAccelerationWaveforms } from '../../api/modules/acceleration'
import { usePredictionTrend } from '../../composables/usePredictionTrend'
import type { AccelerationWaveform, EventRule, InstrumentNode, LowFrequencyObservation, MetricNode, MetricSeriesPoint, MonitoringEvent, PredictionBatch, ProjectObjectTree, RegistryNode, StationNode } from '../../types/engineering'

interface TreeNode {
  id: string
  label: string
  kind: 'site' | 'type' | 'instrument'
  meta?: string
  count?: number
  station?: StationNode
  instrument?: InstrumentNode
  children?: TreeNode[]
}

interface InstrumentRow {
  station: StationNode
  instrument: InstrumentNode
}

const router = useRouter()
const { projectId } = useProjectContext()
const {
  featureMappings,
  predictionRows,
  predictionLoading,
  selectedPredictionFeature,
  loadPredictionFeatures,
  loadPredictionForContext,
  clearPrediction
} = usePredictionTrend()
const loading = ref(false)
const objectLoading = ref(false)
const keyword = ref('')
const tree = ref<ProjectObjectTree>({ stations: [] })
const rows = ref<LowFrequencyObservation[]>([])
const waveformRows = ref<AccelerationWaveform[]>([])
const events = ref<MonitoringEvent[]>([])
const rules = ref<EventRule[]>([])
const range = ref<[string, string] | undefined>(latest24HourRange())
const selectedSiteKey = ref('')
const selectedStationId = ref('')
const selectedInstrumentType = ref('')
const selectedInstrumentKey = ref('')
const selectedMetricKey = ref('')
const qualityFilter = ref('')
const navMode = ref<'station' | 'instrument'>('station')
const dataMode = ref<'low' | 'high'>('low')
const dataWindowMode = ref<'realtime' | 'history' | 'empty'>('realtime')
const activeDetailTab = ref<'records' | 'events' | 'source'>('records')
const rateMode = ref('instant')
const valueMode = ref<'ENGINEERING' | 'RAW'>('ENGINEERING')
let observationRequestVersion = 0
const navModeOptions = [
  { label: 'By Point', value: 'station' },
  { label: 'By Device', value: 'instrument' }
]
const valueModeOptions = [
  { label: 'Engineering', value: 'ENGINEERING' },
  { label: 'Raw', value: 'RAW' }
]

const stationNodes = computed(() => tree.value.stations || [])
const selectedStation = computed(() => {
  if (selectedStationId.value) {
    const station = stationNodes.value.find(item => stationKey(item) === selectedStationId.value)
    if (station) return station
  }
  return stationNodes.value.find(station => siteKeyOf(station) === selectedSiteKey.value) || null
})
const selectedInstrumentRow = computed(() => instrumentRows.value.find(row => instrumentKey(row.instrument) === selectedInstrumentKey.value) || null)
const selectedInstrument = computed(() => selectedInstrumentRow.value?.instrument || null)
const selectedMetric = computed(() => selectedInstrument.value ? metricsOf(selectedInstrument.value).find(item => metricKey(item) === selectedMetricKey.value) || null : null)
const selectedRegistry = computed(() => selectedMetric.value ? queryableRegistryOf(selectedMetric.value) : undefined)
const instrumentRows = computed<InstrumentRow[]>(() => stationNodes.value.flatMap(station => instrumentsOf(station).map(instrument => ({ station, instrument }))))
const selectedSiteLabel = computed(() => siteOptions.value.find(item => item.key === selectedSiteKey.value)?.label || '-')
const isAccelerometer = computed(() => {
  const text = `${selectedInstrument.value?.instrumentType || ''} ${selectedInstrument.value?.name || ''} ${selectedInstrument.value?.code || ''}`.toLowerCase()
  return text.includes('acceleration') || text.includes('accelerometer') || text.includes('Acceleration')
})
const activeDataMode = computed(() => isAccelerometer.value ? 'high' : 'low')

const siteOptions = computed(() => {
  const map = new Map<string, { key: string; label: string }>()
  stationNodes.value.forEach(station => {
    const key = siteKeyOf(station)
    if (!map.has(key)) map.set(key, { key, label: siteNameOf(station) })
  })
  return Array.from(map.values()).sort((a, b) => siteSortNo(a.key, a.label) - siteSortNo(b.key, b.label))
})
const instrumentTypeOptions = computed(() => {
  const rows = instrumentRows.value.filter(row => !selectedSiteKey.value || siteKeyOf(row.station) === selectedSiteKey.value)
  const types = new Set(rows.map(row => instrumentTypeKey(row.instrument)))
  return Array.from(types).map(value => ({ value, label: instrumentTypeName(value) }))
})
const instrumentOptions = computed(() => instrumentRows.value
  .filter(row => !selectedSiteKey.value || siteKeyOf(row.station) === selectedSiteKey.value)
  .filter(row => !selectedInstrumentType.value || instrumentTypeKey(row.instrument) === selectedInstrumentType.value)
  .map(row => ({
    key: instrumentKey(row.instrument),
    label: row.instrument.code || row.instrument.name || 'Unnamed Instrument'
  })))
const metricOptions = computed(() => (selectedInstrument.value ? metricsOf(selectedInstrument.value) : []).map(metric => ({
  key: metricKey(metric),
  label: metric.name || metric.code || 'Unnamed Metric'
})))
const objectTreeData = computed(() => navMode.value === 'instrument' ? buildInstrumentTree() : buildStationTree())
const defaultExpandedKeys = computed(() => objectTreeData.value.flatMap(node => {
  const child = node.children?.[0]
  return child ? [node.id, child.id] : [node.id]
}).slice(0, 10))
const currentNodeKey = computed(() => selectedInstrumentKey.value ? `instrument:${selectedInstrumentKey.value}` : selectedSiteKey.value ? `site:${selectedSiteKey.value}` : '')

const filteredRows = computed(() => rows.value.filter(row => {
  if (!qualityFilter.value) return true
  const good = isGoodQuality(row)
  return qualityFilter.value === 'OK' ? good : !good
}))
const chartRows = computed(() => filteredRows.value.slice().sort((a, b) => timeValue(a.observedAt) - timeValue(b.observedAt)))
const unifiedPoints = computed<MetricSeriesPoint[]>(() => [
  ...chartRows.value.map(item => ({
    projectId: item.projectId,
    stationId: item.stationId,
    instrumentId: item.instrumentId,
    metricCode: item.metricCode,
    engineeringMetricCode: item.engineeringMetricCode,
    timestamp: item.observedAt,
    value: toNumber(observationValue(item)) ?? undefined,
    unit: observationUnit(item),
    rawValue: item.rawValue,
    rawUnit: item.rawUnit,
    engineeringValue: item.engineeringValue ?? item.metricValue,
    engineeringUnit: item.engineeringUnit ?? item.metricUnit,
    valueMode: valueMode.value,
    conversionOperatorCode: item.conversionOperatorCode,
    conversionVersion: item.conversionVersion,
    conversionStatus: item.conversionStatus,
    conversionRemark: item.conversionRemark,
    qualityFlag: item.qualityFlag,
    sourceType: 'OBSERVATION'
  })),
  ...predictionRows.value.map(item => ({
    projectId: item.projectId,
    stationId: item.stationId,
    instrumentId: item.instrumentId,
    metricCode: item.metricCode,
    engineeringMetricCode: item.engineeringMetricCode,
    timestamp: item.futureTime,
    value: toNumber(predictionValue(item)) ?? undefined,
    unit: predictionUnit(item),
    rawValue: item.rawPredictedValue,
    rawUnit: item.rawPredictedUnit,
    engineeringValue: item.engineeringValue,
    engineeringUnit: item.engineeringUnit,
    valueMode: valueMode.value,
    conversionOperatorCode: item.conversionOperatorCode,
    conversionVersion: item.conversionVersion,
    conversionStatus: item.conversionStatus,
    conversionRemark: item.conversionRemark,
    qualityFlag: item.qualityFlag,
    sourceType: 'PREDICTION',
    sourceBatchId: item.batchId,
    sourceBatchCode: item.batchCode,
    sourceRunId: item.runId,
    sourceModelCode: item.modelCode,
    sourceModelVersion: item.modelVersion,
    featureCode: item.featureCode,
    step: item.step,
    horizonMinutes: item.horizonMinutes,
    originTime: item.baseTime,
    lowerBound: valueMode.value === 'RAW' ? item.rawLowerBound : item.lowerBound,
    upperBound: valueMode.value === 'RAW' ? item.rawUpperBound : item.upperBound,
    confidence: item.confidence
  }))
])
const xData = computed(() => chartRows.value.map(item => String(item.observedAt || '')))
const values = computed(() => chartRows.value.map(item => toNumber(observationValue(item))).filter(value => value !== null) as number[])
const unit = computed(() => observationUnit(filteredRows.value[0]) || selectedMetric.value?.metricUnit || '')
const metricDisplayName = computed(() => selectedMetric.value ? metricName(selectedMetric.value.code || selectedMetric.value.name) : 'Metric')
const rateSeries = computed(() => [{ name: rateMode.value === 'instant' ? 'Instant Change Rate' : 'Cumulative Change Rate', data: changeRate(values.value) }])
const rateUnit = computed(() => unit.value ? `${unit.value}/h` : '')
const waveformUnit = computed(() => waveformRows.value[0]?.accelUnit || 'm/s2')
const waveformXData = computed(() => waveformRows.value.map(item => String(item.sampleOffsetMs ?? item.sampleIndex ?? '')))
const waveformSeries = computed(() => [
  { name: 'X', data: waveformRows.value.map(item => toNumber(item.xAccel) ?? 0) },
  { name: 'Y', data: waveformRows.value.map(item => toNumber(item.yAccel) ?? 0) },
  { name: 'Z', data: waveformRows.value.map(item => toNumber(item.zAccel) ?? 0) }
])
const waveformFeature = computed(() => {
  const samples = waveformRows.value.flatMap(item => [
    { axis: 'X', value: Math.abs(Number(item.xAccel ?? 0)) },
    { axis: 'Y', value: Math.abs(Number(item.yAccel ?? 0)) },
    { axis: 'Z', value: Math.abs(Number(item.zAccel ?? 0)) }
  ])
  const peak = samples.reduce((best, item) => item.value > best.value ? item : best, { axis: '-', value: 0 })
  const rms = samples.length ? Math.sqrt(samples.reduce((sum, item) => sum + item.value * item.value, 0) / samples.length) : 0
  return { pga: peak.value.toFixed(4), rms: rms.toFixed(4), axis: peak.axis }
})
const effectiveMetricCode = computed(() => chartRows.value[chartRows.value.length - 1]?.engineeringMetricCode || selectedMetric.value?.code || '')
const applicableRules = computed(() => rules.value.filter(rule => Number(rule.enabled ?? 1) === 1 && sameMetricCode(rule.metricCode, effectiveMetricCode.value)))
const warningThreshold = computed(() => valueMode.value === 'ENGINEERING' ? thresholdFromRules(applicableRules.value, false) : undefined)
const alarmThreshold = computed(() => valueMode.value === 'ENGINEERING' ? thresholdFromRules(applicableRules.value, true) : undefined)
const forecastValues = computed(() => predictionRows.value.map(item => Number(predictionValue(item))).filter(Number.isFinite))
const forecastPeak = computed(() => forecastValues.value.length ? Math.max(...forecastValues.value) : undefined)
const forecastPeakText = computed(() => valueText(forecastPeak.value, predictionUnit(predictionRows.value[0]) || unit.value))
const firstExceedance = computed(() => {
  const threshold = warningThreshold.value
  if (threshold === undefined) return undefined
  return predictionRows.value.find(item => Number(predictionValue(item)) >= threshold)
})
const firstExceedanceText = computed(() => firstExceedance.value?.futureTime ? String(firstExceedance.value.futureTime).replace('T', ' ').slice(0, 19) : 'Not Predicted')
const leadTimeText = computed(() => firstExceedance.value?.horizonMinutes !== undefined ? `${firstExceedance.value.horizonMinutes} min` : '-')
const predictionBatch = computed<PredictionBatch | null>(() => {
  const first = predictionRows.value[0]
  const last = predictionRows.value[predictionRows.value.length - 1]
  return first ? { id: first.batchId, batchCode: first.batchCode, baseTime: first.baseTime, rollingSteps: predictionRows.value.length, horizonMinutes: last?.horizonMinutes, status: 'success' } : null
})
const predictionModelText = computed(() => {
  const item = predictionRows.value[0]
  return item ? `${item.modelCode || '-'} ${item.modelVersion || ''}`.trim() : '-'
})
const relatedEvents = computed(() => events.value.filter(event => {
  const stationMatch = !selectedStation.value || Number(event.stationId) === Number(selectedStation.value.id)
  const instrumentMatch = !selectedInstrument.value || Number(event.instrumentId) === Number(selectedInstrument.value.id)
  const metricMatch = !selectedMetric.value || !event.metricCode || event.metricCode === selectedMetric.value.code
  return stationMatch && instrumentMatch && metricMatch
}).slice(0, 6))
const latestValueText = computed(() => valueText(values.value.length ? values.value[values.value.length - 1] : undefined, unit.value))
const minValueText = computed(() => valueText(values.value.length ? Math.min(...values.value) : undefined, unit.value))
const maxValueText = computed(() => valueText(values.value.length ? Math.max(...values.value) : undefined, unit.value))
const avgValueText = computed(() => valueText(values.value.length ? values.value.reduce((sum, value) => sum + value, 0) / values.value.length : undefined, unit.value))
const stdValueText = computed(() => valueText(std(values.value), unit.value))
const latestObservationTime = computed(() => chartRows.value[chartRows.value.length - 1]?.observedAt || waveformRows.value[waveformRows.value.length - 1]?.sampleTime || '-')
const thresholdText = computed(() => warningThreshold.value === undefined ? 'Not Configured' : valueText(warningThreshold.value, unit.value))
const alarmText = computed(() => alarmThreshold.value === undefined ? 'Not Configured' : valueText(alarmThreshold.value, unit.value))
const qualitySummary = computed(() => {
  const bad = filteredRows.value.filter(row => !isGoodQuality(row)).length
  return bad ? `${bad} reviews` : 'Good'
})
const qualityType = computed(() => qualitySummary.value === 'Good' ? 'success' : 'warning')
const dataWindowLabel = computed(() => {
  if (dataWindowMode.value === 'realtime') return 'Real-Time Data'
  if (dataWindowMode.value === 'history') return 'Historical Data'
  return 'No Data'
})
const predictionWindowText = computed(() => selectedPredictionFeature.value ? `${predictionRows.value.length} steps` : 'Not Available')
const predictionFeatureText = computed(() => {
  const feature = selectedPredictionFeature.value
  if (!feature) return ''
  return `${feature.featureLabel || feature.featureCode} · ${predictionRows.value.length} forecast steps`
})
const conversionStatusText = computed(() => {
  if (valueMode.value === 'RAW') return 'Not Applied'
  const row = chartRows.value[chartRows.value.length - 1]
  return row?.conversionStatus === 'success' ? 'Converted' : row?.conversionRemark || 'Unavailable'
})
const conversionVersionText = computed(() => valueMode.value === 'RAW' ? '-' : chartRows.value[chartRows.value.length - 1]?.conversionVersion || '-')

function observationValue(item?: LowFrequencyObservation) {
  if (!item) return undefined
  return valueMode.value === 'RAW' ? item.rawValue : item.engineeringValue ?? item.metricValue
}

function observationUnit(item?: LowFrequencyObservation) {
  if (!item) return ''
  return String(valueMode.value === 'RAW' ? item.rawUnit || '' : item.engineeringUnit || item.metricUnit || '')
}

function predictionValue(item?: import('../../types/engineering').PredictionDisplay) {
  if (!item) return undefined
  return valueMode.value === 'RAW' ? item.rawPredictedValue : item.engineeringValue ?? item.predictedValue
}

function predictionUnit(item?: import('../../types/engineering').PredictionDisplay) {
  if (!item) return ''
  return String(valueMode.value === 'RAW' ? item.rawPredictedUnit || '' : item.engineeringUnit || item.predictedUnit || '')
}

function filteredInstrumentRows() {
  const text = keyword.value.trim().toLowerCase()
  return instrumentRows.value.filter(row => {
    const haystack = [
      row.station.name,
      row.station.code,
      row.station.siteName,
      row.instrument.name,
      row.instrument.code,
      row.instrument.instrumentType,
      ...metricsOf(row.instrument).map(metric => `${metric.name} ${metric.code}`)
    ].join(' ').toLowerCase()
    return !text || haystack.includes(text)
  })
}

function buildStationTree(): TreeNode[] {
  const siteMap = new Map<string, { label: string; station: StationNode; rows: InstrumentRow[] }>()
  filteredInstrumentRows().forEach(row => {
    const key = siteKeyOf(row.station)
    const item = siteMap.get(key) || { label: siteNameOf(row.station), station: row.station, rows: [] }
    item.rows.push(row)
    siteMap.set(key, item)
  })
  return Array.from(siteMap.entries()).sort((a, b) => siteSortNo(a[0], a[1].label) - siteSortNo(b[0], b[1].label)).map(([siteKey, site]) => {
    const typeMap = groupRows(site.rows, row => instrumentTypeKey(row.instrument))
    return {
      id: `site:${siteKey}`,
      label: site.label,
      kind: 'site',
      station: site.station,
      count: site.rows.length,
      children: Array.from(typeMap.entries()).sort((a, b) => instrumentTypeName(a[0]).localeCompare(instrumentTypeName(b[0]), 'zh-Hans-CN', { numeric: true })).map(([type, rows]) => ({
        id: `site:${siteKey}:type:${type}`,
        label: instrumentTypeName(type),
        kind: 'type',
        station: rows[0]?.station,
        count: rows.length,
        children: rows.map(row => ({
          id: `instrument:${instrumentKey(row.instrument)}`,
          label: row.instrument.code || row.instrument.name || 'Unnamed Instrument',
          kind: 'instrument',
          station: row.station,
          instrument: row.instrument
        }))
      }))
    }
  })
}

function buildInstrumentTree(): TreeNode[] {
  const typeMap = groupRows(filteredInstrumentRows(), row => instrumentTypeKey(row.instrument))
  return Array.from(typeMap.entries()).sort((a, b) => instrumentTypeName(a[0]).localeCompare(instrumentTypeName(b[0]), 'zh-Hans-CN', { numeric: true })).map(([type, rows]) => {
    const siteMap = new Map<string, { label: string; station: StationNode; rows: InstrumentRow[] }>()
    rows.forEach(row => {
      const key = siteKeyOf(row.station)
      const item = siteMap.get(key) || { label: siteNameOf(row.station), station: row.station, rows: [] }
      item.rows.push(row)
      siteMap.set(key, item)
    })
    return {
      id: `type:${type}`,
      label: instrumentTypeName(type),
      kind: 'type',
      count: rows.length,
      children: Array.from(siteMap.entries()).sort((a, b) => siteSortNo(a[0], a[1].label) - siteSortNo(b[0], b[1].label)).map(([siteKey, site]) => ({
        id: `type:${type}:site:${siteKey}`,
        label: site.label,
        kind: 'site',
        station: site.station,
        count: site.rows.length,
        children: site.rows.map(row => ({
          id: `instrument:${instrumentKey(row.instrument)}`,
          label: row.instrument.code || row.instrument.name || 'Unnamed Instrument',
          kind: 'instrument',
          station: row.station,
          instrument: row.instrument
        }))
      }))
    }
  })
}

function onTreeNodeClick(data: TreeNode) {
  if (data.station) {
    selectedSiteKey.value = siteKeyOf(data.station)
    selectedStationId.value = stationKey(data.station)
  }
  if (data.instrument) {
    selectedInstrumentType.value = instrumentTypeKey(data.instrument)
    selectedInstrumentKey.value = instrumentKey(data.instrument)
    const metric = defaultMetricOf(data.instrument, data.station)
    selectedMetricKey.value = metric ? metricKey(metric) : ''
    loadObservations()
  }
}

function onSiteChange() {
  const firstStation = stationNodes.value.find(station => siteKeyOf(station) === selectedSiteKey.value)
  selectedStationId.value = firstStation ? stationKey(firstStation) : ''
  const firstType = instrumentTypeOptions.value[0]
  selectedInstrumentType.value = firstType?.value || ''
  onInstrumentTypeChange()
}

function onInstrumentTypeChange() {
  selectedInstrumentKey.value = instrumentOptions.value[0]?.key || ''
  onInstrumentChange()
}

function onInstrumentChange() {
  if (selectedInstrumentRow.value) {
    selectedStationId.value = stationKey(selectedInstrumentRow.value.station)
    selectedSiteKey.value = siteKeyOf(selectedInstrumentRow.value.station)
  }
  const metric = selectedInstrument.value ? defaultMetricOf(selectedInstrument.value, selectedInstrumentRow.value?.station) : null
  selectedMetricKey.value = metric ? metricKey(metric) : ''
  loadObservations()
}

function onMetricChange() {
  loadObservations()
}

function setDataMode(mode: 'low' | 'high') {
  dataMode.value = mode
  loadObservations()
}

function syncRange() {
  loadObservations()
}

function resetFilters() {
  qualityFilter.value = ''
  range.value = latest24HourRange()
  if (selectPredictionReadyContext()) {
    loadObservations()
    return
  }
  selectedSiteKey.value = siteOptions.value[0]?.key || ''
  const firstStation = stationNodes.value.find(station => siteKeyOf(station) === selectedSiteKey.value)
  selectedStationId.value = firstStation ? stationKey(firstStation) : ''
  onSiteChange()
}

function selectPredictionReadyContext() {
  for (const feature of featureMappings.value) {
    if (!feature.stationId || !feature.instrumentId || !feature.sourceMetricCode) continue
    const station = stationNodes.value.find(item => Number(item.id) === Number(feature.stationId))
    const instrument = station && instrumentsOf(station).find(item => Number(item.id) === Number(feature.instrumentId))
    const metric = instrument && metricsOf(instrument).find(item => sameMetricCode(item.code, feature.sourceMetricCode))
    if (!station || !instrument || !metric) continue
    selectedSiteKey.value = siteKeyOf(station)
    selectedStationId.value = stationKey(station)
    selectedInstrumentType.value = instrumentTypeKey(instrument)
    selectedInstrumentKey.value = instrumentKey(instrument)
    selectedMetricKey.value = metricKey(metric)
    return true
  }
  return false
}

async function loadObjects() {
  if (!projectId.value) return
  objectLoading.value = true
  try {
    const [objectTree, eventRows, ruleRows] = await Promise.all([
      getProjectObjectTree(projectId.value),
      listEvents({ projectId: projectId.value, limit: 200 }),
      listEventRules({ projectId: projectId.value, limit: 200 }),
      loadPredictionFeatures(projectId.value)
    ])
    tree.value = objectTree
    events.value = eventRows
    rules.value = ruleRows
    if (!selectedSiteKey.value) resetFilters()
  } finally {
    objectLoading.value = false
  }
}

async function loadObservations() {
  const currentRequest = ++observationRequestVersion
  if (!projectId.value || !selectedStation.value || !selectedInstrument.value || !selectedMetric.value) {
    clearPrediction()
    return
  }
  clearPrediction()
  if (activeDataMode.value === 'high') {
    await loadWaveformRows(currentRequest)
    return
  }
  const registry = queryableRegistryOf(selectedMetric.value)
  const queryRange = latest24HourRange()
  range.value = queryRange
  rows.value = []
  waveformRows.value = []
  loading.value = true
  try {
    const realtimeRows = await queryLowFrequencyRows(registry?.code, queryRange, 500)
    if (currentRequest !== observationRequestVersion) return
    if (realtimeRows.length) {
      rows.value = realtimeRows
      dataWindowMode.value = 'realtime'
      await loadPredictionTrend()
      return
    }

    const latestRows = await queryLowFrequencyRows(registry?.code, undefined, 1)
    if (currentRequest !== observationRequestVersion) return
    const latestTime = latestRows[0]?.observedAt ? new Date(String(latestRows[0].observedAt)) : null
    if (latestTime && !Number.isNaN(latestTime.getTime())) {
      const historyRange = rangeBefore(latestTime, 24)
      range.value = historyRange
      const historyRows = await queryLowFrequencyRows(registry?.code, historyRange, 500)
      if (currentRequest !== observationRequestVersion) return
      rows.value = historyRows
      dataWindowMode.value = rows.value.length ? 'history' : 'empty'
      await loadPredictionTrend()
      return
    }

    rows.value = []
    dataWindowMode.value = 'empty'
    clearPrediction()
  } finally {
    if (currentRequest === observationRequestVersion) loading.value = false
  }
}

async function loadPredictionTrend() {
  if (!projectId.value || !selectedStation.value || !selectedInstrument.value || !selectedMetric.value) {
    clearPrediction()
    return
  }
  await loadPredictionForContext({
    projectId: projectId.value,
    stationId: Number(selectedStation.value.id),
    instrumentId: Number(selectedInstrument.value.id),
    metricCode: selectedMetric.value.code
  })
}

function queryLowFrequencyRows(registryCode?: string, queryRange?: [string, string], limit = 500) {
  if (!projectId.value || !selectedStation.value || !selectedInstrument.value || !selectedMetric.value) return Promise.resolve([])
  return listLowFrequencyObservations({
    registryCode,
    projectId: projectId.value,
    stationId: selectedStation.value.id,
    instrumentId: selectedInstrument.value.id,
    instrumentType: selectedInstrument.value.instrumentType,
    metricCode: selectedMetric.value.code,
    startTime: queryRange?.[0],
    endTime: queryRange?.[1],
    limit
  })
}

async function loadWaveformRows(requestVersion = observationRequestVersion) {
  if (!projectId.value || !selectedStation.value || !selectedInstrument.value) return
  loading.value = true
  waveformRows.value = []
  rows.value = []
  try {
    const nextRows = await listAccelerationWaveforms({
      projectId: projectId.value,
      stationId: selectedStation.value.id,
      instrumentId: selectedInstrument.value.id,
      metricCode: selectedMetric.value?.code || 'acceleration',
      startTime: range.value?.[0],
      endTime: range.value?.[1],
      limit: 1000
    })
    if (requestVersion !== observationRequestVersion) return
    waveformRows.value = nextRows
  } finally {
    if (requestVersion === observationRequestVersion) loading.value = false
  }
}

function exportRows() {
  const lines = ['observedAt,station,instrument,metric,value,unit,quality']
  filteredRows.value.forEach(row => lines.push([
    row.observedAt || '',
    selectedSiteLabel.value,
    selectedInstrument.value?.code || '',
    row.metricCode || '',
    observationValue(row) ?? '',
    observationUnit(row),
    row.qualityFlag || ''
  ].join(',')))
  const blob = new Blob([lines.join('\n')], { type: 'text/csv;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = 'low-frequency-observations.csv'
  link.click()
  URL.revokeObjectURL(url)
}

function latest24HourRange(): [string, string] {
  const end = new Date()
  return rangeBefore(end, 24)
}

function rangeBefore(end: Date, hours: number): [string, string] {
  const start = new Date(end.getTime() - hours * 60 * 60 * 1000)
  return [formatDateTime(start), formatDateTime(end)]
}

function formatDateTime(date: Date) {
  const pad = (value: number) => String(value).padStart(2, '0')
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())} ${pad(date.getHours())}:${pad(date.getMinutes())}:${pad(date.getSeconds())}`
}

function timeValue(value?: unknown) {
  const time = value ? new Date(String(value)).getTime() : 0
  return Number.isFinite(time) ? time : 0
}

function instrumentsOf(station: StationNode) {
  return Array.isArray(station.instruments) ? station.instruments : []
}

function metricsOf(instrument: InstrumentNode) {
  return Array.isArray(instrument.metrics) ? instrument.metrics : []
}

function defaultMetricOf(instrument: InstrumentNode, station?: StationNode) {
  const metrics = metricsOf(instrument)
  if (!metrics.length) return null
  const predictionMetric = predictionMetricOf(instrument, station)
  if (predictionMetric) return predictionMetric
  const type = instrumentTypeKey(instrument)
  const preferred: Record<string, string[]> = {
    displacement: ['deep_horizontal_displacement', 'horizontal_displacement', 'displacement_tilt_y_deg', 'displacement_tilt_x_deg'],
    pressure_water_level: ['special_differential_water_level', 'groundwater_level', 'pressure_water_level'],
    static_level: ['ground_settlement', 'static_level_value', 'static_level_aux'],
    earth_pressure: ['earth_pressure_kpa', 'earth_pressure_value', 'earth_pressure_frequency'],
    accelerometer: ['acceleration_waveform', 'acceleration_pga_max', 'acceleration_peak_vector']
  }
  const codes = preferred[type] || []
  for (const code of codes) {
    const match = metrics.find(metric => String(metric.code || '').includes(code))
    if (match) return match
  }
  const businessMetric = metrics.find(metric => {
    const code = String(metric.code || '').toLowerCase()
    return !code.includes('voltage') && !code.includes('temperature') && !code.includes('raw')
  })
  return businessMetric || metrics[0]
}

function predictionMetricOf(instrument: InstrumentNode, station?: StationNode) {
  const metrics = metricsOf(instrument)
  const instrumentId = Number(instrument.id)
  const stationId = Number(station?.id)
  const candidates = featureMappings.value
    .filter(feature => Number(feature.enabled ?? 1) === 1)
    .filter(feature => Number(feature.predictionTarget ?? 0) === 1)
    .filter(feature => String(feature.featureRole || 'model_input').toLowerCase() === 'model_input')
    .filter(feature => Boolean(feature.targetType && feature.sourceMetricCode))
    .filter(feature => Number(feature.instrumentId) === instrumentId)
    .filter(feature => !Number.isFinite(stationId) || Number(feature.stationId) === stationId)
    .slice()
    .sort((left, right) => Number(left.featureOrder || 0) - Number(right.featureOrder || 0))
  for (const feature of candidates) {
    const metric = metrics.find(item => sameMetricCode(item.code, feature.sourceMetricCode))
    if (metric) return metric
  }
  return null
}

function registriesOf(metric: MetricNode) {
  return Array.isArray(metric.registries) ? metric.registries : []
}

function queryableRegistryOf(metric: MetricNode): RegistryNode | undefined {
  return registriesOf(metric).find(registry => Number(registry.enabled ?? 1) === 1 && Number(registry.queryable ?? 1) === 1)
}

function siteKeyOf(station: StationNode) {
  const siteNo = station.siteNo || siteNoOfText(`${station.code || ''} ${station.name || ''} ${station.stationType || ''}`)
  return siteNo ? `point-${siteNo}` : String(station.id || station.code)
}

function stationKey(station: StationNode) {
  return String(station.id || station.code || siteKeyOf(station))
}

function siteNameOf(station: StationNode) {
  if (station.siteName) return String(station.siteName)
  const siteNo = siteNoOfText(`${station.code || ''} ${station.name || ''}`)
  return siteNo ? `Point No. ${siteNo}` : station.name || station.code || 'Unnamed Point'
}

function siteSortNo(siteKey: string, label = '') {
  const no = siteNoOfText(`${siteKey} ${label}`)
  return no ? Number(no) : Number.MAX_SAFE_INTEGER
}

function siteNoOfText(text: string) {
  return text.match(/(?:ST[-_ ]?|station|Point|point|point-)?([1-9])(?:No.|#|points|[^0-9]|$)/i)?.[1]
}

function instrumentKey(instrument: InstrumentNode) {
  return String(instrument.id || instrument.code)
}

function instrumentTypeKey(instrument: InstrumentNode) {
  return String(instrument.instrumentType || 'other')
}

function metricKey(metric: MetricNode) {
  return String(metric.id || metric.code)
}

function sameMetricCode(left?: unknown, right?: unknown) {
  const normalize = (value?: unknown) => String(value || '').toLowerCase().replace(/[^a-z0-9]+/g, '')
  const a = normalize(left)
  const b = normalize(right)
  return Boolean(a && b && a === b)
}

function groupRows<T>(items: T[], getKey: (item: T) => string) {
  const map = new Map<string, T[]>()
  items.forEach(item => {
    const key = getKey(item)
    if (!map.has(key)) map.set(key, [])
    map.get(key)?.push(item)
  })
  return map
}

function instrumentTypeName(type?: unknown) {
  const map: Record<string, string> = { displacement: 'Inclinometer', earth_pressure: 'Earth Pressure Cell', static_level: 'Static Level Gauge', pressure_water_level: 'Water Level Gauge', accelerometer: 'Accelerometer' }
  const key = String(type || '')
  return map[key] || key || 'Unknown Instrument'
}

function metricName(metric?: unknown) {
  const key = String(metric || '')
  const map: Record<string, string> = { settlement: 'Cumulative Settlement', displacement: 'Horizontal Displacement', strain: 'Strain', earth_pressure: 'Earth Pressure', voltage1: 'Voltage 1', voltage2: 'Voltage 2' }
  return map[key] || key || 'Metric'
}

function thresholdFromRules(items: EventRule[], alarm: boolean) {
  const rows = items.filter(item => item.thresholdValue !== undefined && item.thresholdValue !== null)
  if (!rows.length) return undefined
  const preferred = rows.filter(item => alarm ? String(item.eventLevel || '').toLowerCase() === 'red' : String(item.eventLevel || '').toLowerCase() !== 'red')
  const source = preferred.length ? preferred : (alarm ? [] : rows)
  if (!source.length) return undefined
  const values = source.map(item => Number(item.thresholdValue)).filter(Number.isFinite)
  return values.length ? (alarm ? Math.max(...values) : Math.min(...values)) : undefined
}

function valueText(value?: number | null, metricUnit?: string) {
  if (value === undefined || value === null || Number.isNaN(Number(value))) return '-'
  const number = Number(value)
  const digits = Math.abs(number) < 1 ? 3 : Math.abs(number) < 10 ? 2 : 1
  return `${number.toFixed(digits)}${metricUnit ? ` ${metricUnit}` : ''}`
}

function toNumber(value: unknown) {
  const number = Number(value)
  return Number.isFinite(number) ? number : null
}

function changeRate(items: number[]) {
  return items.map((value, index) => index === 0 ? 0 : Number((value - items[index - 1]).toFixed(3)))
}

function std(items: number[]) {
  if (!items.length) return undefined
  const mean = items.reduce((sum, value) => sum + value, 0) / items.length
  return Math.sqrt(items.reduce((sum, value) => sum + Math.pow(value - mean, 2), 0) / items.length)
}

function isGoodQuality(row: LowFrequencyObservation) {
  const flag = String(row.qualityFlag || 'OK').toUpperCase()
  return ['OK', 'GOOD', 'VALID', 'NORMAL'].includes(flag)
}

function levelName(level?: unknown) {
  const key = String(level || '').toLowerCase()
  if (key.includes('red') || key.includes('danger') || key.includes('Level 1')) return 'High Risk'
  if (key.includes('orange') || key.includes('warning') || key.includes('Level 2')) return 'Medium Risk'
  if (key.includes('yellow') || key.includes('notice') || key.includes('Level 3')) return 'Low Risk'
  return 'Event'
}

function eventTagType(level?: unknown) {
  const name = levelName(level)
  if (name === 'High Risk') return 'danger'
  if (name === 'Medium Risk') return 'warning'
  return 'success'
}

watch(projectId, loadObjects, { immediate: true })
</script>

<style scoped>
.observation-workbench {
  display: flex;
  flex-direction: column;
  gap: 14px;
  min-width: 1320px;
}
.observation-header { height: 38px; display: flex; align-items: center; justify-content: space-between; gap: 16px; }
.observation-header h1 { margin: 0; color: var(--softx-text); font-size: 22px; letter-spacing: 0; }
:global(.main-panel:has(.observation-workbench)) { overflow-x: auto; }
.filter-bar {
  display: grid;
  grid-template-columns: 126px 142px 160px 176px 290px 122px auto auto auto;
  gap: 12px;
  align-items: end;
  padding: 14px;
  border: 1px solid var(--softx-border);
  border-radius: 8px;
  background: #fff;
}
.filter-bar label span {
  display: block;
  margin-bottom: 5px;
  color: var(--softx-muted);
  font-size: 16px;
  font-weight: 650;
}
.filter-bar :deep(.el-select),
.filter-bar :deep(.el-date-editor) { width: 100%; }
.data-summary-strip {
  display: grid;
  grid-template-columns: repeat(6, minmax(0, 1fr));
  gap: 12px;
}
.data-summary-strip article {
  min-width: 0;
  min-height: 74px;
  padding: 12px 14px;
  border: 1px solid var(--softx-border);
  border-radius: 8px;
  background: #fff;
  box-shadow: 0 8px 22px rgba(15,23,42,.035);
}
.data-summary-strip span {
  display: block;
  overflow: hidden;
  color: var(--softx-muted);
  font-size: 14px;
  font-weight: 650;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.data-summary-strip strong {
  display: block;
  margin-top: 8px;
  overflow: hidden;
  color: var(--softx-text);
  font-size: 19px;
  font-weight: 820;
  line-height: 1.1;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.main-grid {
  display: grid;
  grid-template-columns: 320px minmax(0, 1fr) 300px;
  grid-template-areas:
    "tree trend metric"
    "bottom bottom bottom";
  gap: 14px;
}
.detail-tabs-card {
  grid-area: bottom;
  min-width: 0;
  height: 420px;
  overflow: hidden;
}
.panel-card {
  min-width: 0;
  padding: 14px;
  border: 1px solid var(--softx-border);
  border-radius: 8px;
  background: #fff;
  box-shadow: 0 8px 22px rgba(15,23,42,.035);
}
.object-tree-card { grid-area: tree; height: 700px; display: flex; flex-direction: column; overflow: hidden; }
.trend-card { grid-area: trend; height: 700px; display: flex; flex-direction: column; overflow: hidden; }
.metric-card { grid-area: metric; height: 700px; overflow: auto; }
.panel-head {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  align-items: flex-start;
  margin-bottom: 12px;
}
.panel-head.compact { display: block; }
.panel-head strong { display: block; color: var(--softx-text); font-size: 16px; font-weight: 800; }
.panel-head span { display: block; margin-top: 4px; color: var(--softx-muted); font-size: 16px; line-height: 1.45; }
.object-tree-card .panel-head strong { font-size: 16px; }
.object-tree-card .panel-head span { margin-top: 5px; font-size: 16px; }
.object-tree {
  flex: 1;
  min-height: 0;
  margin-top: 12px;
  overflow-y: scroll;
  scrollbar-gutter: stable;
  padding-right: 4px;
}
.object-tree :deep(.el-tree-node__content) { min-height: 42px; border-radius: 10px; }
.object-tree :deep(.el-tree-node__content:hover) { background: #f4f7fb; }
.object-tree :deep(.is-current > .el-tree-node__content) { background: #eef5ff; color: #0f4ec7; }
.tree-node {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  align-items: center;
  gap: 8px;
  width: 100%;
  padding-right: 8px;
}
.tree-node-main { min-width: 0; }
.node-label {
  display: block;
  overflow: hidden;
  color: var(--softx-text);
  font-size: 16px;
  font-weight: 700;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.tree-node.leaf .node-label { font-weight: 650; }
.tree-node-main small {
  display: block;
  margin-top: 3px;
  overflow: hidden;
  color: var(--softx-muted);
  font-size: 16px;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.node-count {
  min-width: 24px;
  height: 22px;
  padding: 0 8px;
  border-radius: 999px;
  background: #eef5ff;
  color: #2463d8;
  font-size: 16px;
  line-height: 22px;
  text-align: center;
}
.trend-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  min-height: 34px;
  margin-bottom: 10px;
}
.data-tabs {
  display: flex;
  align-items: center;
  gap: 22px;
}
.data-tabs button {
  border: 0;
  background: transparent;
  color: var(--softx-muted);
  font-size: 16px;
  font-weight: 750;
  cursor: pointer;
}
.data-tabs button:disabled {
  cursor: default;
  opacity: .55;
}
.data-tabs button.active {
  color: #1d5cff;
  opacity: 1;
}
.data-tabs button.active::after {
  display: block;
  width: 100%;
  height: 2px;
  margin-top: 7px;
  border-radius: 999px;
  background: #1d5cff;
  content: "";
}
.chart-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  color: var(--softx-muted);
  font-size: 16px;
}
.trend-batch { width: 290px; }
.fullscreen-btn {
  width: 28px;
  min-width: 28px;
  padding: 0;
}
.chart-section {
  min-height: 0;
}
.primary-chart {
  flex: 1 1 0;
  min-height: 0;
}
.chart-title {
  display: flex;
  align-items: center;
  gap: 16px;
  min-height: 30px;
  color: var(--softx-muted);
  font-size: 16px;
}
.chart-title strong {
  color: var(--softx-text);
  font-size: 16px;
  font-weight: 760;
}
.primary-chart :deep(.unified-series-chart) { height: calc(100% - 30px); min-height: 210px; }
.rate-chart {
  display: flex;
  flex-direction: column;
  flex: 0 0 250px;
  margin-top: 0;
  padding-top: 3px;
  border-top: 1px solid #edf1f7;
}
.rate-chart :deep(.chart) {
  flex: 1;
  min-height: 0;
  height: auto;
}
.waveform-chart {
  flex: 1 1 0;
  min-height: 0;
}
.waveform-chart :deep(.chart) { height: calc(100% - 30px); min-height: 460px; }
.waveform-stats {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 10px;
  margin-top: 10px;
}
.waveform-stats article {
  padding: 10px 12px;
  border: 1px solid #edf1f7;
  border-radius: 8px;
  background: #fbfdff;
}
.waveform-stats span {
  display: block;
  color: var(--softx-muted);
  font-size: 16px;
}
.waveform-stats strong {
  display: block;
  margin-top: 4px;
  color: var(--softx-text);
  font-size: 21px;
}
.sub-chart-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0;
}
.sub-chart-head strong { font-size: 16px; }
.sub-chart-head div {
  display: flex;
  align-items: center;
  gap: 8px;
  color: var(--softx-muted);
  font-size: 16px;
}
.metric-card {
  display: flex;
  flex-direction: column;
  gap: 0;
}
.metric-section {
  padding: 14px 0;
  border-top: 1px solid #edf1f7;
}
.metric-card .panel-head + .metric-section {
  border-top: 0;
  padding-top: 4px;
}
.metric-section div {
  display: grid;
  grid-template-columns: 92px minmax(0, 1fr);
  align-items: center;
  gap: 12px;
  min-height: 30px;
}
.metric-section span,
.recent-stat span {
  color: var(--softx-muted);
  font-size: 16px;
}
.metric-section strong,
.recent-stat b {
  min-width: 0;
  overflow: hidden;
  color: var(--softx-text);
  font-size: 16px;
  font-weight: 750;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.risk-up { color: #ef4444 !important; }
.threshold-list div {
  grid-template-columns: 14px 78px minmax(0, 1fr);
}
.threshold-list i {
  width: 9px;
  height: 9px;
  border-radius: 50%;
}
.threshold-list .warning { background: #f59e0b; }
.threshold-list .alarm { background: #ef4444; }
.metric-meta strong {
  font-size: 16px;
}
.recent-stat {
  display: grid;
  gap: 8px;
  padding: 12px;
  border-radius: 8px;
  background: #f8fafc;
}
.recent-stat > strong {
  margin-bottom: 2px;
  color: var(--softx-text);
  font-size: 16px;
  font-weight: 800;
}
.recent-stat div {
  display: grid;
  grid-template-columns: 92px minmax(0, 1fr);
  align-items: center;
  gap: 12px;
}
.recent-stat b {
  justify-self: end;
  font-size: 16px;
}
.detail-tabs,
.detail-tabs :deep(.el-tabs__content),
.detail-tabs :deep(.el-tab-pane) {
  height: 100%;
}
.detail-tabs :deep(.el-tabs__content) {
  overflow: hidden;
}
.detail-tabs :deep(.el-tabs__header) {
  margin-bottom: 10px;
}
.detail-tabs-card :deep(.el-table) { font-size: 16px; }
.event-pane-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  min-height: 32px;
  margin-bottom: 10px;
}
.event-pane-head strong {
  color: var(--softx-text);
  font-size: 16px;
  font-weight: 800;
}
.event-list {
  display: grid;
  gap: 8px;
  max-height: 330px;
  overflow-y: auto;
  padding-right: 3px;
}
.event-list article {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr) auto;
  gap: 10px;
  align-items: center;
  padding: 10px;
  border: 1px solid #edf1f7;
  border-radius: 8px;
  background: #fbfdff;
}
.event-list strong,
.event-list small {
  display: block;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.event-list small,
.event-list article > span {
  color: var(--softx-muted);
  font-size: 16px;
}
.source-rule-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
}
.source-rule-grid article {
  min-width: 0;
  min-height: 82px;
  padding: 12px;
  border: 1px solid #edf1f7;
  border-radius: 8px;
  background: #fbfdff;
}
.source-rule-grid span,
.source-rule-grid strong {
  display: block;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.source-rule-grid span {
  color: var(--softx-muted);
  font-size: 14px;
  font-weight: 650;
}
.source-rule-grid strong {
  margin-top: 10px;
  color: var(--softx-text);
  font-size: 16px;
  font-weight: 780;
}
.object-tree::-webkit-scrollbar,
.event-list::-webkit-scrollbar {
  width: 8px;
}
.object-tree::-webkit-scrollbar-track,
.event-list::-webkit-scrollbar-track {
  background: transparent;
}
.object-tree::-webkit-scrollbar-thumb,
.event-list::-webkit-scrollbar-thumb {
  border-radius: 999px;
  background: #cbd5e1;
}
</style>


