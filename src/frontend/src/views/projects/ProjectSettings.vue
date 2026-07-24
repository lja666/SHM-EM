<template>
  <div class="project-settings">
    <section class="header-band">
      <div>
        <p class="eyebrow">PROJECT CONFIGURATION</p>
        <h1>{{ title }}</h1>
        <p class="subtitle">{{ subtitle }}</p>
      </div>
      <el-button :icon="Refresh" @click="load" :loading="loading">Refresh</el-button>
    </section>

    <section class="metric-row">
      <DataCard label="Monitoring Points" :value="monitoringPointCount" note="Field monitoring locations" />
      <DataCard label="Sensor Records" :value="summary.instrumentCount || objectTree.instrumentCount || 0" note="Unique registered sensor identifiers" />
      <DataCard label="Metrics" :value="summary.stationMetricCount || objectTree.stationMetricCount || 0" note="Point and metric bindings" />
      <DataCard label="Data Sources" :value="summary.registryCount || objectTree.registryCount || 0" note="Registered observation sources" />
    </section>

    <section class="settings-grid">
      <div class="panel">
        <div class="panel-head">
          <strong>Project Identity</strong>
        </div>
        <el-descriptions :column="1" border>
          <el-descriptions-item label="Project Code">{{ project.projectCode || '-' }}</el-descriptions-item>
          <el-descriptions-item label="Project Type">{{ project.infrastructureType || summary.infrastructureType || '-' }}</el-descriptions-item>
          <el-descriptions-item label="Scenario Label">{{ project.scenarioLabel || summary.scenarioLabel || '-' }}</el-descriptions-item>
          <el-descriptions-item label="Location">{{ project.locationText || summary.locationText || '-' }}</el-descriptions-item>
          <el-descriptions-item label="Status">{{ project.status || summary.status || '-' }}</el-descriptions-item>
        </el-descriptions>
      </div>

      <div class="panel">
        <div class="panel-head">
          <strong>Dataset Provenance</strong>
        </div>
        <el-descriptions :column="1" border>
          <el-descriptions-item label="Dataset">{{ dataset.datasetName || dataset.datasetCode || '-' }}</el-descriptions-item>
          <el-descriptions-item label="Scenario Type">{{ dataset.scenarioType || project.infrastructureType || '-' }}</el-descriptions-item>
          <el-descriptions-item label="Coverage">{{ formatCoverage(dataset.timeStart, dataset.timeEnd) }}</el-descriptions-item>
          <el-descriptions-item label="Reproducibility">{{ dataset.reproducibilityLevel || '-' }}</el-descriptions-item>
          <el-descriptions-item label="License">{{ dataset.license || 'See data availability statement' }}</el-descriptions-item>
        </el-descriptions>
      </div>
    </section>

    <section class="settings-grid">
      <div class="panel panel-wide">
        <div class="panel-head">
          <strong>Object Type Distribution</strong>
        </div>
        <div class="count-list">
          <div v-for="item in mergedCounts" :key="item.key" class="count-item">
            <span>{{ item.label }}</span>
            <strong>{{ item.value }}</strong>
          </div>
          <el-empty v-if="!mergedCounts.length" description="No Configuration Statistics" :image-size="72" />
        </div>
      </div>

    </section>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { Refresh } from '@element-plus/icons-vue'
import DataCard from '../../components/DataCard.vue'
import { getProjectContext, getProjectObjectTree } from '../../api/modules/project'
import type { CountItem, DatasetManifest, Project, ProjectCard, ProjectContext, ProjectObjectTree } from '../../types/engineering'

const route = useRoute()
const loading = ref(false)
const context = ref<ProjectContext>({})
const objectTree = ref<Partial<ProjectObjectTree>>({})

