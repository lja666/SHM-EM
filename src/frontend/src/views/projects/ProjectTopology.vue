<template>
  <section class="em-page objects-page">
    <el-alert
      v-if="errorMessage"
      type="error"
      show-icon
      :closable="false"
      :title="errorMessage"
    />

    <section class="object-kpis">
      <article><span class="kpi-icon blue"><el-icon><Location /></el-icon></span><div><p>Field Points</p><strong>{{ displaySiteCount }}</strong></div></article>
      <article><span class="kpi-icon green"><el-icon><Cpu /></el-icon></span><div><p>Sensor Records</p><strong>{{ tree.instrumentCount || instrumentCount }}</strong></div></article>
      <article><span class="kpi-icon purple"><el-icon><TrendCharts /></el-icon></span><div><p>Metrics</p><strong>{{ metricCount }}</strong></div></article>
      <article><span class="kpi-icon orange"><el-icon><Connection /></el-icon></span><div><p>Registries</p><strong>{{ tree.registryCount || registryCount }}</strong></div></article>
    </section>

    <section class="object-layout">
      <aside class="shm-card object-tree-card">
        <div class="nav-head">
          <div>
            <strong>Device Navigation</strong>
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
            <div class="tree-node" :class="{ leaf: data.kind === 'instrument' || data.kind === 'metric' }">
              <div class="tree-node-main">
                <span class="node-label">{{ data.label }}</span>
                <small v-if="data.meta">{{ data.meta }}</small>
              </div>
              <span v-if="data.count !== undefined" class="node-count">{{ data.count }}</span>
            </div>
          </template>
        </el-tree>
        <div v-else class="empty-nav">No Objects</div>
      </aside>

      <main class="shm-card topology-card">
        <div class="card-head">
          <div>
            <h2>Project Plan / Object Location</h2>
          </div>
          <el-button size="small" @click="router.push(`/projects/${projectId}/data/low-frequency`)">Observation Data</el-button>
        </div>
        <div class="topology-surface point-layout-map">
          <div class="point-layout-stage">
            <img
              class="point-layout-image"
              src="/pit-point-layout.png"
              alt="Project Monitoring Point Layout"
              @error="imageReady = false"
              @load="imageReady = true"
            />
            <div v-if="!imageReady" class="topology-empty">
              <strong>Monitoring layout image failed to load</strong>
              <span>Check whether public/pit-point-layout.png exists.</span>
            </div>
            <button
              v-for="site in sitePoints"
              :key="site.siteNo"
              type="button"
              class="site-zone"
              :class="[site.levelClass, { selected: site.selected, disabled: !site.station }]"
              :style="{ left: `${site.x}%`, top: `${site.y}%`, width: `${siteBoxWidth}%`, height: `${siteBoxHeight}%` }"
              :title="site.title"
              @click="site.station && selectStation(site.station)"
            >
            </button>
          </div>
        </div>
        <div class="object-legend">
          <span><i class="online"></i>Online</span>
          <span><i class="offline"></i>Offline</span>
          <span><i class="incomplete"></i>Incomplete Configuration</span>
          <span><i class="disabled"></i>Unbound</span>
        </div>
      </main>

      <aside class="shm-card detail-card">
        <div class="card-head">
          <div>
            <h2>Device Details</h2>
          </div>
          <el-tag v-if="selectedStation" :type="deviceStatusType">
            {{ deviceStatusText }}
          </el-tag>
        </div>

        <template v-if="selectedStation">
          <div class="selected-object">
            <span class="object-icon"><el-icon><Location /></el-icon></span>
            <div>
              <strong>{{ selectedInstrument?.name || selectedInstrument?.code || selectedStation.name || selectedStation.code }}</strong>
              <small>{{ selectedInstrument ? instrumentName(selectedInstrument.instrumentType) : stationTypeName(selectedStation.stationType) }} · {{ siteNameOf(selectedStation) }}</small>
            </div>
          </div>

          <div v-if="selectedInstrument" class="device-monitor-summary" v-loading="metricLoading">
            <div class="metric-selector">
              <span>Primary Metric</span>
              <el-select
                :model-value="selectedMetric ? metricKey(selectedMetric) : ''"
                size="small"
                placeholder="Select Metric"
                @change="selectMetricByKey"
              >
                <el-option
                  v-for="metric in metricsOf(selectedInstrument)"
                  :key="metricKey(metric)"
                  :label="metric.name || metric.code || 'Unnamed Metric'"
                  :value="metricKey(metric)"
                />
              </el-select>
            </div>

            <section class="current-value">
              <span>Current Reading</span>
              <strong>{{ metricSummary.current }}</strong>
              <small>{{ metricSummary.metricName }}</small>
            </section>

            <div class="summary-grid">
              <article>
                <span>Max</span>
                <strong>{{ metricSummary.max }}</strong>
              </article>
              <article>
                <span>Minimum Value</span>
                <strong>{{ metricSummary.min }}</strong>
              </article>
              <article>
                <span>Delta</span>
                <strong :class="metricSummary.deltaClass">{{ metricSummary.delta }}</strong>
              </article>
            </div>

            <dl class="summary-meta">
              <dt>Latest Collection</dt><dd>{{ metricSummary.latestTime }}</dd>
              <dt>Device ID</dt><dd>{{ selectedInstrument.code || '-' }}</dd>
              <dt>Data Quality</dt><dd>{{ metricSummary.quality }}</dd>
            </dl>
          </div>
          <el-empty v-else description="No devices for the current point" />

          <div class="detail-actions">
            <el-button type="primary" @click="router.push(`/projects/${projectId}/data/low-frequency`)">View Observation Data</el-button>
            <el-button @click="router.push(`/projects/${projectId}/events`)">Rules and Events</el-button>
            <el-button @click="router.push(`/projects/${projectId}/events`)">View Events</el-button>
          </div>
        </template>
        <el-empty v-else description="No Selected Point" />
      </aside>

      <section class="shm-card station-table-card">
        <div class="card-head">
          <div>
            <h2>Instrument List</h2>
          </div>
        </div>
        <el-table :data="projectInstruments" height="330">
          <el-table-column label="Parent Point" min-width="130">
            <template #default="{ row }">{{ row.stationName }}</template>
          </el-table-column>
          <el-table-column label="Instrument ID" prop="code" min-width="150" />
          <el-table-column label="Instrument Type" min-width="140">
            <template #default="{ row }">{{ instrumentName(row.instrumentType) }}</template>
          </el-table-column>
          <el-table-column label="Sampling Mode" prop="samplingMode" min-width="120" />
          <el-table-column label="Sampling Frequency" width="110">
            <template #default="{ row }">{{ row.samplingFrequency || '-' }}</template>
          </el-table-column>
          <el-table-column label="Online Status" width="100">
            <template #default="{ row }"><el-tag size="small" :type="row.status === 'online' ? 'success' : 'info'">{{ row.status || '-' }}</el-tag></template>
          </el-table-column>
          <el-table-column label="Actions" width="90" fixed="right">
            <template #default="{ row }"><el-button text type="primary" @click="selectInstrumentRow(row)">View</el-button></template>
          </el-table-column>
        </el-table>
      </section>

      <section class="shm-card instrument-table-card">
        <div class="card-head">
          <div>
            <h2>Device Related Events</h2>
          </div>
        </div>
        <el-table :data="deviceWarnings" height="330">
          <el-table-column label="Warning Level" width="100">
            <template #default="{ row }"><el-tag size="small" :type="eventLevelTagType(row.eventLevel)">{{ levelName(levelClassOf(row.eventLevel)) }}</el-tag></template>
          </el-table-column>
          <el-table-column label="Point" min-width="130">
            <template #default="{ row }">{{ row.stationName }}</template>
          </el-table-column>
          <el-table-column label="Device" min-width="150">
            <template #default="{ row }">{{ row.instrumentName }}</template>
          </el-table-column>
          <el-table-column label="Metric" prop="metricCode" min-width="120" />
          <el-table-column label="Trigger Value" width="110">
            <template #default="{ row }">{{ warningValueText(row) }}</template>
          </el-table-column>
          <el-table-column label="Time" prop="detectedAt" min-width="160" />
          <el-table-column label="Status" width="100">
            <template #default="{ row }"><el-tag size="small" :type="row.eventStatus === 'closed' ? 'info' : 'warning'">{{ row.eventStatus || 'open' }}</el-tag></template>
          </el-table-column>
          <el-table-column label="Actions" width="90" fixed="right">
            <template #default="{ row }"><el-button text type="primary" @click="selectWarningRow(row)">Locate</el-button></template>
          </el-table-column>
        </el-table>
      </section>
    </section>
  </section>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { Connection, Cpu, Location, Search, TrendCharts } from '@element-plus/icons-vue'
