<template>
  <section class="prediction-runs-page">
    <header class="page-header">
      <div><h1>Prediction Runs</h1><p>Prediction batches, model versions, completeness, and reproducibility evidence.</p></div>
      <div class="header-actions">
        <el-button :icon="Refresh" :loading="loading" @click="load">Refresh</el-button>
        <el-button type="primary" :icon="TrendCharts" :disabled="!selectedBatch" @click="openSeries">View Series</el-button>
      </div>
    </header>

    <section class="filters-panel">
      <label><span>Status</span><el-select v-model="statusFilter" clearable @change="load"><el-option label="All statuses" value="" /><el-option label="Success" value="success" /><el-option label="Running" value="running" /><el-option label="Failed" value="failed" /></el-select></label>
      <label><span>Batch</span><el-select v-model="selectedBatchId" filterable @change="selectBatch"><el-option v-for="item in batches" :key="item.id" :label="item.batchCode" :value="item.id" /></el-select></label>
      <div class="filter-batch"><PredictionBatchBadge :batch="selectedBatch" :completeness="detail?.completeness" /></div>
    </section>

    <section class="run-kpis">
      <RiskIndicator label="Total Batches" :value="batches.length" meta="Available run history" icon="batch" />
      <RiskIndicator label="Latest Status" :value="statusText(selectedBatch?.status)" :tone="selectedBatch?.status === 'success' ? 'success' : 'warning'" icon="batch" />
      <RiskIndicator label="Output Completeness" :value="`${numberText(detail?.completeness?.completenessPercent)}%`" :tone="detail?.completeness?.complete ? 'success' : 'warning'" icon="forecast" />
      <RiskIndicator label="Operational Gate" :value="gate?.executionEligible ? 'Eligible' : 'Blocked'" :meta="gateMeta" :tone="gate?.executionEligible ? 'success' : 'warning'" icon="risk" />
    </section>

    <section class="runs-workspace">
      <main class="panel batch-list-panel">
        <div class="panel-head"><strong>Prediction Batch Table</strong><span>{{ batches.length }} batches</span></div>
        <el-table :data="batches" height="100%" highlight-current-row @current-change="onCurrentBatch">
          <el-table-column prop="batchCode" label="Batch" min-width="190" show-overflow-tooltip />
          <el-table-column label="Base Time" width="145"><template #default="{ row }">{{ timeText(row.baseTime) }}</template></el-table-column>
          <el-table-column label="Forecast" width="112"><template #default="{ row }">{{ row.horizonMinutes }} min / {{ row.rollingSteps }}</template></el-table-column>
          <el-table-column prop="modelCount" label="Models" width="64" />
          <el-table-column label="Status" width="86"><template #default="{ row }"><el-tag :type="statusType(row.status)" effect="plain">{{ statusText(row.status) }}</el-tag></template></el-table-column>
          <el-table-column label="Action" width="72" fixed="right"><template #default="{ row }"><el-button text type="primary" @click.stop="selectBatch(row.id)">Inspect</el-button></template></el-table-column>
        </el-table>
      </main>

      <aside v-loading="detailLoading" class="panel batch-detail-panel">
        <div class="panel-head"><strong>Batch Detail</strong><el-tag v-if="gate" :type="gate.executionEligible ? 'success' : 'warning'">{{ gate.executionEligible ? 'Operationally Eligible' : 'Execution Blocked' }}</el-tag></div>
        <template v-if="detail">
          <div class="detail-facts">
            <article><span>Base Time</span><strong>{{ timeText(detail.batch?.baseTime) }}</strong></article>
            <article><span>Horizon</span><strong>{{ detail.batch?.horizonMinutes }} min / {{ detail.batch?.rollingSteps }} steps</strong></article>
            <article><span>Models</span><strong>{{ detail.completeness?.successfulModels }}/{{ detail.completeness?.expectedModels }} successful</strong></article>
            <article><span>Outputs</span><strong>{{ detail.completeness?.actualPointCount }}/{{ detail.completeness?.expectedPointCount }}</strong></article>
          </div>
          <el-tabs v-model="activeTab" class="detail-tabs">
            <el-tab-pane label="Model Runs" name="runs">
              <div class="model-run-list">
                <article v-for="run in detail.runs" :key="run.id">
                  <div><strong>{{ run.modelCode }}</strong><small>{{ run.targetType }} · {{ run.modelVersion }}</small></div>
                  <span>{{ run.rollingSteps }} steps</span>
                  <el-tag size="small" :type="statusType(run.status)">{{ statusText(run.status) }}</el-tag>
                </article>
              </div>
            </el-tab-pane>
            <el-tab-pane label="Completeness" name="completeness">
              <div class="target-grid">
                <article v-for="target in detail.completeness?.targets" :key="target.targetType">
                  <div><strong>{{ target.targetType }}</strong><span>{{ target.featureCount }} targets</span></div>
                  <el-progress :percentage="Number(target.completenessPercent || 0)" :status="target.complete ? 'success' : 'warning'" />
                  <small>{{ target.coveredSteps }}/{{ detail.completeness?.expectedSteps }} steps · {{ target.missingPointCount }} missing</small>
                </article>
              </div>
            </el-tab-pane>
            <el-tab-pane label="Execution Gate" name="gate">
              <div class="gate-check-list">
                <article v-for="check in gateChecks" :key="check.label" :class="{ pass: check.valid, fail: !check.valid }">
                  <i></i><strong>{{ check.label }}</strong><span>{{ check.valid ? 'Passed' : 'Failed' }}</span>
                </article>
              </div>
              <dl v-if="gate" class="gate-facts">
                <dt>Mode</dt><dd>{{ gate.executionMode }}</dd>
                <dt>Reference Time</dt><dd>{{ timeText(gate.referenceTime) }}</dd>
                <dt>Batch Age</dt><dd>{{ gate.baseTimeAgeMinutes ?? '-' }} min / {{ gate.maxAgeMinutes ?? '-' }} min</dd>
                <dt>Gate Record</dt><dd>#{{ gate.id || '-' }}</dd>
              </dl>
              <el-alert v-if="!gate?.issues?.length" type="success" :closable="false" title="All operational execution checks passed" />
              <ul v-else class="issue-list"><li v-for="issue in gate.issues" :key="issue">{{ issue }}</li></ul>
            </el-tab-pane>
            <el-tab-pane label="Inputs & Hashes" name="evidence">
              <dl class="evidence-list">
                <dt>Pipeline</dt><dd>{{ detail.batch?.pipelineVersion || '-' }}</dd>
                <dt>Feature Mapping</dt><dd>{{ detail.batch?.featureMappingVersion || '-' }}</dd>
                <dt>Input Hash</dt><dd>{{ detail.batch?.inputHash || '-' }}</dd>
                <dt>Output Hash</dt><dd>{{ detail.batch?.outputHash || '-' }}</dd>
                <dt>Gate Hash</dt><dd>{{ gate?.gateHash || '-' }}</dd>
              </dl>
            </el-tab-pane>
            <el-tab-pane label="Diagnostics" name="diagnostics">
              <el-alert v-if="!detail.completeness?.issues?.length" type="success" :closable="false" title="No completeness or quality issues detected" />
              <ul v-else class="issue-list"><li v-for="issue in detail.completeness.issues" :key="issue">{{ issue }}</li></ul>
            </el-tab-pane>
          </el-tabs>
          <div class="detail-actions">
            <el-button @click="openSeries">View Series</el-button>
            <el-button @click="openEvents">Evaluate Rules</el-button>
            <el-button type="primary" :icon="DocumentChecked" @click="showReproduction">View Evidence</el-button>
          </div>
        </template>
        <el-empty v-else description="Select a prediction batch" />
      </aside>
    </section>

    <el-dialog v-model="reproductionVisible" title="Batch Evidence" width="620px">
      <dl v-if="detail" class="reproduction-list">
        <dt>Batch</dt><dd>{{ detail.batch?.batchCode }}</dd><dt>Pipeline</dt><dd>{{ detail.batch?.pipelineVersion }}</dd><dt>Feature Mapping</dt><dd>{{ detail.batch?.featureMappingVersion }}</dd><dt>Input Hash</dt><dd>{{ detail.batch?.inputHash }}</dd><dt>Output Hash</dt><dd>{{ detail.batch?.outputHash }}</dd><dt>Operational Gate</dt><dd>{{ gate?.gateHash || '-' }}</dd>
      </dl>
    </el-dialog>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { DocumentChecked, Refresh, TrendCharts } from '@element-plus/icons-vue'
