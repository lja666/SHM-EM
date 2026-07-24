<template>
  <section class="event-center">
    <section class="priority-strip">
      <button
        v-for="item in summary"
        :key="item.key"
        class="priority-card"
        :class="{ active: statusFilter === item.key, danger: item.tone === 'danger', warn: item.tone === 'warn' }"
        type="button"
        @click="statusFilter = item.key"
      >
        <span>{{ item.label }}</span>
        <strong>{{ item.value }}</strong>
        <small>{{ item.note }}</small>
      </button>
    </section>

    <section class="event-workspace">
      <section class="queue-panel">
        <div class="queue-toolbar">
          <div>
            <strong>Handling Queue</strong>
          </div>
          <el-input v-model="keyword" placeholder="Search event code, metric, or reason" clearable />
        </div>

        <div class="queue-list">
          <button
            v-for="event in filteredEvents"
            :key="event.id || event.eventCode"
            class="event-row"
            :class="{ active: selectedEvent?.id === event.id }"
            type="button"
            @click="selectQueueEvent(event)"
            @dblclick="openSelectedObservation"
          >
            <span class="level-pill" :class="`level-${event.eventLevel || 'normal'}`">{{ levelText(event.eventLevel) }}</span>
            <el-tag size="small" :type="isForecastEvent(event) ? 'warning' : 'info'">{{ isForecastEvent(event) ? 'Forecast' : 'Observed' }}</el-tag>
            <span class="event-main">
              <strong>{{ eventTitle(event) }}</strong>
              <small>{{ eventQueueSubtitle(event) }}</small>
            </span>
            <span class="event-state">{{ statusText(event.eventStatus) }}</span>
          </button>
          <el-empty v-if="!filteredEvents.length" description="No events under the current filter" />
        </div>
      </section>

      <aside class="event-detail-panel">
        <div class="event-detail-head">
          <div>
            <span class="level-pill" :class="`level-${selectedEvent?.eventLevel || 'normal'}`">{{ levelText(selectedEvent?.eventLevel) }}</span>
            <el-tag v-if="selectedEvent" size="small" :type="isForecastEvent(selectedEvent) ? 'warning' : 'info'">{{ isForecastEvent(selectedEvent) ? 'Forecast' : 'Observed' }}</el-tag>
            <h2>{{ selectedEventTitle }}</h2>
          </div>
          <el-tag v-if="selectedEvent" effect="plain">{{ statusText(selectedEvent.eventStatus) }}</el-tag>
        </div>

        <section class="event-fact-grid">
          <article><span>Detected At</span><strong>{{ selectedEvent?.detectedAt || '-' }}</strong></article>
          <article><span>Related Object</span><strong>{{ selectedEventObjectText }}</strong></article>
          <article><span>Metric</span><strong>{{ selectedEventMetricText }}</strong></article>
          <article><span>Trigger / Threshold</span><strong>{{ selectedEventValueText }}</strong></article>
        </section>

        <section class="event-rule-box">
          <span>Handling Basis</span>
          <strong>{{ selectedEvent ? ruleNameOf(selectedEvent) : '-' }}</strong>
          <small v-if="selectedEvent">{{ sourceText(selectedEvent) }}</small>
        </section>

        <div class="event-action-grid">
          <el-button type="primary" :disabled="!selectedEvent" @click="openSelectedObservation">Open Analysis</el-button>
          <el-button :disabled="!selectedEvent" @click="router.push(`/projects/${projectId}/response/workflows?eventId=${selectedEvent?.id || ''}`)">Response Chain</el-button>
          <el-button v-if="selectedEvent && isForecastEvent(selectedEvent)" @click="showPredictionEvidence = true">Forecast Evidence</el-button>
          <el-button v-else @click="openRuleValidation">Evaluate Rule</el-button>
        </div>
      </aside>
    </section>

    <section class="support-tabs-card" :class="{ 'support-tabs-card--rules': activeSupportTab === 'rules' }">
      <el-tabs v-model="activeSupportTab" class="support-tabs">
        <el-tab-pane label="Object Filter" name="objects">
          <section class="support-object-pane">
            <aside class="operation-card object-query-card">
        <div class="object-picker-head">
          <div>
            <strong>Object Tree</strong>
          </div>
          <el-tag type="primary" effect="plain">{{ selectedInstrumentCount }} units</el-tag>
        </div>
        <el-tree
          ref="objectTreeRef"
          class="object-check-tree"
          :data="objectTreeData"
          node-key="id"
          show-checkbox
          default-expand-all
          :default-checked-keys="selectedObjectKeys"
          :props="{ children: 'children', label: 'label' }"
          @check="onObjectCheck"
        >
          <template #default="{ data }">
            <span class="check-node">
              <b>{{ data.label }}</b>
              <small v-if="data.meta">{{ data.meta }}</small>
            </span>
            <span v-if="data.count !== undefined" class="node-count">{{ data.count }}</span>
          </template>
        </el-tree>
        <div class="card-actions single">
          <el-button type="primary" :disabled="!selectedInstrumentCount && !selectedEvent" @click="openSelectedObservation">Open Observation Data</el-button>
        </div>
            </aside>
            <section class="run-events-card compact-run-events">
              <div class="panel-title compact">
                <strong>Execution Result Event</strong>
              </div>
              <div class="run-event-list">
                <button
                  v-for="event in runEvents"
                  :key="event.id || event.eventCode || `${event.metricCode}-${event.detectedAt}`"
                  type="button"
                  :class="{ active: selectedEvent === event || selectedEvent?.eventCode === event.eventCode }"
                  @click="selectRunEvent(event)"
                >
                  <span class="level-pill" :class="`level-${event.eventLevel || 'normal'}`">{{ levelText(event.eventLevel) }}</span>
                  <strong>{{ eventTitle(event) }}</strong>
                  <small>{{ valueText(event.triggerValue, event.unit) }} / {{ valueText(event.thresholdValue, event.unit) }}</small>
                </button>
                <el-empty v-if="!runEvents.length" description="Events will appear after execution" />
              </div>
            </section>
          </section>
        </el-tab-pane>
        <el-tab-pane label="Rule Configuration" name="rules">
          <section class="support-rule-pane">
            <main class="operation-card rule-config-card">
        <div class="rule-config-summary">
          <article>
            <span>Field</span>
            <strong>{{ selectedMetricCode || '-' }}</strong>
          </article>
          <article>
            <span>Mode</span>
            <strong>{{ ruleConfigMode === 'custom' ? 'Custom' : 'Existing Scheme' }}</strong>
          </article>
          <article>
            <span>Level</span>
            <strong>{{ ruleConfigMode === 'custom' ? `${enabledCustomThresholds.length} levels` : (selectedRule?.eventLevel || '-') }}</strong>
          </article>
        </div>
        <div class="rule-config-layout">
          <div class="field-list">
            <button
              v-for="field in metricFields"
              :key="field.code"
              type="button"
              :class="{ active: selectedMetricCode === field.code }"
              @click="selectedMetricCode = field.code"
            >
              <strong>{{ field.name }}</strong>
              <small>{{ field.code }} · {{ field.instrumentCount }} units · {{ field.ruleCount }} schemes</small>
            </button>
            <el-empty v-if="!metricFields.length" description="Select devices of the same type on the left first" />
          </div>
          <div class="rule-config-form">
            <div class="field-summary">
              <span>Current Field</span>
              <strong>{{ selectedMetricField?.name || '-' }}</strong>
              <small>{{ selectedMetricCode || '-' }}{{ selectedMetricField?.unit ? ` · ${selectedMetricField.unit}` : '' }}</small>
            </div>
            <div class="input-source-config">
              <span>Input Source</span>
              <el-radio-group v-model="inputSource" size="small">
                <el-radio-button value="OBSERVATION">Observation</el-radio-button>
                <el-radio-button value="PREDICTION">Prediction</el-radio-button>
              </el-radio-group>
            </div>
            <div v-if="inputSource === 'PREDICTION'" class="prediction-rule-grid">
              <label>
                <span>Prediction Batch</span>
                <el-select v-model="selectedPredictionBatchId" placeholder="Select a batch">
                  <el-option v-for="batch in predictionBatches" :key="batch.id" :label="`${batch.batchCode} · ${formatDateTimeText(batch.baseTime)}`" :value="Number(batch.id)" />
                </el-select>
              </label>
              <label>
                <span>Forecast Feature</span>
                <el-select v-model="selectedPredictionFeatureCode" filterable placeholder="Select a feature">
                  <el-option v-for="feature in predictionTargetFeatures" :key="feature.id" :label="feature.featureLabel || feature.featureCode" :value="feature.featureCode" />
                </el-select>
              </label>
              <label><span>Horizon</span><el-input-number v-model="forecastHorizonMinutes" :min="3" :max="1440" :step="3" controls-position="right" /><em>min</em></label>
              <label><span>Consecutive Steps</span><el-input-number v-model="minimumConsecutiveSteps" :min="1" :max="40" controls-position="right" /></label>
              <label>
                <span>Series Quality Filter</span>
                <el-select v-model="seriesQualityFilter">
                  <el-option label="Normal Only" value="normal" />
                  <el-option label="Allow All" value="allow_all" />
                </el-select>
              </label>
            </div>
            <el-radio-group v-model="ruleConfigMode" class="mode-switch" @change="onRuleModeChange" @click="onRuleModeClick">
              <el-radio-button value="existing">Existing Scheme</el-radio-button>
              <el-radio-button value="custom">Custom Rule</el-radio-button>
            </el-radio-group>
            <template v-if="ruleConfigMode === 'existing'">
              <dl class="step-facts rule-detail" :class="{ empty: !selectedRule }" @click="openRuleDialog">
                <template v-if="selectedRule">
                  <dt>Rule Code</dt><dd>{{ selectedRule.ruleCode || '-' }}</dd>
                  <dt>Rule Name</dt><dd>{{ selectedRule.ruleName || '-' }}</dd>
                  <dt>Level</dt><dd>{{ selectedRule.eventLevel || '-' }}</dd>
                  <dt>Operator</dt><dd>{{ selectedRule.operator || '-' }}</dd>
                  <dt>Threshold</dt><dd>{{ valueText(selectedRule.thresholdValue, selectedRule.thresholdUnit) }}</dd>
                </template>
                <template v-else>
                  <dt>Pending Selection</dt><dd>Click to select an existing threshold scheme</dd>
                  <dt>Candidate Schemes</dt><dd>{{ dialogRules.length }} items</dd>
                  <dt>Field</dt><dd>{{ selectedMetricCode || '-' }}</dd>
                  <dt>Object</dt><dd>{{ selectedInstrumentCount ? `${selectedInstrumentCount} instruments` : 'Not Selected' }}</dd>
                  <dt>Execution Window</dt><dd>Last 24 Hours</dd>
                </template>
              </dl>
            </template>
            <template v-else>
              <div class="custom-rule-grid multi-threshold-grid">
                <label>
                  <span>Operator</span>
                  <el-select v-model="customOperator">
                    <el-option label="Greater Than >" value=">" />
                    <el-option label="Greater Than or Equal >=" value=">=" />
                    <el-option label="Less Than <" value="<" />
                    <el-option label="Less Than or Equal <=" value="<=" />
                    <el-option label="Absolute Value >" value="abs_gt" />
                  </el-select>
                </label>
                <div class="threshold-levels">
                  <div class="threshold-level-row head">
                    <span>Enabled</span><span>Level</span><span>Threshold</span><span>Unit</span>
                  </div>
                  <div
                    v-for="item in customThresholds"
                    :key="item.level"
                    class="threshold-level-row"
                  >
                    <el-checkbox v-model="item.enabled" />
                    <strong :class="`level-${item.level}`">{{ item.label }}</strong>
                    <el-input-number v-model="item.value" :min="0" :step="1" controls-position="right" :disabled="!item.enabled" />
                    <em>{{ selectedMetricField?.unit || 'unit' }}</em>
                  </div>
                </div>
              </div>
            </template>
          </div>
        </div>
            </main>
          </section>
        </el-tab-pane>
        <el-tab-pane label="Evaluate / Execute" name="run">
          <section class="support-run-pane">
            <aside class="operation-card run-card">
        <div class="run-context">
          <article>
            <span>Input</span>
            <strong>{{ inputSource === 'PREDICTION' ? (selectedPredictionFeature?.featureLabel || 'Not Selected') : (selectedInstrumentCount ? `${selectedInstrumentCount} units / ${selectedStationIds.length} points` : 'Not Selected') }}</strong>
          </article>
          <article>
            <span>Metric</span>
            <strong>{{ selectedMetricCode || '-' }}</strong>
          </article>
          <article>
            <span>Input Source</span>
            <strong>{{ inputSource === 'PREDICTION' ? selectedPredictionBatch?.batchCode || 'Not Selected' : 'Observation · Last 24 Hours' }}</strong>
          </article>
          <article>
            <span>Threshold</span>
            <strong>{{ thresholdBrief }}</strong>
          </article>
        </div>
        <div class="signal-stack">
          <section>
            <strong>Evaluate</strong>
            <div class="signal-grid">
              <article :class="signalClass(objectReady)">
                <i></i><strong>Object</strong><span>{{ objectReady ? 'Selected' : 'Not Selected' }}</span>
              </article>
              <article :class="signalClass(ruleReady)">
                <i></i><strong>Rule</strong><span>{{ ruleReady ? 'Selected' : 'Not Selected' }}</span>
              </article>
              <article :class="signalClass(evaluateSignal === 'success')">
                <i></i><strong>Result</strong><span>{{ evaluateStatusText }}</span>
              </article>
            </div>
            <el-button type="primary" :loading="runningAction === 'evaluate'" @click="evaluateSelectedRule">Start Evaluation</el-button>
          </section>
          <section>
            <strong>Execute</strong>
            <el-alert
              v-if="inputSource === 'PREDICTION' && operationalGate && !operationalGate.executionEligible"
              class="execution-gate-alert"
              type="warning"
              :closable="false"
              :title="operationalGate.issues?.[0] || 'Prediction execution is blocked'"
            />
            <div class="signal-grid">
              <article :class="signalClass(objectReady)">
                <i></i><strong>Object</strong><span>{{ objectReady ? 'Selected' : 'Not Selected' }}</span>
              </article>
              <article :class="signalClass(ruleReady)">
                <i></i><strong>Rule</strong><span>{{ ruleReady ? 'Selected' : 'Not Selected' }}</span>
              </article>
              <article :class="signalClass(executeSignal === 'success')">
                <i></i><strong>Result</strong><span>{{ executeStatusText }}</span>
              </article>
            </div>
            <el-button type="danger" plain :loading="runningAction === 'execute'" :disabled="!formalExecutionReady" @click="executeSelectedRule">Create Formal Event</el-button>
          </section>
        </div>
            </aside>
          </section>
        </el-tab-pane>
      </el-tabs>
    </section>

    <el-dialog v-model="showRuleDialog" title="Rule Scheme Selection" width="860px">
      <div class="rule-dialog-head">
        <div>
          <strong>{{ selectedMetricCode || 'All Fields' }}</strong>
          <span>After selection, the scheme will be used as the evaluation and execution rule for the current field.</span>
        </div>
        <el-tag type="primary" effect="plain">{{ dialogRules.length }} schemes</el-tag>
      </div>
      <el-table :data="dialogRules" height="420" stripe highlight-current-row @row-click="markDialogRule">
        <el-table-column label="" width="56" align="center">
          <template #default="{ row }">
            <el-checkbox
              :model-value="Number(pendingRuleId) === Number(row.id)"
              @click.stop
              @change="setPendingRule(row, $event)"
            />
          </template>
        </el-table-column>
        <el-table-column prop="ruleCode" label="Rule Code" min-width="150" />
        <el-table-column prop="ruleName" label="Rule Name" min-width="180" />
        <el-table-column prop="metricCode" label="Field" min-width="170" />
        <el-table-column prop="eventLevel" label="Level" width="90" />
        <el-table-column prop="operator" label="Operator" width="90" />
        <el-table-column label="Threshold" width="120">
          <template #default="{ row }">{{ valueText(row.thresholdValue, row.thresholdUnit) }}</template>
        </el-table-column>
      </el-table>
      <template #footer>
        <el-button @click="showRuleDialog = false">Close</el-button>
        <el-button type="primary" :disabled="!pendingRuleId" @click="applyPendingRule">Use Selected Scheme</el-button>
      </template>
    </el-dialog>
    <PredictionEvidenceDrawer v-model="showPredictionEvidence" :event-id="selectedEvent?.id" />
  </section>