import { useProjectContext } from '../../composables/useProjectContext'
import { getProjectObjectTree } from '../../api/modules/project'
import { listEvents } from '../../api/modules/event'
import { listLowFrequencyObservations } from '../../api/modules/observation'
import type { InstrumentNode, LowFrequencyObservation, MetricNode, MonitoringEvent, ProjectObjectTree, StationNode } from '../../types/engineering'

interface ObjectTreeNode {
  id: string
  label: string
  kind: 'station' | 'type' | 'instrument' | 'metric'
  meta?: string
  count?: number
  station?: StationNode
  instrument?: InstrumentNode
  metric?: MetricNode
  children?: ObjectTreeNode[]
}

interface DeviceNavRow {
  station: StationNode
  instrument: InstrumentNode
}

type ProjectInstrumentRow = InstrumentNode & {
  station: StationNode
  stationName: string
}

type DeviceWarningRow = MonitoringEvent & {
  station?: StationNode
  instrument?: InstrumentNode
  stationName: string
  instrumentName: string
}

type AssetStatus = 'online' | 'offline' | 'incomplete' | 'disabled'

const router = useRouter()
const { projectId } = useProjectContext()
const loading = ref(false)
const errorMessage = ref('')
const keyword = ref('')
const imageReady = ref(true)
const navMode = ref<'station' | 'instrument'>('station')
const tree = ref<ProjectObjectTree>({ stations: [] })
const events = ref<MonitoringEvent[]>([])
const metricRows = ref<LowFrequencyObservation[]>([])
const metricLoading = ref(false)
const selectedStation = ref<StationNode | null>(null)
const selectedInstrument = ref<InstrumentNode | null>(null)
const selectedMetric = ref<MetricNode | null>(null)
const navModeOptions = [
  { label: 'By Point', value: 'station' },
  { label: 'By Device', value: 'instrument' }
]
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