import { listPredictionBatches, getPredictionBatchDetail, getPredictionExecutionGate } from '../../api/modules/prediction'
import { useProjectContext } from '../../composables/useProjectContext'
import RiskIndicator from '../../components/RiskIndicator.vue'
import PredictionBatchBadge from '../../components/PredictionBatchBadge.vue'
import type { PredictionBatch, PredictionBatchDetail, PredictionExecutionGate } from '../../types/engineering'

const router = useRouter()
const { projectId } = useProjectContext()
const loading = ref(false)
const detailLoading = ref(false)
const batches = ref<PredictionBatch[]>([])
const selectedBatchId = ref<number>()
const detail = ref<PredictionBatchDetail | null>(null)
const gate = ref<PredictionExecutionGate | null>(null)
const statusFilter = ref('')
const activeTab = ref('runs')
const reproductionVisible = ref(false)
const selectedBatch = computed(() => batches.value.find(item => item.id === selectedBatchId.value) || detail.value?.batch || null)
const gateMeta = computed(() => gate.value?.executionEligible
  ? `${gate.value.actualPointCount || 0}/${gate.value.expectedPointCount || 0} outputs validated`
  : gate.value?.issues?.[0] || 'Select a batch')
const gateChecks = computed(() => [
  { label: 'Model Set', valid: Boolean(gate.value?.modelSetValid) },
  { label: 'Feature Set', valid: Boolean(gate.value?.featureSetValid) },
  { label: `${gate.value?.expectedSteps ?? detail.value?.completeness?.expectedSteps ?? '-'}-Step Timeline`, valid: Boolean(gate.value?.timelineValid) },
  { label: 'Data Quality', valid: Boolean(gate.value?.qualityValid) },
  { label: 'Artifact Hashes', valid: Boolean(gate.value?.artifactHashValid) },
  { label: 'Operational Freshness', valid: Boolean(gate.value?.freshnessValid) }
])