</template>

<script setup lang="ts">
import { computed, nextTick, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElRadioButton, ElRadioGroup } from 'element-plus'
import { listEvents } from '../../api/modules/event'
import { evaluateEventRule, executeEventRule, listEventRules } from '../../api/modules/eventRule'
import { getPredictionExecutionGate, listPredictionBatches, listPredictionFeatures } from '../../api/modules/prediction'
import { getProjectObjectTree } from '../../api/modules/project'
import { useProjectContext } from '../../composables/useProjectContext'
import PredictionEvidenceDrawer from '../../components/PredictionEvidenceDrawer.vue'
import type { EventRule, InstrumentNode, MonitoringEvent, PredictionBatch, PredictionExecutionGate, PredictionFeatureMapping, ProjectObjectTree, StationNode } from '../../types/engineering'

interface ObjectTreeNode {
  id: string
  label: string
  meta?: string
  count?: number
  kind: 'type' | 'site' | 'instrument'
  instrumentType?: string
  station?: StationNode
  instrument?: InstrumentNode
  children?: ObjectTreeNode[]
}

interface MetricFieldOption {
  code: string
  name: string
  unit?: string
  instrumentCount: number
  ruleCount: number
}

interface ThresholdLevelConfig {
  level: 'yellow' | 'orange' | 'red'
  label: string
  enabled: boolean
  value?: number
}