const stationNodes = computed(() => tree.value.stations || [])
const siteKeys = computed(() => {
  const keys = new Set<string>()
  stationNodes.value.forEach(station => keys.add(siteKeyOf(station)))
  return keys
})
const displaySiteCount = computed(() => Number(tree.value.siteCount || siteKeys.value.size || tree.value.stationCount || stationNodes.value.length))
const filteredStations = computed(() => stationNodes.value.filter(station => {
  const text = [
    station.name,
    station.code,
    ...instrumentsOf(station).flatMap(instrument => [instrument.name, instrument.code, ...metricsOf(instrument).map(metric => metric.code)])
  ].join(' ').toLowerCase()
  return !keyword.value || text.includes(keyword.value.toLowerCase())
}))
const instrumentCount = computed(() => stationNodes.value.reduce((sum, station) => sum + instrumentsOf(station).length, 0))
const onlineInstrumentCount = computed(() => stationNodes.value.reduce((sum, station) => sum + instrumentsOf(station).filter(item => item.status === 'online').length, 0))
const activeStationCount = computed(() => stationNodes.value.filter(station => station.status === 'active').length)
const activeSiteCount = computed(() => {
  const keys = new Set<string>()
  stationNodes.value.filter(station => station.status === 'active').forEach(station => keys.add(siteKeyOf(station)))
  return keys.size
})
const metricCount = computed(() => stationNodes.value.reduce((sum, station) => sum + stationMetricCount(station), 0))
const registryCount = computed(() => stationNodes.value.reduce((sum, station) => sum + instrumentsOf(station).reduce((inner, instrument) => inner + metricsOf(instrument).reduce((metricSum, metric) => metricSum + registriesOf(metric).length, 0), 0), 0))
const projectInstruments = computed<ProjectInstrumentRow[]>(() => stationNodes.value.flatMap(station => instrumentsOf(station).map(instrument => ({
  ...instrument,
  station,
  stationName: station.name || station.code || '-'
}))))
const deviceWarnings = computed<DeviceWarningRow[]>(() => events.value
  .slice()
  .sort((a, b) => timeValue(b.detectedAt) - timeValue(a.detectedAt))
  .map(event => {
    const station = stationNodes.value.find(item => Number(item.id) === Number(event.stationId))
    const instrument = station
      ? instrumentsOf(station).find(item => Number(item.id) === Number(event.instrumentId))
      : projectInstruments.value.find(item => Number(item.id) === Number(event.instrumentId))
    return {
      ...event,
      station,
      instrument,
      stationName: station?.name || station?.code || '-',
      instrumentName: instrument?.name || instrument?.code || '-'
    }
  }))
const stationBySiteNo = computed(() => {
  const map = new Map<string, StationNode>()
  stationNodes.value.forEach(station => {
    const siteNo = stationNoOf(station)
    if (siteNo && !map.has(siteNo)) map.set(siteNo, station)
  })
  siteCoordinates.forEach((site, index) => {
    if (!map.has(site.siteNo) && stationNodes.value[index]) {
      map.set(site.siteNo, stationNodes.value[index])
    }
  })
  return map
})
const sitePoints = computed(() => siteCoordinates.map(site => {
  const station = stationBySiteNo.value.get(site.siteNo)
  const status = station ? assetStatusOf(station) : 'disabled'
  return {
    ...site,
    station,
    status,
    levelClass: status,
    selected: station && selectedStation.value?.id === station.id,
    title: station
      ? `Point No. ${site.siteNo} · ${station.name || station.code} · ${assetStatusName(status)}`
      : `Point No. ${site.siteNo} - Unbound Object`
  }
}))
const objectTreeData = computed(() => navMode.value === 'instrument' ? buildInstrumentTree() : buildStationTree())
const defaultExpandedKeys = computed(() => objectTreeData.value.flatMap(node => {
  const child = node.children?.[0]
  return child ? [node.id, child.id] : [node.id]
}).slice(0, 10))
const currentNodeKey = computed(() => {
  if (selectedInstrument.value) return instrumentNodeId(selectedInstrument.value)
  if (selectedStation.value) return `site:${siteKeyOf(selectedStation.value)}`
  return ''
})
const metricSummary = computed(() => {
  const metric = selectedMetric.value
  const rows = metricRows.value
    .filter(row => row.metricValue !== undefined && row.metricValue !== null)
    .slice()
    .sort((a, b) => timeValue(a.observedAt) - timeValue(b.observedAt))
  const values = rows.map(row => Number(row.metricValue)).filter(Number.isFinite)
  const latest = rows[rows.length - 1]
  const unit = metric?.metricUnit || latest?.metricUnit || ''
  const currentValue = values.length ? values[values.length - 1] : null
  const previousValue = values.length > 1 ? values[values.length - 2] : null
  const deltaValue = currentValue !== null && previousValue !== null ? currentValue - previousValue : null
  return {
    metricName: metric?.name || metric?.code || 'Select a primary metric',
    current: formatMetricValue(currentValue, unit),
    max: formatMetricValue(values.length ? Math.max(...values) : null, unit),
    min: formatMetricValue(values.length ? Math.min(...values) : null, unit),
    delta: formatDeltaValue(deltaValue, unit),
    deltaClass: deltaValue === null ? '' : deltaValue > 0 ? 'up' : deltaValue < 0 ? 'down' : 'flat',
    latestTime: latest?.observedAt || '--',
    quality: latest?.qualityFlag || (values.length ? 'Valid' : selectedMetric.value && !queryableRegistryOf(selectedMetric.value) ? 'No Available Data Source' : 'No Data')
  }
})
const deviceStatusText = computed(() => {
  if (!selectedInstrument.value && !selectedStation.value) return '-'
  if (selectedInstrument.value?.status) return assetStatusName(assetStatusOfInstrument(selectedInstrument.value))
  return selectedStation.value ? assetStatusName(assetStatusOf(selectedStation.value)) : '-'
})
const deviceStatusType = computed(() => {
  const status = deviceStatusText.value.toLowerCase()
  if (status.includes('offline') || status.includes('Offline')) return 'info'
  if (status.includes('Incomplete Configuration')) return 'warning'
  return 'success'
})