const projectId = computed(() => Number(route.params.projectId || 0))
const project = computed<Project>(() => context.value.project || {})
const summary = computed<ProjectCard>(() => context.value.summary || context.value.projectDisplay || {})
const dataset = computed<DatasetManifest>(() => context.value.dataset || {})
const title = computed(() => project.value.projectName || summary.value.projectName || summary.value.displayName || 'Project Settings')
const subtitle = computed(() => project.value.description || 'Project context, dataset provenance, and monitored-object configuration')
const monitoringPointCount = computed(() => Number(
  summary.value.siteCount
  ?? objectTree.value.siteCount
  ?? summary.value.stationCount
  ?? objectTree.value.stationCount
  ?? 0
))

const mergedCounts = computed(() => {
  const rows: Array<{ key: string; label: string; value: number }> = []
  rows.push({
    key: 'inventory-acquisition-modules',
    label: 'Acquisition Modules',
    value: Number(summary.value.acquisitionModuleCount ?? objectTree.value.acquisitionModuleCount ?? 0)
  })
  rows.push({
    key: 'inventory-dtus',
    label: 'DTUs',
    value: Number(summary.value.dtuCount ?? objectTree.value.dtuCount ?? 0)
  })
  appendCounts(rows, 'Installation Record Type', context.value.stationTypeCounts)
  appendCounts(rows, 'Sensor Type', context.value.instrumentTypeCounts)
  appendCounts(rows, 'Metric Type', context.value.metricCounts)
  appendCounts(rows, 'Event Level', context.value.eventLevelCounts)
  return rows
})

function appendCounts(rows: Array<{ key: string; label: string; value: number }>, prefix: string, counts?: CountItem[]) {
  ;(counts || []).forEach((item, index) => {
    rows.push({
      key: `${prefix}-${item.itemCode || index}`,
      label: `${prefix}: ${item.itemCode || '-'}`,
      value: Number(item.itemCount || 0)
    })
  })
}

function formatCoverage(start?: string, end?: string) {
  if (!start && !end) return '-'
  return `${start || '?'} to ${end || '?'}`
}

async function load() {
  if (!projectId.value) return
  loading.value = true
  try {
    const [ctx, tree] = await Promise.all([
      getProjectContext(projectId.value),
      getProjectObjectTree(projectId.value).catch(() => ({} as ProjectObjectTree))
    ])
    context.value = ctx || {}
    objectTree.value = tree || {}
  } finally {
    loading.value = false
  }
}

watch(projectId, load)
onMounted(load)
</script>

<style scoped>
.project-settings { display: flex; flex-direction: column; gap: 16px; width: 100%; }
.header-band, .panel { border: 1px solid var(--softx-border); border-radius: 8px; background: #fff; }
.header-band { display: flex; align-items: center; justify-content: space-between; gap: 16px; padding: 18px 20px; }
.eyebrow { margin: 0 0 4px; color: #2457d6; font-size: 12px; font-weight: 750; }
h1 { margin: 0; font-size: 24px; letter-spacing: 0; }
.subtitle { margin: 6px 0 0; color: var(--softx-muted); }
.metric-row, .settings-grid { display: grid; gap: 16px; }
.metric-row {
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
}
.metric-row :deep(.kpi) {
  min-width: 0;
  min-height: 112px;
  padding: 16px;
  border: 1px solid var(--softx-border);
  border-radius: 8px;
  background: #fff;
  box-shadow: none;
}
.metric-row :deep(.kpi-note) {
  line-height: 1.35;
  white-space: normal;
}
.settings-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
.panel { padding: 16px; min-width: 0; }
.panel-wide { grid-column: 1 / -1; }
.panel-head { display: flex; flex-direction: column; gap: 3px; margin-bottom: 12px; }
.panel-head strong { font-size: 15px; }
.panel-head span { color: var(--softx-muted); font-size: 12px; }
.count-list { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 10px; }
.count-item { display: flex; align-items: center; justify-content: space-between; gap: 12px; border: 1px solid var(--softx-border); border-radius: 8px; padding: 10px 12px; background: #f8fafc; }
.count-item span { color: var(--softx-muted); }
@media (max-width: 1120px) {
  .settings-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
}
@media (max-width: 720px) {
  .header-band { align-items: flex-start; flex-direction: column; }
  .settings-grid, .count-list { grid-template-columns: 1fr; }
}
</style>