async function load() {
  loading.value = true
  try {
    batches.value = await listPredictionBatches({ projectId: projectId.value, status: statusFilter.value || undefined, limit: 200 })
    if (!selectedBatchId.value || !batches.value.some(item => item.id === selectedBatchId.value)) selectedBatchId.value = batches.value[0]?.id
    await selectBatch(selectedBatchId.value)
  } finally { loading.value = false }
}
async function selectBatch(id?: number) {
  if (!id) { detail.value = null; gate.value = null; return }
  selectedBatchId.value = id
  detailLoading.value = true
  try {
    const [batchDetail, operationalGate] = await Promise.all([
      getPredictionBatchDetail(id),
      getPredictionExecutionGate(id, { mode: 'OPERATIONAL' })
    ])
    detail.value = batchDetail
    gate.value = operationalGate
  } finally { detailLoading.value = false }
}
function onCurrentBatch(row?: PredictionBatch) { if (row?.id) selectBatch(row.id) }
function openSeries() { router.push({ path: `/projects/${projectId.value}/data/low-frequency`, query: { batchId: selectedBatchId.value } }) }
function openEvents() { router.push({ path: `/projects/${projectId.value}/events`, query: { batchId: selectedBatchId.value, source: 'PREDICTION' } }) }
function showReproduction() { reproductionVisible.value = true }
const timeText = (value?: string) => value ? value.replace('T', ' ').slice(0, 19) : '-'
const numberText = (value?: number) => Number.isFinite(Number(value)) ? Number(value).toFixed(1) : '0.0'
const statusText = (value?: string) => value ? value.charAt(0).toUpperCase() + value.slice(1).toLowerCase() : 'Unknown'
const statusType = (value?: string) => value === 'success' ? 'success' : value === 'failed' ? 'danger' : 'warning'
onMounted(load)
</script>