async function load() {
  if (!projectId.value) return
  loading.value = true
  errorMessage.value = ''
  try {
    const [objectTree, eventRows] = await Promise.all([
      getProjectObjectTree(projectId.value),
      listEvents({ projectId: projectId.value, limit: 200 })
    ])
    tree.value = objectTree
    events.value = eventRows
    selectStation(objectTree.stations?.[0] || null)
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : 'Object topology API request failed'
    tree.value = { stations: [] }
    events.value = []
    selectStation(null)
  } finally {
    loading.value = false
  }
}

function selectStation(station: StationNode | null) {
  selectedStation.value = station
  selectedInstrument.value = station ? instrumentsOf(station)[0] || null : null
  selectedMetric.value = selectedInstrument.value ? metricsOf(selectedInstrument.value)[0] || null : null
}

function selectInstrument(instrument: InstrumentNode) {
  selectedInstrument.value = instrument
  selectedMetric.value = metricsOf(instrument)[0] || null
}

function selectInstrumentRow(row: ProjectInstrumentRow) {
  selectStation(row.station)
  selectedInstrument.value = row
  selectedMetric.value = metricsOf(row)[0] || null
}

function selectWarningRow(row: DeviceWarningRow) {
  if (row.station) selectStation(row.station)
  if (row.instrument) selectInstrument(row.instrument)
}

function selectMetric(metric: MetricNode) {
  selectedMetric.value = metric
}

function selectMetricByKey(key: string) {
  const metric = selectedInstrument.value ? metricsOf(selectedInstrument.value).find(item => metricKey(item) === key) : null
  if (metric) selectMetric(metric)
}

async function loadMetricRows() {
  metricRows.value = []
  if (!projectId.value || !selectedStation.value || !selectedInstrument.value || !selectedMetric.value) return
  const registry = queryableRegistryOf(selectedMetric.value)
  if (!registry?.code) return
  metricLoading.value = true
  try {
    metricRows.value = await listLowFrequencyObservations({
      registryCode: registry.code,
      projectId: projectId.value,
      stationId: selectedStation.value.id,
      instrumentId: selectedInstrument.value.id,
      metricCode: selectedMetric.value.code,
      limit: 96
    })
  } catch {
    metricRows.value = []
  } finally {
    metricLoading.value = false
  }
}

function buildStationTree(): ObjectTreeNode[] {
  const siteMap = new Map<string, { label: string; station: StationNode; rows: DeviceNavRow[] }>()
  filteredStations.value.forEach(station => {
    const key = siteKeyOf(station)
    const item = siteMap.get(key) || { label: siteNameOf(station), station, rows: [] }
    instrumentsOf(station).forEach(instrument => item.rows.push({ station, instrument }))
    siteMap.set(key, item)
  })
  return Array.from(siteMap.entries()).sort((a, b) => siteSortNo(a[0], a[1].label) - siteSortNo(b[0], b[1].label)).map(([siteKey, item]) => {
    const typeMap = groupRows(item.rows, row => String(row.instrument.instrumentType || 'other'))
    return {
      id: `site:${siteKey}`,
      label: item.label,
      kind: 'station',
      count: item.rows.length,
      station: item.station,
      children: Array.from(typeMap.entries()).sort((a, b) => instrumentName(a[0]).localeCompare(instrumentName(b[0]), 'zh-Hans-CN', { numeric: true })).map(([type, rows]) => ({
        id: `site:${siteKey}:type:${type}`,
        label: instrumentName(type),
        kind: 'type',
        count: rows.length,
        station: rows[0]?.station,
        children: rows.map(row => deviceTreeNode(row.station, row.instrument))
      }))
    }
  })
}