const router = useRouter()
const route = useRoute()
const { projectId } = useProjectContext()
const events = ref<MonitoringEvent[]>([])
const rules = ref<EventRule[]>([])
const predictionBatches = ref<PredictionBatch[]>([])
const predictionFeatures = ref<PredictionFeatureMapping[]>([])
const operationalGate = ref<PredictionExecutionGate | null>(null)
const gateLoading = ref(false)
const objectTree = ref<ProjectObjectTree | null>(null)
const objectTreeRef = ref<{ setCheckedKeys: (keys: string[]) => void } | null>(null)
const selectedEvent = ref<MonitoringEvent | null>(null)
const selectedRuleId = ref<number>()
const selectedObjectKeys = ref<string[]>([])
const autoLocatedObjectKey = ref('')
const showRuleDialog = ref(false)
const pendingRuleId = ref<number>()
const runEvents = ref<MonitoringEvent[]>([])
const selectedMetricCode = ref('')
const inputSource = ref<'OBSERVATION' | 'PREDICTION'>('OBSERVATION')
const selectedPredictionBatchId = ref<number>()
const selectedPredictionFeatureCode = ref('')
const forecastHorizonMinutes = ref(120)
const minimumConsecutiveSteps = ref(2)
const seriesQualityFilter = ref('normal')
const showPredictionEvidence = ref(false)
const ruleConfigMode = ref<'existing' | 'custom'>('existing')
const customOperator = ref('>')
const customThresholds = ref<ThresholdLevelConfig[]>([
  { level: 'yellow', label: 'Yellow Warning', enabled: true, value: 5 },
  { level: 'orange', label: 'Orange Warning', enabled: true, value: 10 },
  { level: 'red', label: 'Red Warning', enabled: false, value: 20 }
])
const runningAction = ref('')
const activeProcessStep = ref('observe')
const evaluateSignal = ref<'idle' | 'success' | 'error'>('idle')
const executeSignal = ref<'idle' | 'success' | 'error'>('idle')
const keyword = ref('')
const statusFilter = ref('attention')
const activeSupportTab = ref<'objects' | 'rules' | 'run'>('objects')
const reviewFilterOptions = [
  { label: 'Pending Judgement', value: 'attention' },
  { label: 'Newly Detected', value: 'open' },
  { label: 'Processing', value: 'acknowledged' },
  { label: 'All', value: 'all' }
]

const sortedEvents = computed(() => events.value.slice().sort((a, b) => {
  const level = levelWeight(b.eventLevel) - levelWeight(a.eventLevel)
  if (level) return level
  return String(b.detectedAt || '').localeCompare(String(a.detectedAt || ''))
}))

const filteredEvents = computed(() => {
  const text = keyword.value.trim().toLowerCase()
  return sortedEvents.value.filter(event => {
    const statusOk = statusFilter.value === 'all'
      || (statusFilter.value === 'attention' && !isClosed(event) && !isResolved(event))
      || event.eventStatus === statusFilter.value
    const textOk = !text || JSON.stringify(event).toLowerCase().includes(text)
    return statusOk && textOk
  })
})

const summary = computed(() => [
  { key: 'attention', label: 'Pending Judgement', value: events.value.filter(item => !isClosed(item) && !isResolved(item)).length, note: 'Prioritize Closed Loop', tone: 'warn' },
  { key: 'open', label: 'Newly Detected', value: events.value.filter(item => ['open', 'new'].includes(String(item.eventStatus))).length, note: 'Needs Confirmation', tone: 'warn' },
  { key: 'acknowledged', label: 'Processing', value: events.value.filter(item => item.eventStatus === 'acknowledged').length, note: 'Track Response', tone: 'normal' },
  { key: 'all', label: 'Red/Orange Events', value: events.value.filter(item => ['red', 'orange'].includes(String(item.eventLevel))).length, note: 'High Priority', tone: 'danger' }
])
const enabledRuleCount = computed(() => rules.value.filter(rule => Number(rule.enabled ?? 1) === 1).length || rules.value.length)
const closureReadyCount = computed(() => events.value.filter(item => item.eventStatus && item.eventStatus !== 'new' && item.eventStatus !== 'open').length)
const stations = computed(() => objectTree.value?.stations || [])
const objectTreeData = computed<ObjectTreeNode[]>(() => buildObjectTree())
const ruleMap = computed(() => {
  const map = new Map<string, EventRule>()
  rules.value.forEach(rule => {
    if (rule.id !== undefined) map.set(String(rule.id), rule)
    if (rule.metricCode) map.set(`metric:${rule.metricCode}`, rule)
  })
  return map
})
const selectedRule = computed(() => rules.value.find(rule => Number(rule.id) === Number(selectedRuleId.value)))
const selectedPredictionBatch = computed(() => predictionBatches.value.find(batch => Number(batch.id) === Number(selectedPredictionBatchId.value)))
const selectedPredictionFeature = computed(() => predictionFeatures.value.find(feature => feature.featureCode === selectedPredictionFeatureCode.value))
const predictionTargetFeatures = computed(() => predictionFeatures.value.filter(feature => Number(feature.predictionTarget ?? 1) === 1))
const predictionInputReady = computed(() => Boolean(selectedPredictionBatch.value?.id && selectedPredictionFeature.value?.featureCode))
const selectedInstruments = computed(() => {
  const selected = new Set(selectedObjectKeys.value)
  const rows: Array<{ station: StationNode; instrument: InstrumentNode }> = []
  stations.value.forEach(station => {
    ;(station.instruments || []).forEach(instrument => {
      const type = instrument.instrumentType || 'other'
      const typeKey = `type:${type}`
      const siteKey = `type:${type}:site:${siteKeyOf(station)}`
      const instrumentTreeKey = instrumentKey(station, instrument)
      if (selected.has(typeKey) || selected.has(siteKey) || selected.has(instrumentTreeKey)) {
        rows.push({ station, instrument })
      }
    })
  })
  return rows
})
const selectedInstrumentCount = computed(() => selectedInstruments.value.length)
const selectedStationIds = computed(() => Array.from(new Set(selectedInstruments.value.map(item => Number(item.station.id)).filter(Boolean))))
const selectedInstrumentType = computed(() => selectedInstruments.value[0]?.instrument.instrumentType || '')
const metricFields = computed<MetricFieldOption[]>(() => {
  const map = new Map<string, MetricFieldOption>()
  selectedInstruments.value.forEach(({ instrument }) => {
    ;(instrument.metrics || []).forEach(metric => {
      const code = metric.code || String(metric.id || '')
      if (!code) return
      const item = map.get(code) || {
        code,
        name: metric.name || code,
        unit: metric.metricUnit,
        instrumentCount: 0,
        ruleCount: 0
      }
      item.instrumentCount += 1
      if (!item.unit && metric.metricUnit) item.unit = metric.metricUnit
      map.set(code, item)
    })
  })
  const fields = Array.from(map.values())
  fields.forEach(field => {
    field.ruleCount = rules.value.filter(rule => rule.metricCode === field.code).length
  })
  return fields.sort((a, b) => b.ruleCount - a.ruleCount || a.name.localeCompare(b.name))
})
const selectedMetricField = computed(() => metricFields.value.find(field => field.code === selectedMetricCode.value))
const matchingRules = computed(() => rules.value.filter(rule => !selectedMetricCode.value || rule.metricCode === selectedMetricCode.value))
const dialogRules = computed(() => matchingRules.value.length ? matchingRules.value : rules.value)
const objectReady = computed(() => inputSource.value === 'PREDICTION' ? predictionInputReady.value : selectedInstrumentCount.value > 0)
const ruleReady = computed(() => {
  if (!selectedMetricCode.value) return false
  if (ruleConfigMode.value === 'custom') return enabledCustomThresholds.value.length > 0
  return !!selectedRule.value?.id
})
const formalExecutionReady = computed(() => objectReady.value
  && ruleReady.value
  && (inputSource.value !== 'PREDICTION' || (!gateLoading.value && Boolean(operationalGate.value?.executionEligible))))
const enabledCustomThresholds = computed(() => customThresholds.value.filter(item => item.enabled && item.value !== undefined && item.value !== null))
const thresholdBrief = computed(() => {
  if (ruleConfigMode.value === 'custom') {
    return enabledCustomThresholds.value.length
      ? enabledCustomThresholds.value.map(item => `${levelShortText(item.level)} ${item.value}`).join(' / ')
      : 'Not Configured'
  }
  return valueText(selectedRule.value?.thresholdValue, selectedRule.value?.thresholdUnit)
})
const evaluateStatusText = computed(() => evaluateSignal.value === 'success' ? 'Pass' : evaluateSignal.value === 'error' ? 'Failed' : 'Not Evaluated')
const executeStatusText = computed(() => executeSignal.value === 'success' ? 'Generated' : executeSignal.value === 'error' ? 'Failed' : 'Not Executed')
const selectedEventTitle = computed(() => selectedEvent.value ? eventTitle(selectedEvent.value) : 'No Event Selected')
const selectedEventValueText = computed(() => selectedEvent.value
  ? `${valueText(selectedEvent.value.triggerValue, selectedEvent.value.unit)} / ${valueText(selectedEvent.value.thresholdValue, selectedEvent.value.unit)}`
  : '-')