<style scoped>
.prediction-runs-page { min-width: 1120px; min-height: calc(100vh - 92px); padding: 18px; box-sizing: border-box; background: #f4f7fb; color: #172033; }
.page-header { display: flex; align-items: center; justify-content: space-between; gap: 20px; margin-bottom: 14px; }
.page-header h1 { margin: 0; font-size: 23px; letter-spacing: 0; }.page-header p { margin: 4px 0 0; color: #64748b; font-size: 13px; }.header-actions { display: flex; gap: 8px; }
.filters-panel { display: grid; grid-template-columns: 180px 320px minmax(320px, 1fr); gap: 12px; align-items: end; padding: 14px; background: #fff; border: 1px solid #dce4ef; border-radius: 8px; }.filters-panel label span { display: block; margin-bottom: 6px; color: #475569; font-size: 12px; }.filters-panel :deep(.el-select) { width: 100%; }
.run-kpis { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 12px; margin: 12px 0; }
.runs-workspace { height: calc(100vh - 322px); min-height: 520px; display: grid; grid-template-columns: minmax(620px, 1fr) minmax(380px, 430px); gap: 12px; }.panel { min-width: 0; min-height: 0; padding: 14px; background: #fff; border: 1px solid #dce4ef; border-radius: 8px; box-sizing: border-box; }.panel-head { height: 34px; display: flex; align-items: flex-start; justify-content: space-between; gap: 12px; }.panel-head strong { font-size: 16px; }.panel-head span { color: #64748b; font-size: 12px; }.batch-list-panel { display: flex; flex-direction: column; }.batch-list-panel :deep(.el-table) { flex: 1; }
.batch-detail-panel { display: flex; flex-direction: column; overflow: hidden; }.detail-facts { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 8px; }.detail-facts article { padding: 10px; background: #f8fafc; border: 1px solid #e5eaf1; border-radius: 7px; }.detail-facts span,.detail-facts strong { display: block; }.detail-facts span { color: #64748b; font-size: 11px; }.detail-facts strong { margin-top: 4px; font-size: 13px; }.detail-tabs { flex: 1; min-height: 0; margin-top: 8px; }.detail-tabs :deep(.el-tabs__content),.detail-tabs :deep(.el-tab-pane) { height: calc(100% - 5px); overflow: auto; }
.model-run-list article { display: grid; grid-template-columns: minmax(0, 1fr) 72px 72px; align-items: center; gap: 8px; padding: 10px 4px; border-bottom: 1px solid #edf1f6; }.model-run-list strong,.model-run-list small { display: block; }.model-run-list small { margin-top: 2px; color: #64748b; }.model-run-list > article > span { color: #475569; font-size: 12px; }.target-grid { display: grid; gap: 8px; }.target-grid article { padding: 10px; border: 1px solid #e5eaf1; border-radius: 7px; }.target-grid article > div { display: flex; justify-content: space-between; margin-bottom: 6px; }.target-grid span,.target-grid small { color: #64748b; font-size: 11px; }.evidence-list,.reproduction-list { display: grid; grid-template-columns: 130px minmax(0, 1fr); margin: 0; }.evidence-list dt,.evidence-list dd,.reproduction-list dt,.reproduction-list dd { margin: 0; padding: 9px; border-bottom: 1px solid #e5eaf1; }.evidence-list dt,.reproduction-list dt { color: #64748b; }.evidence-list dd,.reproduction-list dd { overflow-wrap: anywhere; font-family: Consolas, monospace; font-size: 11px; }.issue-list { margin: 0; padding-left: 20px; color: #b45309; }.detail-actions { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 6px; padding-top: 10px; border-top: 1px solid #e5eaf1; }.detail-actions :deep(.el-button) { min-width: 0; margin: 0; padding-inline: 8px; }
.gate-check-list { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 7px; margin-bottom: 10px; }.gate-check-list article { display: grid; grid-template-columns: 10px minmax(0, 1fr) auto; align-items: center; gap: 7px; padding: 8px; border-bottom: 1px solid #e5eaf1; }.gate-check-list i { width: 8px; height: 8px; border-radius: 50%; background: #94a3b8; }.gate-check-list .pass i { background: #16a34a; }.gate-check-list .fail i { background: #dc2626; }.gate-check-list strong { font-size: 12px; }.gate-check-list span { color: #64748b; font-size: 11px; }.gate-facts { display: grid; grid-template-columns: 110px minmax(0, 1fr); margin: 0 0 10px; }.gate-facts dt,.gate-facts dd { margin: 0; padding: 6px 8px; border-bottom: 1px solid #edf1f6; }.gate-facts dt { color: #64748b; }.gate-facts dd { overflow-wrap: anywhere; }
@media (max-width: 1380px) { .runs-workspace { grid-template-columns: minmax(620px, 1fr) 390px; }.filters-panel { grid-template-columns: 160px 280px minmax(280px, 1fr); } }
</style>