function buildInstrumentTree(): ObjectTreeNode[] {
  const typeMap = groupRows(deviceNavRows(), row => String(row.instrument.instrumentType || 'other'))
  return Array.from(typeMap.entries()).sort((a, b) => instrumentName(a[0]).localeCompare(instrumentName(b[0]), 'zh-Hans-CN', { numeric: true })).map(([type, rows]) => {
    const siteMap = new Map<string, { label: string; station: StationNode; rows: DeviceNavRow[] }>()
    rows.forEach(row => {
      const key = siteKeyOf(row.station)
      const item = siteMap.get(key) || { label: siteNameOf(row.station), station: row.station, rows: [] }
      item.rows.push(row)
      siteMap.set(key, item)
    })
    return {
      id: `type:${type}`,
      label: instrumentName(type),
      kind: 'type',
      count: rows.length,
      children: Array.from(siteMap.entries()).sort((a, b) => siteSortNo(a[0], a[1].label) - siteSortNo(b[0], b[1].label)).map(([siteKey, item]) => ({
        id: `type:${type}:site:${siteKey}`,
        label: item.label,
        kind: 'station',
        count: item.rows.length,
        station: item.station,
        children: item.rows.map(row => deviceTreeNode(row.station, row.instrument))
      }))
    }
  })
}

function onTreeNodeClick(data: ObjectTreeNode) {
  if (data.station) selectStation(data.station)
  if (data.instrument) selectInstrument(data.instrument)
  if (data.metric) selectMetric(data.metric)
}

function deviceNavRows() {
  return filteredStations.value.flatMap(station => instrumentsOf(station).map(instrument => ({ station, instrument })))
}

function deviceTreeNode(station: StationNode, instrument: InstrumentNode): ObjectTreeNode {
  return {
    id: instrumentNodeId(instrument),
    label: deviceLabel(instrument),
    kind: 'instrument',
    station,
    instrument
  }
}

function groupRows<T>(rows: T[], getKey: (row: T) => string) {
  const map = new Map<string, T[]>()
  rows.forEach(row => {
    const key = getKey(row)
    if (!map.has(key)) map.set(key, [])
    map.get(key)?.push(row)
  })
  return map
}

function stationNodeId(station: StationNode) {
  return `station:${stationKey(station)}`
}

function instrumentNodeId(instrument: InstrumentNode) {
  return `instrument:${instrumentKey(instrument)}`
}

function metricNodeId(metric: MetricNode) {
  return `metric:${metricKey(metric)}`
}

function instrumentsOf(station: StationNode) {
  return Array.isArray(station.instruments) ? station.instruments : []
}

function metricsOf(instrument: InstrumentNode) {
  return Array.isArray(instrument.metrics) ? instrument.metrics : []
}

function registriesOf(metric: MetricNode) {
  return Array.isArray(metric.registries) ? metric.registries : []
}

function queryableRegistryOf(metric: MetricNode) {
  return registriesOf(metric).find(registry => {
    const enabled = Number(registry.enabled ?? 1) === 1
    const queryable = Number(registry.queryable ?? 1) === 1
    const mode = String(registry.storageMode || '').toLowerCase()
    return enabled && queryable && (!mode || mode === 'low_frequency')
  })
}

function stationMetricCount(station: StationNode) {
  return instrumentsOf(station).reduce((sum, instrument) => sum + metricsOf(instrument).length, 0)
}

function assetStatusOf(station: StationNode): AssetStatus {
  const stationState = normalizedAssetState(station.status)
  if (stationState === 'offline') return 'offline'
  const instruments = instrumentsOf(station)
  if (!instruments.length) return 'incomplete'
  const instrumentStatuses = instruments.map(assetStatusOfInstrument)
  if (instrumentStatuses.every(status => status === 'offline')) return 'offline'
  if (instrumentStatuses.some(status => status === 'incomplete')) return 'incomplete'
  return 'online'
}

function assetStatusOfInstrument(instrument: InstrumentNode): AssetStatus {
  const state = normalizedAssetState(instrument.status)
  if (state === 'offline') return 'offline'
  const metrics = metricsOf(instrument)
  if (!metrics.length || metrics.every(metric => !registriesOf(metric).length)) return 'incomplete'
  return 'online'
}

function normalizedAssetState(status?: unknown) {
  const key = String(status || '').toLowerCase()
  if (['offline', 'inactive', 'disabled', 'lost', 'error', 'fault', 'Offline', 'Disabled', 'Abnormal'].some(item => key.includes(item))) return 'offline'
  return 'online'
}

function assetStatusName(status: AssetStatus) {
  const map: Record<AssetStatus, string> = {
    online: 'Online',
    offline: 'Offline',
    incomplete: 'Incomplete Configuration',
    disabled: 'Unbound'
  }
  return map[status]
}