const selectedEventObjectText = computed(() => {
  const event = selectedEvent.value
  if (!event) return '-'
  return eventObjectText(event)
})
const selectedEventMetricText = computed(() => {
  const metricCode = selectedEvent.value?.metricCode
  if (!metricCode) return '-'
  const metric = metricFields.value.find(field => field.code === metricCode)
  return metric?.name || metricName(metricCode)
})
const processSteps = computed(() => [
  {
    code: 'observe',
    actor: 'backend',
    title: 'Observation Data Query',
    value: `${selectedInstrumentCount.value || stations.value.length}`,
    status: selectedInstrumentCount.value ? 'Selected Object' : 'Selectable',
    desc: 'Select a device type or a single instrument to query data',
    operationHint: 'The backend queries observation tables by event object, instrument, metric, and time window; the frontend opens the corresponding observation window.'
  },
  {
    code: 'configure',
    actor: 'frontend',
    title: 'Rule Configuration',
    value: `${enabledRuleCount.value}`,
    status: selectedRule.value ? 'Selected Rule' : 'Pending Selection',
    desc: 'View rule code, metric, level, and threshold',
    operationHint: 'The frontend displays rule instances and thresholds, then sends the selected ruleId to the backend for evaluation or execution.'
  },
  {
    code: 'evaluate',
    actor: 'backend',
    title: 'Evaluate',
    value: evaluateStatusText.value,
    status: objectReady.value && ruleReady.value ? 'Evaluable' : 'Not Ready',
    desc: 'Use status lights to confirm the object and rule before evaluation',
    operationHint: 'The backend performs side-effect-free rule evaluation and returns trigger values, thresholds, snapshots, and candidate event counts.'
  },
  {
    code: 'execute',
    actor: 'backend',
    title: 'Execute',
    value: executeStatusText.value,
    status: objectReady.value && ruleReady.value ? 'Executable' : 'Not Ready',
    desc: 'Persist event after object and rule are ready',
    operationHint: 'The backend persists evaluation batches, monitoring events, and metric snapshots, then triggers response orchestration.'
  },
  {
    code: 'review',
    actor: 'frontend',
    title: 'Event Review',
    value: `${filteredEvents.value.length}`,
    status: 'Filterable',
    desc: 'Filter queues and link objects with rules',
    operationHint: 'The frontend filters event queues, presents summaries, and opens observation windows and detail navigation.'
  },
  {
    code: 'close',
    actor: 'backend',
    title: 'Response Evidence Orchestration',
    value: `${closureReadyCount.value}`,
    status: 'Closed Loop',
    desc: 'Generate notifications, reports, and evidence',
    operationHint: 'The backend orchestrates notifications, reports, and evidence archiving; the frontend opens the response evidence workspace.'
  }
])
const activeStep = computed(() => processSteps.value.find(step => step.code === activeProcessStep.value) || processSteps.value[0])

function levelWeight(level?: string) {
  return ({ red: 4, orange: 3, yellow: 2, normal: 1 } as Record<string, number>)[String(level || '').toLowerCase()] || 0
}

function levelType(level?: string) {
  if (level === 'red') return 'danger'
  if (level === 'orange') return 'warning'
  if (level === 'yellow') return 'success'
  return 'info'
}

function levelText(level?: string) {
  return String(level || 'normal').toUpperCase()
}

function levelShortText(level?: string) {
  const map: Record<string, string> = { red: 'Red', orange: 'Orange', yellow: 'Yellow' }
  return map[String(level || '')] || String(level || '-')
}

function statusText(status?: string) {
  const map: Record<string, string> = {
    new: 'New Event',
    open: 'New Event',
    acknowledged: 'Acknowledged',
    resolved: 'Resolved',
    closed: 'Closed',
    pending: 'Pending',
    completed: 'Completed',
    finished: 'Completed',
    archived: 'Archived',
    failed: 'Failed'
  }
  return map[String(status || '')] || status || '-'
}

function valueText(value?: number, unit?: string) {
  if (value === undefined || value === null) return '-'
  return `${value}${unit ? ` ${unit}` : ''}`
}

function buildObjectTree(): ObjectTreeNode[] {
  const groups = new Map<string, { label: string; sites: Map<string, { label: string; station: StationNode; children: ObjectTreeNode[] }> }>()
  stations.value.forEach(station => {
    ;(station.instruments || []).forEach(instrument => {
      const type = instrument.instrumentType || 'other'
      if (!groups.has(type)) {
        groups.set(type, { label: instrumentTypeName(type), sites: new Map() })
      }
      const siteKey = siteKeyOf(station)
      const group = groups.get(type)
      if (!group?.sites.has(siteKey)) {
        group?.sites.set(siteKey, { label: siteNameOf(station), station, children: [] })
      }
      group?.sites.get(siteKey)?.children.push({
        id: instrumentKey(station, instrument),
        label: instrument.code || instrument.name || `Instrument-${instrument.id}`,
        kind: 'instrument',
        instrumentType: type,
        station,
        instrument
      })
    })
  })
  return Array.from(groups.entries()).map(([type, group]) => ({
    id: `type:${type}`,
    label: group.label,
    count: Array.from(group.sites.values()).reduce((sum, site) => sum + site.children.length, 0),
    kind: 'type',
    instrumentType: type,
    children: Array.from(group.sites.entries()).sort((a, b) => siteSortNo(a[0], a[1].label) - siteSortNo(b[0], b[1].label)).map(([siteKey, site]) => ({
      id: `type:${type}:site:${siteKey}`,
      label: site.label,
      count: site.children.length,
      kind: 'site',
      instrumentType: type,
      station: site.station,
      children: site.children
    }))
  }))
}

function onObjectCheck(node: ObjectTreeNode, state: { checkedKeys?: string[] }) {
  const locatedKey = autoLocatedObjectKey.value
  const rawKeys = (state.checkedKeys || []).map(String).filter(key => key !== locatedKey)
  if (locatedKey) autoLocatedObjectKey.value = ''
  const targetType = node.instrumentType || rawKeys.map(typeOfTreeKey).find(Boolean)
  const allowedKeys = targetType ? rawKeys.filter(key => typeOfTreeKey(key) === targetType) : rawKeys
  selectedObjectKeys.value = allowedKeys
  evaluateSignal.value = 'idle'
  executeSignal.value = 'idle'
  nextTick(() => objectTreeRef.value?.setCheckedKeys(allowedKeys))
  if (allowedKeys.length && allowedKeys.length !== rawKeys.length) ElMessage.warning('Only devices of the same type can be selected together; a single device can always be selected.')
}

function instrumentKey(station: StationNode, instrument: InstrumentNode) {
  return `instrument:${station.id || station.code}:${instrument.id || instrument.code}`
}

function instrumentKeyOfEvent(event: MonitoringEvent) {
  const stationId = String(event.stationId || '')
  const instrumentId = String(event.instrumentId || '')
  for (const station of stations.value) {
    const stationMatched = !stationId
      || [station.id, station.code, station.siteNo, station.siteName].some(value => String(value || '') === stationId)
    if (!stationMatched) continue
    for (const instrument of station.instruments || []) {
      const instrumentMatched = !instrumentId
        || [instrument.id, instrument.code, instrument.name].some(value => String(value || '') === instrumentId)
      if (instrumentMatched) return instrumentKey(station, instrument)
    }
  }
  return ''
}

function selectEventObject(event: MonitoringEvent) {
  const key = instrumentKeyOfEvent(event)
  if (!key) {
    ElMessage.warning('No device related to this event was found in the object tree')
    return
  }
  selectedObjectKeys.value = [key]
  autoLocatedObjectKey.value = key
  if (event.metricCode) selectedMetricCode.value = event.metricCode
  evaluateSignal.value = 'idle'
  executeSignal.value = 'idle'
  nextTick(() => {
    objectTreeRef.value?.setCheckedKeys([key])
    const checkedNode = document.querySelector('.object-check-tree .el-checkbox.is-checked')
    checkedNode?.scrollIntoView({ block: 'center', behavior: 'smooth' })
  })
}

function siteKeyOf(station: StationNode) {
  return String(station.siteNo || station.siteName || station.code || station.id || 'site')
}

function siteSortNo(key: string, label: string) {
  const text = `${key} ${label}`
  const match = text.match(/\d+/)
  return match ? Number(match[0]) : Number.MAX_SAFE_INTEGER
}

function siteNameOf(station: StationNode) {
  return station.siteName || station.name || station.code || `Point-${station.id}`
}

function instrumentTypeName(type?: string) {
  const map: Record<string, string> = {
    displacement: 'Inclinometer',
    pressure_water_level: 'Water Level Gauge',
    pressure_water_level_meter: 'Water Level Gauge',
    water_level: 'Water Level Gauge',
    water_level_meter: 'Water Level Gauge',
    static_level: 'Static Level Gauge',
    earth_pressure: 'Earth Pressure Cell',
    accelerometer: 'Accelerometer'
  }
  return map[String(type || '')] || type || 'Other Devices'
}

function metricName(metric?: string) {
  const key = String(metric || '')
  const map: Record<string, string> = {
    special_differential_water_level_cm: 'Actual Water Level Height',
    special_differential_water_level: 'Actual Water Level Height',
    pressure_water_level: 'Water Level Gauge Reading',
    groundwater_level: 'Groundwater Level',
    settlement: 'Cumulative Settlement',
    displacement: 'Horizontal Displacement',
    earth_pressure_kpa: 'Earth Pressure',
    earth_pressure_value: 'Earth Pressure',
    acceleration_pga_max: 'Peak Acceleration',
    acceleration_peak_vector: 'Composite Peak Acceleration'
  }
  return map[key] || key || 'Metric'
}

function typeOfTreeKey(key: string) {
  if (key.startsWith('type:')) return key.split(':')[1] || ''
  for (const station of stations.value) {
    for (const instrument of station.instruments || []) {
      if (instrumentKey(station, instrument) === key) return instrument.instrumentType || 'other'
    }
  }
  return ''
}

function signalClass(ok: boolean) {
  return ok ? 'signal-ok' : 'signal-wait'
}

function ruleNameOf(event: MonitoringEvent) {
  const rule = ruleMap.value.get(String(event.ruleId || '')) || ruleMap.value.get(`metric:${event.metricCode || ''}`)
  return rule?.ruleName || rule?.ruleCode || String(event.ruleId ? `Rule #${event.ruleId}` : 'Pending Rule Match')
}

function eventTitle(event: MonitoringEvent) {
  if (isForecastEvent(event)) return `Forecast threshold exceeded · ${metricName(event.metricCode)}`
  const reason = String(event.triggerReason || '').trim()
  if (reason && !isIdentifierText(reason)) return reason
  const type = String(event.eventType || '').trim()
  if (type && !isIdentifierText(type)) return type
  return event.metricCode || event.eventCode || `Event #${event.id || '-'}`
}

function isIdentifierText(value: string) {
  return /^[A-Z0-9_:-]+$/i.test(value) && /[_:-]/.test(value)
}

function sourceText(event: MonitoringEvent) {
  if (isForecastEvent(event)) return 'Forecast Rule Execution · Prediction Evidence Available'
  if (event.evaluationRunId) return 'Rule Execution Output'
  return 'Rule Execution Output'
}

function isForecastEvent(event: MonitoringEvent) {
  const source = String(event.sourceType || '').toUpperCase()
  return source === 'FORECAST' || source === 'PREDICTION'
}

function formatDateTimeText(value?: string) {
  return value ? value.replace('T', ' ').slice(0, 16) : '-'
}

function eventQueueSubtitle(event: MonitoringEvent) {
  const parts = [eventObjectText(event), event.detectedAt || '']
  return parts.filter(item => item && item !== '-').join(' · ') || 'Waiting for Object Association'
}

function eventObjectText(event: MonitoringEvent) {
  const station = findStation(event)
  const instrument = findInstrument(event, station)
  const stationText = namedField(event, 'stationName') || station?.name || station?.siteName || (event.stationId ? `Point No. ${event.stationId}` : '')
  const rawInstrumentText = namedField(event, 'instrumentName') || instrument?.name || ''
  const instrumentTypeText = instrumentTypeName(namedField(event, 'instrumentType') || instrument?.instrumentType || rawInstrumentText)
  const instrumentText = rawInstrumentText && !isIdentifierText(rawInstrumentText)
    ? rawInstrumentText
    : (instrumentTypeText !== 'Other Devices' ? instrumentTypeText : (instrument?.code || (event.instrumentId ? `Instrument${event.instrumentId}` : '')))
  if (stationText && instrumentText) return `${stationText} / ${instrumentText}`
  return stationText || instrumentText || '-'
}

function findStation(event: MonitoringEvent) {
  if (!event.stationId) return undefined
  return stations.value.find(station => Number(station.id) === Number(event.stationId))
}

function findInstrument(event: MonitoringEvent, station?: StationNode) {
  if (!event.instrumentId) return undefined
  const pools = station ? [station] : stations.value
  for (const item of pools) {
    const instrument = (item.instruments || []).find(row => Number(row.id) === Number(event.instrumentId))
    if (instrument) return instrument
  }
  return undefined
}

function namedField(event: MonitoringEvent, key: string) {
  const value = event[key]
  return typeof value === 'string' ? value.trim() : ''
}

function isAcknowledged(event: MonitoringEvent) {
  return ['acknowledged', 'resolved', 'closed'].includes(String(event.eventStatus))
}

function isResolved(event: MonitoringEvent) {
  return ['resolved', 'closed'].includes(String(event.eventStatus))
}

function isClosed(event: MonitoringEvent) {
  return event.eventStatus === 'closed'
}

function openEvent(row: MonitoringEvent) {
  selectedEvent.value = row
  selectEventObject(row)
}

function openObservation(row: MonitoringEvent) {
  openObservationPage({
    stationId: row.stationId,
    instrumentId: row.instrumentId,
    metricCode: row.metricCode,
    source: isForecastEvent(row) ? 'PREDICTION' : 'OBSERVATION',
    eventId: row.id,
    batchId: row.predictionBatchId
  })
}

function openObservationPage(query?: Record<string, string | number | undefined>) {
  router.push({
    path: `/projects/${projectId.value}/data/low-frequency`,
    query
  })
}

function openSelectedObservation() {
  if (selectedEvent.value && isForecastEvent(selectedEvent.value)) {
    openObservation(selectedEvent.value)
    return
  }
  const first = selectedInstruments.value[0]
  if (first) {
    openObservationPage({
      stationId: first.station.id,
      instrumentId: first.instrument.id,
      instrumentType: first.instrument.instrumentType,
      metricCode: selectedMetricCode.value || selectedRule.value?.metricCode || selectedEvent.value?.metricCode
    })
    return
  }
  if (selectedEvent.value) openObservation(selectedEvent.value)
}

function openRuleValidation() {
  activeSupportTab.value = 'run'
  if (selectedEvent.value?.metricCode) selectedMetricCode.value = selectedEvent.value.metricCode
  nextTick(() => {
    const card = document.querySelector('.support-tabs-card')
    card?.scrollIntoView({ block: 'start', behavior: 'smooth' })
  })
}

async function evaluateSelectedRule() {
  if (!ruleReady.value) {
    ElMessage.warning('Select a field and complete rule configuration first')
    return
  }
  if (!objectReady.value) {
    ElMessage.warning('Select devices or an event first')
    return
  }
  runningAction.value = 'evaluate'
  evaluateSignal.value = 'idle'
  try {
    const result = await evaluateEventRule(buildRulePayload('evaluate'))
    setRunEventsFromResult(result)
    evaluateSignal.value = 'success'
    ElMessage.success(`Evaluate completed; candidate events:  ${Number(result.eventCount || 0)} items`)
  } catch (error) {
    evaluateSignal.value = 'error'
    throw error
  } finally {
    runningAction.value = ''
  }
}

async function executeSelectedRule() {
  if (!ruleReady.value) {
    ElMessage.warning('Select a field and complete rule configuration first')
    return
  }
  if (!objectReady.value) {
    ElMessage.warning('Select devices or an event first')
    return
  }
  if (inputSource.value === 'PREDICTION' && !operationalGate.value?.executionEligible) {
    ElMessage.warning(operationalGate.value?.issues?.[0] || 'The selected prediction batch is not eligible for formal execution')
    return
  }
  runningAction.value = 'execute'
  executeSignal.value = 'idle'
  try {
    const result = await executeEventRule(buildRulePayload('execute'))
    setRunEventsFromResult(result)
    executeSignal.value = 'success'
    ElMessage.success('Execute completed; event and response chain generated')
    await load()
    if (runEvents.value[0]) selectedEvent.value = runEvents.value[0]
  } catch (error) {
    executeSignal.value = 'error'
    throw error
  } finally {
    runningAction.value = ''
  }
}

function setRunEventsFromResult(result: Record<string, unknown>) {
  const rows = extractResultEvents(result)
  runEvents.value = rows
  if (rows[0]) selectedEvent.value = rows[0]
}

function extractResultEvents(result: Record<string, unknown>) {
  const rows: MonitoringEvent[] = []
  if (Array.isArray(result.events)) rows.push(...result.events as MonitoringEvent[])
  const evaluation = result.evaluation && typeof result.evaluation === 'object' ? result.evaluation as Record<string, unknown> : null
  if (evaluation && Array.isArray(evaluation.events)) rows.push(...evaluation.events as MonitoringEvent[])
  if (result.event && typeof result.event === 'object') rows.unshift(result.event as MonitoringEvent)
  const seen = new Set<string>()
  return rows.filter(event => {
    const key = String(event.id || event.eventCode || `${event.metricCode}-${event.detectedAt}-${event.triggerValue}`)
    if (seen.has(key)) return false
    seen.add(key)
    return true
  })
}