function stationKey(station: StationNode) {
  return String(station.id || station.code)
}

function stationSortNo(station: StationNode) {
  return Number(siteNoOfStation(station) || Number.MAX_SAFE_INTEGER)
}

function instrumentKey(instrument: InstrumentNode) {
  return String(instrument.id || instrument.code)
}

function metricKey(metric: MetricNode) {
  return String(metric.id || metric.code)
}

function stationTypeName(type?: unknown) {
  const map: Record<string, string> = { displacement: 'Deep Horizontal Displacement', earth_pressure: 'Earth Pressure', settlement: 'Settlement', water_level: 'Water Level', vibration: 'Vibration' }
  const key = String(type || '')
  return map[key] || key || '-'
}

function instrumentName(type?: unknown) {
  const map: Record<string, string> = { displacement: 'Inclinometer', earth_pressure: 'Earth Pressure Cell', static_level: 'Static Level Gauge', pressure_water_level: 'Water Level Gauge', accelerometer: 'Accelerometer' }
  const key = String(type || '')
  return map[key] || key || '-'
}

function stationNoOf(station: StationNode) {
  return siteNoOfStation(station)
}

function siteNoOfStation(station: StationNode) {
  if (station.siteNo) return String(station.siteNo)
  const text = `${station.code || ''} ${station.name || ''} ${station.stationType || ''}`
  return siteNoOfText(text)
}

function siteKeyOf(station: StationNode) {
  const siteNo = siteNoOfStation(station)
  return siteNo ? `point-${siteNo}` : stationKey(station)
}

function siteNameOf(station: StationNode) {
  if (station.siteName) return String(station.siteName)
  const siteNo = siteNoOfStation(station)
  return siteNo ? `Point No. ${siteNo}` : station.name || station.code || 'Unnamed Point'
}

function siteSortNo(siteKey: string, label = '') {
  const siteNo = siteNoOfText(`${siteKey} ${label}`)
  return siteNo ? Number(siteNo) : Number.MAX_SAFE_INTEGER
}

function deviceLabel(instrument: InstrumentNode) {
  return instrument.code || instrument.name || 'Unnamed Instrument'
}

function siteNoOfText(text: string) {
  const match = text.match(/(?:ST[-_ ]?|station|Point|point)?([1-9])(?:No.|#|points|[^0-9]|$)/i)
  return match?.[1]
}

function levelClassOf(level?: unknown): keyof typeof levelRank {
  const key = String(level || '').toLowerCase()
  if (key.includes('red') || key.includes('critical') || key.includes('danger') || key.includes('Level 1')) return 'red'
  if (key.includes('orange') || key.includes('warning') || key.includes('Level 2')) return 'orange'
  if (key.includes('yellow') || key.includes('notice') || key.includes('Level 3')) return 'yellow'
  return 'normal'
}

function levelName(level?: unknown) {
  const key = String(level || '').toLowerCase()
  const map: Record<string, string> = { red: 'Severe', orange: 'High Risk', yellow: 'Medium Risk', normal: 'Normal' }
  return map[key] || String(level || 'Event')
}

function eventLevelTagType(level?: unknown) {
  const key = levelClassOf(level)
  if (key === 'red') return 'danger'
  if (key === 'orange' || key === 'yellow') return 'warning'
  return 'success'
}

function warningValueText(row: MonitoringEvent) {
  if (row.triggerValue === undefined || row.triggerValue === null) return '--'
  return `${Number(row.triggerValue).toFixed(3)}${row.unit ? ` ${row.unit}` : ''}`
}

function formatMetricValue(value: number | null, unit?: string) {
  if (value === null || !Number.isFinite(value)) return '--'
  return `${Number(value.toFixed(3))}${unit ? ` ${unit}` : ''}`
}

function formatDeltaValue(value: number | null, unit?: string) {
  if (value === null || !Number.isFinite(value)) return '--'
  const sign = value > 0 ? '+' : ''
  return `${sign}${Number(value.toFixed(3))}${unit ? ` ${unit}` : ''}`
}

function timeValue(value?: string) {
  if (!value) return 0
  const time = new Date(String(value).replace(' ', 'T')).getTime()
  return Number.isFinite(time) ? time : 0
}

watch(projectId, load, { immediate: true })
watch(
  () => [projectId.value, selectedStation.value?.id, selectedInstrument.value?.id, selectedMetric.value?.code],
  loadMetricRows
)
</script>

<style scoped>
:global(.main-panel:has(.objects-page)) {
  overflow-x: auto;
}
.objects-page {
  gap: 18px;
  min-width: 1180px;
}
.object-kpis {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: clamp(10px, .85vw, 16px);
}
.object-kpis article {
  display: flex;
  align-items: center;
  gap: clamp(10px, .85vw, 16px);
  min-height: clamp(70px, 6vw, 86px);
  padding: clamp(8px, .85vw, 12px);
  border: 1px solid var(--shm-border);
  border-radius: var(--shm-card-radius);
  background: #fff;
  box-shadow: var(--shm-card-shadow);
}
.kpi-icon { display: grid; place-items: center; width: 38px; height: 38px; min-width: 30px; border-radius: 11px; color: #fff; font-size: clamp(16px, 1.4vw, 22px); }
.kpi-icon.blue { background: linear-gradient(135deg, #2f6bff, #165dff); }
.kpi-icon.green { background: linear-gradient(135deg, #2ccf74, #16a34a); }
.kpi-icon.purple { background: linear-gradient(135deg, #8b5cf6, #5b5cf6); }
.kpi-icon.orange { background: linear-gradient(135deg, #ff9a2e, #f97316); }
.object-kpis p { margin: 0 0 6px; color: var(--shm-text-main); font-size: clamp(15px, .92vw, 17px); font-weight: 650; }
.object-kpis strong { display: block; color: var(--shm-text-title); font-size: clamp(16px, 1.45vw, 22px); line-height: 1; font-weight: 800; }
.object-layout {
  display: grid;
  grid-template-columns: repeat(12, minmax(0, 1fr));
  grid-auto-rows: auto;
  gap: 16px;
  align-items: stretch;
}
.shm-card {
  min-width: 0;
  padding: 20px;
  border: 1px solid var(--shm-border);
  border-radius: var(--shm-card-radius);
  background: #fff;
  box-shadow: var(--shm-card-shadow);
}
.object-tree-card,
.topology-card,
.detail-card,
.station-table-card,
.instrument-table-card {
  display: flex;
  flex-direction: column;
  min-height: 0;
  overflow: hidden;
}
.object-tree-card { order: 1; grid-column: 1 / 4; }
.topology-card { order: 2; grid-column: 4 / 10; }
.detail-card { order: 3; grid-column: 10 / 13; }
.station-table-card { order: 4; grid-column: 1 / 7; }
.instrument-table-card { order: 5; grid-column: 7 / 13; }
.object-tree-card,
.topology-card,
.detail-card {
  height: clamp(570px, 49.5vw, 690px);
}
.station-table-card,
.instrument-table-card {
  height: clamp(360px, 30vw, 430px);
}
.detail-card {
  overflow-y: scroll;
  scrollbar-gutter: stable;
}
.card-head {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  align-items: flex-start;
  margin-bottom: 14px;
}
.card-head h2 { margin: 0; color: var(--shm-text-title); font-size: 16px; font-weight: 750; }
.nav-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 12px;
}
.nav-head strong,
.nav-head span { display: block; }
.nav-head strong {
  color: var(--shm-text-title);
  font-size: 16px;
  font-weight: 800;
}
.nav-head span {
  margin-top: 5px;
  color: var(--shm-text-secondary);
  font-size: 16px;
}
.object-tree {
  flex: 1;
  min-height: 0;
  max-height: none;
  margin-top: 12px;
  overflow-y: scroll;
  scrollbar-gutter: stable;
  padding-right: 4px;
}
.object-tree :deep(.el-tree-node__content) {
  min-height: 42px;
  border-radius: 10px;
}
.object-tree :deep(.el-tree-node__content:hover) {
  background: #f4f7fb;
}
.object-tree :deep(.is-current > .el-tree-node__content) {
  background: #eef5ff;
  color: #0f4ec7;
}
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
  color: var(--shm-text-main);
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
  color: var(--shm-text-secondary);
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
.empty-nav {
  flex: 1;
  display: grid;
  place-items: center;
  color: var(--shm-text-secondary);
}
.tree-root {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px;
  border-radius: 10px;
  background: #f8fafc;
  color: var(--shm-text-main);
  font-weight: 700;
  font-size: 16px;
}
.tree-root span,
.node-main {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.tree-station {
  display: grid;
  gap: 5px;
  width: 100%;
  padding: 10px;
  border: 1px solid transparent;
  border-radius: 10px;
  background: #fff;
  color: var(--shm-text-main);
  text-align: left;
  cursor: pointer;
}
.tree-station:hover,
.tree-station.active {
  border-color: #bdd0ff;
  background: #f2f6ff;
}
.node-main { display: flex; align-items: center; gap: 8px; font-weight: 700; }
.tree-station small { color: var(--shm-text-secondary); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.topology-surface {
  container-type: size;
  flex: 1;
  position: relative;
  display: grid;
  place-items: center;
  width: 100%;
  min-height: 0;
  overflow: hidden;
  border: 1px solid var(--shm-border);
  border-radius: 12px;
  background: #fff;
}
.point-layout-stage {
  position: relative;
  width: 100%;
  height: auto;
  max-height: 100%;
  aspect-ratio: 1672 / 941;
}
.point-layout-image {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  object-fit: contain;
  background: #fff;
}
.site-zone {
  position: absolute;
  z-index: 2;
  padding: 0;
  border: clamp(1px, .14vw, 2px) solid var(--zone-color);
  border-radius: clamp(4px, .5vw, 7px);
  background: var(--zone-bg);
  box-shadow: 0 8px 18px rgba(15,23,42,.12);
  cursor: pointer;
  transition: transform .16s ease, box-shadow .16s ease, background .16s ease, opacity .16s ease;
}
.site-zone::before {
  content: "";
  position: absolute;
  inset: clamp(2px, .28vw, 3px);
  border: 1px solid rgba(255,255,255,.78);
  border-radius: clamp(3px, .35vw, 4px);
  pointer-events: none;
}
.site-zone.online { --zone-color: #1677ff; --zone-bg: rgba(22,119,255,.1); }
.site-zone.offline { --zone-color: #64748b; --zone-bg: rgba(100,116,139,.16); }
.site-zone.incomplete { --zone-color: #b7791f; --zone-bg: rgba(183,121,31,.16); }
.site-zone.disabled {
  --zone-color: #94a3b8;
  --zone-bg: rgba(148,163,184,.12);
  cursor: not-allowed;
  opacity: .62;
}
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
.topology-empty {
  position: absolute;
  inset: 0;
  z-index: 1;
  display: grid;
  place-content: center;
  justify-items: center;
  gap: 10px;
  max-width: 560px;
  margin: auto;
  text-align: center;
}
.topology-empty strong { color: var(--shm-text-title); font-size: 18px; }
.topology-empty span { color: var(--shm-text-secondary); line-height: 1.7; }
.object-legend {
  display: flex;
  flex-wrap: wrap;
  gap: 16px;
  margin-top: 12px;
  color: var(--shm-text-secondary);
  font-size: 16px;
}
.object-legend span { display: inline-flex; align-items: center; gap: 6px; }
.object-legend i { width: 9px; height: 9px; border-radius: 999px; background: var(--shm-primary); }
.object-legend i.online { background: #1677ff; }
.object-legend i.offline { background: #64748b; }
.object-legend i.incomplete { background: #b7791f; }
.object-legend i.disabled { background: #94a3b8; }
.selected-object {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px;
  border: 1px solid var(--shm-border);
  border-radius: 12px;
  background: #f8fafc;
}
.object-icon { display: grid; place-items: center; width: 38px; height: 38px; border-radius: 10px; background: #fff7ed; color: var(--shm-orange); }
.selected-object strong,
.selected-object small { display: block; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.selected-object small { margin-top: 4px; color: var(--shm-text-secondary); }
.device-monitor-summary {
  display: grid;
  align-content: start;
  gap: 12px;
  margin-bottom: 14px;
  padding: 12px;
  border: 1px solid #dbe5f2;
  border-radius: 10px;
  background: linear-gradient(180deg, #f8fbff 0%, #fff 100%);
}
.metric-selector {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr);
  align-items: center;
  gap: 10px;
}
.metric-selector span {
  color: var(--shm-text-secondary);
  font-size: 16px;
  font-weight: 650;
}
.current-value {
  display: grid;
  gap: 6px;
  padding: 12px;
  border-radius: 10px;
  background: #eef5ff;
}
.current-value span,
.summary-grid span,
.summary-meta dt {
  color: var(--shm-text-secondary);
  font-size: 16px;
}
.current-value strong {
  overflow: hidden;
  color: var(--shm-text-title);
  font-size: clamp(16px, 1.45vw, 22px);
  line-height: 1.05;
  font-weight: 850;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.current-value small {
  overflow: hidden;
  color: var(--shm-text-main);
  font-size: 16px;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.summary-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 8px;
}
.summary-grid article {
  display: grid;
  gap: 5px;
  min-width: 0;
  padding: 10px;
  border: 1px solid var(--shm-border);
  border-radius: 10px;
  background: #fff;
}
.summary-grid strong {
  overflow: hidden;
  color: var(--shm-text-title);
  font-size: 16px;
  font-weight: 800;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.summary-grid strong.up { color: #ef4444; }
.summary-grid strong.down { color: #16a34a; }
.summary-grid strong.flat { color: var(--shm-text-title); }
.summary-meta {
  display: grid;
  grid-template-columns: 74px minmax(0, 1fr);
  gap: 8px 10px;
  margin: 0;
}
.summary-meta dd {
  margin: 0;
  overflow: hidden;
  color: var(--shm-text-main);
  font-size: 16px;
  font-weight: 650;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.detail-actions { display: grid; gap: 8px; }
.detail-actions .el-button { width: 100%; margin-left: 0; }
.station-table-card :deep(.el-table),
.instrument-table-card :deep(.el-table) {
  flex: 1;
  font-size: 16px;
}
.object-tree::-webkit-scrollbar,
.detail-card::-webkit-scrollbar,
.device-monitor-summary::-webkit-scrollbar {
  width: 8px;
}
.object-tree::-webkit-scrollbar-track,
.detail-card::-webkit-scrollbar-track,
.device-monitor-summary::-webkit-scrollbar-track {
  border-radius: 999px;
  background: #eef3f9;
}
.object-tree::-webkit-scrollbar-thumb,
.detail-card::-webkit-scrollbar-thumb,
.device-monitor-summary::-webkit-scrollbar-thumb {
  border: 2px solid #eef3f9;
  border-radius: 999px;
  background: #b8c6d8;
}
@media (max-width: 900px) {
  .object-kpis { grid-template-columns: repeat(4, minmax(0, 1fr)); }
}
</style>