function selectRunEvent(event: MonitoringEvent) {
  selectedEvent.value = event
  selectEventObject(event)
}

function selectQueueEvent(event: MonitoringEvent) {
  selectedEvent.value = event
  selectEventObject(event)
}

function onRuleModeChange(mode: string | number | boolean | undefined) {
  if (mode === 'existing') openRuleDialog()
}

function onRuleModeClick(event: MouseEvent) {
  const target = event.target as HTMLElement | null
  const button = target?.closest('.el-radio-button')
  if (button?.textContent?.includes('Existing Scheme')) openRuleDialog()
}

function openRuleDialog() {
  ruleConfigMode.value = 'existing'
  pendingRuleId.value = selectedRuleId.value || dialogRules.value[0]?.id
  showRuleDialog.value = true
}

function markDialogRule(rule: EventRule) {
  pendingRuleId.value = rule.id
}

function setPendingRule(rule: EventRule, checked: unknown) {
  pendingRuleId.value = checked ? rule.id : undefined
}

function applyPendingRule() {
  const rule = rules.value.find(item => Number(item.id) === Number(pendingRuleId.value))
  if (rule) selectRuleFromDialog(rule)
}

function selectRuleFromDialog(rule: EventRule) {
  selectedRuleId.value = rule.id
  selectedMetricCode.value = rule.metricCode || selectedMetricCode.value
  ruleConfigMode.value = 'existing'
  showRuleDialog.value = false
}

function buildRulePayload(runMode: 'evaluate' | 'execute') {
  const [observationStart, observationEnd] = latest24HourRange()
  const usingCustomRule = ruleConfigMode.value === 'custom'
  const rule = selectedRule.value
  const prediction = inputSource.value === 'PREDICTION'
  const feature = selectedPredictionFeature.value
  return {
    projectId: projectId.value,
    ruleId: usingCustomRule ? undefined : rule?.id,
    stationIds: prediction && feature?.stationId ? [Number(feature.stationId)] : selectedStationIds.value,
    instrumentIds: prediction && feature?.instrumentId ? [Number(feature.instrumentId)] : selectedInstruments.value.map(item => Number(item.instrument.id)).filter(Boolean),
    instrumentType: prediction ? undefined : selectedInstrumentType.value,
    metricCode: prediction ? feature?.sourceMetricCode : selectedMetricCode.value,
    startTime: prediction ? undefined : observationStart,
    endTime: prediction ? undefined : observationEnd,
    runMode,
    customRule: usingCustomRule,
    eventLevel: usingCustomRule ? highestCustomLevel() : rule?.eventLevel,
    operator: usingCustomRule ? customOperator.value : rule?.operator,
    thresholdValue: usingCustomRule ? highestCustomThreshold()?.value : rule?.thresholdValue,
    thresholds: usingCustomRule ? enabledCustomThresholds.value.map(item => ({ level: item.level, thresholdValue: item.value })) : undefined,
    thresholdUnit: selectedMetricField.value?.unit || rule?.thresholdUnit,
    inputSource: inputSource.value,
    predictionBatchId: prediction ? selectedPredictionBatch.value?.id : undefined,
    predictionBatchCode: prediction ? selectedPredictionBatch.value?.batchCode : undefined,
    predictionTargetType: prediction ? feature?.targetType : undefined,
    predictionFeatureCode: prediction ? feature?.featureCode : undefined,
    forecastHorizonMinutes: prediction ? forecastHorizonMinutes.value : undefined,
    minimumConsecutiveSteps: prediction ? minimumConsecutiveSteps.value : undefined,
    seriesQualityFilter: prediction ? seriesQualityFilter.value : undefined,
    predictionExecutionMode: prediction ? (runMode === 'execute' ? 'OPERATIONAL' : 'REPLAY') : undefined
  }
}

async function loadOperationalGate() {
  operationalGate.value = null
  if (inputSource.value !== 'PREDICTION' || !selectedPredictionBatchId.value) return
  gateLoading.value = true
  try {
    operationalGate.value = await getPredictionExecutionGate(selectedPredictionBatchId.value, { mode: 'OPERATIONAL' })
  } finally {
    gateLoading.value = false
  }
}

function highestCustomThreshold() {
  const order = ['red', 'orange', 'yellow']
  return enabledCustomThresholds.value.slice().sort((a, b) => order.indexOf(a.level) - order.indexOf(b.level))[0]
}

function highestCustomLevel() {
  return highestCustomThreshold()?.level
}

function latest24HourRange(): [string, string] {
  const end = new Date()
  const start = new Date(end.getTime() - 24 * 60 * 60 * 1000)
  return [formatDateTime(start), formatDateTime(end)]
}

function formatDateTime(value: Date) {
  const pad = (num: number) => String(num).padStart(2, '0')
  return `${value.getFullYear()}-${pad(value.getMonth() + 1)}-${pad(value.getDate())} ${pad(value.getHours())}:${pad(value.getMinutes())}:${pad(value.getSeconds())}`
}

async function load() {
  const [eventRows, ruleRows, objectRows, batches, features] = await Promise.all([
    listEvents({ projectId: projectId.value, limit: 500 }),
    listEventRules({ projectId: projectId.value, limit: 500 }),
    getProjectObjectTree(projectId.value),
    listPredictionBatches({ projectId: projectId.value, limit: 30 }),
    listPredictionFeatures({ projectId: projectId.value, limit: 500 })
  ])
  events.value = eventRows
  rules.value = ruleRows
  objectTree.value = objectRows
  predictionBatches.value = batches
  predictionFeatures.value = features
  const requestedSource = String(route.query.source || '').toUpperCase()
  const requestedBatchId = Number(route.query.batchId)
  const predictionRequested = requestedSource === 'PREDICTION' || requestedSource === 'FORECAST'
  if (predictionRequested) inputSource.value = 'PREDICTION'
  else if (requestedSource === 'OBSERVATION') inputSource.value = 'OBSERVATION'
  if (requestedBatchId && batches.some(batch => Number(batch.id) === requestedBatchId)) {
    selectedPredictionBatchId.value = requestedBatchId
  } else if (!selectedPredictionBatchId.value) {
    selectedPredictionBatchId.value = batches[0]?.id
  }
  if (!selectedPredictionFeatureCode.value) selectedPredictionFeatureCode.value = features.find(feature => Number(feature.predictionTarget ?? 1) === 1)?.featureCode || ''
  if (!selectedRuleId.value && ruleRows[0]?.id) selectedRuleId.value = ruleRows[0].id
  const requestedEventId = Number(route.query.eventId)
  selectedEvent.value = eventRows.find(event => requestedEventId && Number(event.id) === requestedEventId)
    || eventRows.find(event => predictionRequested ? isForecastEvent(event) : requestedSource === 'OBSERVATION' ? !isForecastEvent(event) : false)
    || sortedEvents.value[0]
    || null
}

watch(projectId, load, { immediate: true })
watch(metricFields, fields => {
  if (!fields.some(field => field.code === selectedMetricCode.value)) {
    selectedMetricCode.value = fields[0]?.code || ''
  }
}, { immediate: true })
watch(selectedMetricCode, () => {
  const firstRule = matchingRules.value[0]
  selectedRuleId.value = firstRule?.id
  ruleConfigMode.value = firstRule ? 'existing' : 'custom'
  evaluateSignal.value = 'idle'
  executeSignal.value = 'idle'
})
watch(selectedPredictionFeature, feature => {
  if (inputSource.value === 'PREDICTION' && feature?.sourceMetricCode) selectedMetricCode.value = feature.sourceMetricCode
})
watch(selectedPredictionBatchId, loadOperationalGate)
watch(inputSource, source => {
  if (source === 'PREDICTION' && selectedPredictionFeature.value?.sourceMetricCode) {
    selectedMetricCode.value = selectedPredictionFeature.value.sourceMetricCode
  }
  evaluateSignal.value = 'idle'
  executeSignal.value = 'idle'
  loadOperationalGate()
})
</script>

<style scoped>
:global(.main-panel:has(.event-center)) { overflow-x: auto; }
.event-center { display: flex; flex-direction: column; gap: 16px; min-width: 1320px; }
.priority-strip { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 12px; }
.priority-card { min-height: 96px; padding: 14px 16px; text-align: left; border: 1px solid var(--softx-border); border-radius: 8px; background: #fff; cursor: pointer; }
.priority-card.active { border-color: #2457d6; box-shadow: inset 0 0 0 1px rgba(36,87,214,.16); }
.priority-card.warn { background: #fffaf0; }
.priority-card.danger { background: #fff4f3; }
.priority-card span, .priority-card small { display: block; color: var(--softx-muted); }
.priority-card strong { display: block; margin: 8px 0 4px; font-size: 25px; color: var(--softx-text); }
.support-tabs-card {
  min-width: 0;
  height: 520px;
  padding: 16px;
  border: 1px solid var(--softx-border);
  border-radius: 8px;
  background: #fff;
  overflow: hidden;
}
.support-tabs-card--rules {
  height: 700px;
}
.support-tabs,
.support-tabs :deep(.el-tabs__content),
.support-tabs :deep(.el-tab-pane) {
  height: 100%;
}
.support-tabs :deep(.el-tabs__content) {
  overflow: hidden;
}
.support-object-pane {
  display: grid;
  grid-template-columns: 360px minmax(0, 1fr);
  gap: 16px;
  height: calc(100% - 8px);
  min-height: 0;
}
.support-rule-pane,
.support-run-pane {
  height: calc(100% - 8px);
  min-height: 0;
}
.operation-card {
  display: flex;
  flex-direction: column;
  min-width: 0;
  height: 100%;
  padding: 16px;
  border: 1px solid var(--softx-border);
  border-radius: 8px;
  background: #fff;
  overflow: hidden;
}
.panel-title {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  align-items: flex-start;
  margin-bottom: 14px;
}
.panel-title strong,
.panel-title span {
  display: block;
}
.panel-title strong {
  color: var(--softx-text);
  font-size: 16px;
}
.panel-title span {
  max-width: 560px;
  color: var(--softx-muted);
  line-height: 1.45;
}
.panel-title.compact {
  display: block;
}
.panel-title.compact strong {
  font-size: 16px;
}
.panel-title.compact span {
  margin-top: 5px;
  max-width: none;
}
.process-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 10px;
}
.process-kpi {
  min-width: 0;
  min-height: 142px;
  padding: 12px;
  border: 1px solid #e5ebf3;
  border-radius: 8px;
  background: #f8fafc;
  cursor: pointer;
  outline: none;
  transition: border-color .16s ease, background .16s ease, box-shadow .16s ease;
}
.process-kpi:hover,
.process-kpi.active {
  border-color: #2457d6;
  background: #f5f8ff;
  box-shadow: inset 0 0 0 1px rgba(36,87,214,.12);
}
.process-kpi-top {
  display: flex;
  justify-content: space-between;
  gap: 8px;
  align-items: center;
}
.process-kpi-top span,
.process-kpi-top b {
  display: inline-flex;
  align-items: center;
  height: 24px;
  padding: 0 8px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 750;
}
.process-kpi-top b {
  min-width: 0;
  overflow: hidden;
  background: #fff;
  color: var(--softx-muted);
  text-overflow: ellipsis;
  white-space: nowrap;
}
.process-kpi.actor-backend .process-kpi-top span { background: #eef5ff; color: #1d4ed8; }
.process-kpi.actor-frontend .process-kpi-top span { background: #ecfdf3; color: #087443; }
.process-kpi strong {
  display: block;
  margin-top: 10px;
  color: var(--softx-text);
}
.process-kpi em {
  display: block;
  margin-top: 8px;
  overflow: hidden;
  color: #17202a;
  font-size: 24px;
  font-style: normal;
  font-weight: 800;
  line-height: 1.05;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.process-kpi small {
  display: block;
  margin-top: 6px;
  color: var(--softx-muted);
  line-height: 1.45;
}
.step-controls {
  display: grid;
  grid-template-columns: minmax(0, 1fr);
  gap: 10px;
}
.object-picker-head {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  align-items: flex-start;
  margin-bottom: 14px;
}
.object-picker-head strong,
.object-picker-head span {
  display: block;
}
.object-picker-head strong {
  color: var(--softx-text);
  font-size: 16px;
  font-weight: 700;
  line-height: 1.45;
}
.object-picker-head span {
  margin-top: 4px;
  color: var(--softx-muted);
}
.object-check-tree {
  flex: 1;
  min-height: 0;
  max-height: none;
  overflow-y: auto;
  padding: 8px;
  border: 1px solid #e5ebf3;
  border-radius: 8px;
  background: #f8fafc;
}
.object-check-tree :deep(.el-tree-node__content) {
  min-height: 36px;
  border-radius: 8px;
}
.object-check-tree :deep(.el-tree-node__content:hover) {
  background: #eef5ff;
}
.check-node {
  display: grid;
  min-width: 0;
}
.check-node b,
.check-node small {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.check-node b {
  color: var(--softx-text);
}
.check-node small {
  color: var(--softx-muted);
}
.node-count {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 26px;
  height: 22px;
  margin-left: auto;
  padding: 0 8px;
  border-radius: 999px;
  background: #eef5ff;
  color: #2457d6;
  font-size: 12px;
  font-weight: 750;
}
.field-list {
  display: grid;
  gap: 8px;
  min-height: 0;
  overflow-y: auto;
  grid-auto-rows: minmax(58px, 1fr);
}
.rule-config-layout {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(560px, 1fr);
  gap: 12px;
  flex: 1;
  min-height: 0;
}
.card-actions {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 8px;
  margin-top: 12px;
}
.card-actions.single {
  grid-template-columns: 1fr;
}
.card-actions .el-button {
  width: 100%;
  margin-left: 0;
}
.rule-config-summary,
.run-context {
  display: grid;
  gap: 8px;
  margin-bottom: 10px;
}
.rule-config-summary {
  grid-template-columns: 1.2fr .8fr .7fr;
}
.run-context {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}
.rule-config-summary article,
.run-context article {
  min-width: 0;
  padding: 10px;
  border: 1px solid #e5ebf3;
  border-radius: 8px;
  background: #f8fafc;
}
.rule-config-summary span,
.run-context span,
.rule-config-summary strong,
.run-context strong {
  display: block;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.rule-config-summary span,
.run-context span {
  color: var(--softx-muted);
  font-size: 12px;
}
.rule-config-summary strong,
.run-context strong {
  margin-top: 4px;
  color: var(--softx-text);
  font-size: 14px;
}
.signal-stack {
  display: grid;
  grid-template-rows: repeat(2, minmax(0, 1fr));
  gap: 14px;
  flex: 1;
  min-height: 0;
  overflow: hidden;
}
.signal-stack section {
  display: grid;
  grid-template-rows: auto minmax(0, 1fr) auto;
  align-items: stretch;
  gap: 10px;
  min-height: 0;
  padding: 12px;
  border: 1px solid #e5ebf3;
  border-radius: 8px;
  background: #f8fafc;
}
.signal-stack section > strong {
  color: var(--softx-text);
}
.signal-stack .el-button {
  width: 100%;
  margin-left: 0;
}
.run-event-list {
  display: grid;
  gap: 8px;
  flex: 1;
  min-height: 0;
  align-content: start;
  overflow-y: auto;
}
.run-event-list button {
  display: grid;
  grid-template-columns: 76px minmax(0, 1fr) 170px;
  gap: 4px 8px;
  align-items: center;
  min-width: 0;
  padding: 8px;
  border: 1px solid #e5ebf3;
  border-radius: 8px;
  background: #fff;
  text-align: left;
  cursor: pointer;
}
.run-event-list button.active,
.run-event-list button:hover {
  border-color: #2457d6;
  background: #f5f8ff;
}
.run-event-list strong,
.run-event-list small {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.run-event-list strong { color: var(--softx-text); }
.run-event-list small {
  color: var(--softx-muted);
  font-size: 12px;
  text-align: right;
}
.field-list button {
  min-height: 0;
  padding: 10px;
  border: 1px solid #e5ebf3;
  border-radius: 8px;
  background: #f8fafc;
  text-align: left;
  cursor: pointer;
}
.field-list button.active,
.field-list button:hover {
  border-color: #2457d6;
  background: #f5f8ff;
}
.field-list strong,
.field-list small {
  display: block;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.field-list strong {
  color: var(--softx-text);
}
.field-list small {
  margin-top: 4px;
  color: var(--softx-muted);
}
.rule-config-form {
  display: flex;
  flex-direction: column;
  gap: 10px;
  min-width: 0;
  min-height: 0;
  padding-right: 2px;
  overflow-y: auto;
  scrollbar-gutter: stable;
}
.input-source-config {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 10px;
  border: 1px solid #e5ebf3;
  border-radius: 8px;
}
.input-source-config > span { color: var(--softx-muted); font-size: 12px; font-weight: 650; }
.prediction-rule-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
  padding: 12px;
  border: 1px dashed #a78bfa;
  border-radius: 8px;
  background: #faf8ff;
}
.prediction-rule-grid label { min-width: 0; display: grid; grid-template-columns: minmax(0, 1fr) auto; align-items: center; gap: 6px; }
.prediction-rule-grid label > span { grid-column: 1 / -1; color: var(--softx-muted); font-size: 12px; }
.prediction-rule-grid label > .el-select { grid-column: 1 / -1; width: 100%; }
.prediction-rule-grid em { color: var(--softx-muted); font-style: normal; font-size: 12px; }
.field-summary {
  padding: 10px;
  border: 1px solid #e5ebf3;
  border-radius: 8px;
  background: #f8fafc;
}
.field-summary span,
.field-summary strong,
.field-summary small {
  display: block;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.field-summary span,
.field-summary small {
  color: var(--softx-muted);
}
.field-summary strong {
  margin-top: 4px;
  color: var(--softx-text);
  font-size: 16px;
}
.mode-switch {
  width: 100%;
}
.mode-switch :deep(.el-radio-button) {
  flex: 1;
}
.mode-switch :deep(.el-radio-button__inner) {
  width: 100%;
}
.rule-config-form .el-select,
.custom-rule-grid .el-input-number {
  width: 100%;
}
.rule-detail {
  align-self: stretch;
  flex: 1;
  align-content: stretch;
  cursor: pointer;
}
.rule-detail dt,
.rule-detail dd {
  display: flex;
  align-items: center;
  min-height: 0;
}
.rule-detail.empty {
  border-style: dashed;
  background: #f5f8ff;
}
.custom-rule-grid {
  display: grid;
  grid-template-rows: auto auto;
  gap: 10px;
  flex: 0 0 auto;
  min-height: 0;
}
.custom-rule-grid label {
  display: grid;
  gap: 6px;
  color: var(--softx-muted);
  font-weight: 650;
}
.threshold-row {
  grid-template-columns: minmax(0, 1fr) 58px;
  align-items: end;
}
.threshold-row > span {
  grid-column: 1 / -1;
}
.threshold-row em {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  height: 32px;
  border: 1px solid #e5ebf3;
  border-radius: 8px;
  background: #f8fafc;
  color: var(--softx-muted);
  font-style: normal;
  font-weight: 650;
}
.threshold-levels {
  display: grid;
  grid-template-rows: auto repeat(3, minmax(42px, auto));
  gap: 8px;
  min-height: 0;
  padding: 8px;
  border: 1px solid #e5ebf3;
  border-radius: 8px;
  background: #f8fafc;
}
.threshold-level-row {
  display: grid;
  grid-template-columns: 58px 104px minmax(160px, 1fr) 72px;
  gap: 8px;
  align-items: center;
  min-height: 42px;
}
.threshold-level-row.head {
  color: var(--softx-muted);
  font-size: 12px;
  font-weight: 650;
}
.threshold-level-row strong {
  font-size: 13px;
  white-space: nowrap;
}
.threshold-level-row strong.level-red { color: #d92d20; }
.threshold-level-row strong.level-orange { color: #b55d00; }
.threshold-level-row strong.level-yellow { color: #8a6100; }
.threshold-level-row .el-input-number {
  width: 100%;
}
.threshold-level-row em {
  color: var(--softx-muted);
  font-style: normal;
  font-weight: 650;
}
.signal-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 8px;
  align-items: stretch;
  min-height: 0;
}
.signal-grid article {
  display: grid;
  gap: 5px;
  justify-items: start;
  align-content: center;
  min-width: 0;
  min-height: 0;
  padding: 10px;
  border: 1px solid #e5ebf3;
  border-radius: 8px;
  background: #f8fafc;
}
.signal-grid i {
  width: 12px;
  height: 12px;
  border-radius: 999px;
  box-shadow: 0 0 0 3px rgba(148,163,184,.16);
}
.signal-grid .signal-ok i {
  background: #22c55e;
  box-shadow: 0 0 0 3px rgba(34,197,94,.16);
}
.signal-grid .signal-wait i {
  background: #94a3b8;
}
.signal-grid strong,
.signal-grid span {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.signal-grid strong {
  color: var(--softx-text);
}
.signal-grid span {
  color: var(--softx-muted);
}
.step-facts {
  display: grid;
  grid-template-columns: 86px minmax(0, 1fr);
  gap: 8px 10px;
  margin: 0;
  padding: 10px;
  border: 1px solid #e5ebf3;
  border-radius: 8px;
  background: #f8fafc;
}
.step-facts dt {
  color: var(--softx-muted);
}
.step-facts dd {
  min-width: 0;
  margin: 0;
  overflow: hidden;
  color: var(--softx-text);
  font-weight: 650;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.rule-dialog-head {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  align-items: flex-start;
  margin-bottom: 12px;
}
.rule-dialog-head strong,
.rule-dialog-head span {
  display: block;
}
.rule-dialog-head strong {
  color: var(--softx-text);
}
.rule-dialog-head span {
  margin-top: 4px;
  color: var(--softx-muted);
}
.operation-links {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 8px;
  margin-top: 12px;
}
.operation-links button {
  min-height: 42px;
  border: 1px solid #e5ebf3;
  border-radius: 8px;
  background: #f8fafc;
  color: var(--softx-text);
  font-weight: 650;
  cursor: pointer;
}
.operation-links button:hover {
  border-color: #2457d6;
  background: #f5f8ff;
  color: #2457d6;
}
.event-workspace {
  display: grid;
  grid-template-columns: minmax(0, 1.28fr) minmax(360px, .72fr);
  gap: 16px;
  align-items: stretch;
  height: 440px;
  min-height: 0;
}
.event-detail-panel {
  box-sizing: border-box;
  display: flex;
  flex-direction: column;
  min-width: 0;
  min-height: 0;
  height: 100%;
  padding: 16px;
  border: 1px solid var(--softx-border);
  border-radius: 8px;
  background: #fff;
  overflow: hidden;
}
.event-detail-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 14px;
}
.event-detail-head h2 {
  display: -webkit-box;
  margin: 10px 0 0;
  overflow: hidden;
  color: var(--softx-text);
  font-size: 18px;
  font-weight: 820;
  line-height: 1.35;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 3;
}
.event-fact-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
}
.event-fact-grid article,
.event-reason-box,
.event-rule-box {
  min-width: 0;
  padding: 12px;
  border: 1px solid #e5ebf3;
  border-radius: 8px;
  background: #f8fafc;
}
.event-fact-grid span,
.event-reason-box span,
.event-rule-box span,
.event-rule-box small {
  display: block;
  overflow: hidden;
  color: var(--softx-muted);
  font-size: 12px;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.event-fact-grid strong,
.event-reason-box strong,
.event-rule-box strong {
  display: block;
  margin-top: 8px;
  overflow: hidden;
  color: var(--softx-text);
  font-size: 14px;
  font-weight: 750;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.event-reason-box,
.event-rule-box {
  margin-top: 12px;
}
.event-reason-box strong {
  display: -webkit-box;
  white-space: normal;
  line-height: 1.55;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 4;
}
.event-rule-box small {
  margin-top: 6px;
}
.event-action-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 8px;
  margin-top: 12px;
  padding-top: 0;
}
.event-action-grid .el-button {
  width: 100%;
  margin-left: 0;
}
.compact-run-events {
  min-height: 0;
  height: 100%;
}
.run-events-card,
.queue-panel { box-sizing: border-box; min-width: 0; min-height: 0; height: 100%; padding: 16px; background: #fff; border: 1px solid var(--softx-border); border-radius: 8px; }
.run-events-card,
.queue-panel { display: flex; flex-direction: column; overflow: hidden; }
.queue-toolbar { display: flex; align-items: flex-start; justify-content: space-between; gap: 12px; margin-bottom: 14px; }
.queue-toolbar strong { display: block; }
.queue-toolbar span { display: block; margin-top: 4px; color: var(--softx-muted); font-size: 12px; }
.queue-toolbar .el-input { width: 240px; }
.queue-list { display: flex; flex: 1; min-height: 0; flex-direction: column; gap: 8px; overflow: auto; }
.event-row { display: grid; grid-template-columns: 82px 74px minmax(0, 1fr) 76px; align-items: center; gap: 8px 10px; min-height: 74px; padding: 12px; border: 1px solid #e5ebf3; border-radius: 8px; background: #fff; text-align: left; cursor: pointer; }
.event-row.active { border-color: #2457d6; background: #f5f8ff; }
.event-main strong { display: block; color: var(--softx-text); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.event-main small { display: block; margin-top: 6px; color: var(--softx-muted); font-size: 12px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.event-state { font-weight: 650; color: #42526d; }
.level-pill { display: inline-flex; align-items: center; justify-content: center; height: 28px; border-radius: 999px; font-size: 12px; font-weight: 750; background: #eef2f6; color: #42526d; }
.level-red { background: #fff1f0; color: #d92d20; }
.level-orange { background: #fff4e5; color: #b55d00; }
.level-yellow { background: #fff9db; color: #8a6100; }
@media (max-width: 1180px) {
  .operation-card { height: 100%; min-height: 0; }
  .process-grid { grid-template-columns: repeat(3, minmax(0, 1fr)); }
  .priority-strip { grid-template-columns: repeat(4, minmax(0, 1fr)); }
  .event-workspace { grid-template-columns: minmax(0, 1.28fr) minmax(360px, .72fr); height: 440px; }
  .support-object-pane { grid-template-columns: 360px minmax(0, 1fr); height: calc(100% - 8px); }
  .support-tabs-card { min-height: 0; }
}
@media (max-width: 760px) {
  .priority-strip { grid-template-columns: repeat(4, minmax(0, 1fr)); }
  .process-grid { grid-template-columns: 1fr; }
  .rule-config-layout { grid-template-columns: minmax(0, 1fr) minmax(560px, 1fr); }
  .operation-links { grid-template-columns: 1fr; }
  .queue-toolbar { flex-direction: row; }
  .queue-toolbar .el-input { width: 240px; }
}
</style>


