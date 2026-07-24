<template>
  <el-drawer :model-value="modelValue" title="Forecast Event Evidence" size="520px" @update:model-value="emit('update:modelValue', $event)">
    <div v-loading="loading" class="evidence-drawer">
      <el-alert v-if="error" type="warning" :closable="false" :title="error" />
      <template v-if="trace">
        <div class="evidence-summary">
          <article><span>Lead Time</span><strong>{{ trace.leadTimeMinutes ?? '-' }} min</strong></article>
          <article><span>First Exceedance</span><strong>{{ timeText(trace.firstExceedanceTime) }}</strong></article>
          <article><span>Peak Forecast</span><strong>{{ trace.peakPredictedValue ?? '-' }}</strong></article>
          <article><span>Consecutive Steps</span><strong>{{ trace.consecutiveExceedanceSteps ?? '-' }}</strong></article>
          <article><span>Execution Gate</span><strong>{{ gateDecision }}</strong></article>
          <article><span>Gate Record</span><strong>#{{ trace.predictionGateId ?? '-' }}</strong></article>
        </div>
        <el-tabs>
          <el-tab-pane label="Model & Batch">
            <dl><template v-for="item in modelFacts" :key="item.label"><dt>{{ item.label }}</dt><dd>{{ item.value }}</dd></template></dl>
          </el-tab-pane>
          <el-tab-pane label="Input Window">
            <dl><template v-for="item in inputFacts" :key="item.label"><dt>{{ item.label }}</dt><dd>{{ item.value }}</dd></template></dl>
          </el-tab-pane>
          <el-tab-pane label="Hashes">
            <dl class="hash-list"><template v-for="item in hashFacts" :key="item.label"><dt>{{ item.label }}</dt><dd>{{ item.value }}</dd></template></dl>
          </el-tab-pane>
          <el-tab-pane label="Execution Gate">
            <dl><template v-for="item in gateFacts" :key="item.label"><dt>{{ item.label }}</dt><dd>{{ item.value }}</dd></template></dl>
            <el-alert v-if="trace.predictionGateId && trace.gateExecutionEligible && !gateIssues.length" class="gate-alert" type="success" :closable="false" title="Formal prediction execution gate passed" />
            <el-alert v-else-if="!trace.predictionGateId" class="gate-alert" type="warning" :closable="false" title="This event has no linked execution gate record" />
            <ul v-else class="gate-issues"><li v-for="issue in gateIssues" :key="issue">{{ issue }}</li></ul>
          </el-tab-pane>
          <el-tab-pane label="Evaluation Snapshot"><pre>{{ snapshotText }}</pre></el-tab-pane>
        </el-tabs>
      </template>
    </div>
  </el-drawer>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { getPredictionEventTrace } from '../api/modules/prediction'
import type { EventPredictionTrace } from '../types/engineering'

const props = defineProps<{ modelValue: boolean; eventId?: number | null }>()
const emit = defineEmits<{ 'update:modelValue': [value: boolean] }>()
const loading = ref(false)
const error = ref('')
const trace = ref<EventPredictionTrace | null>(null)
const timeText = (value?: string) => value ? value.replace('T', ' ').slice(0, 19) : '-'
const facts = (items: Array<[string, unknown]>) => items.map(([label, value]) => ({ label, value: value ?? '-' }))
const modelFacts = computed(() => facts([['Batch', trace.value?.batchCode], ['Batch Status', trace.value?.batchStatus], ['Pipeline', trace.value?.pipelineVersion], ['Feature Mapping', trace.value?.featureMappingVersion], ['Model', trace.value?.modelCode], ['Model Version', trace.value?.modelVersion], ['Target', trace.value?.targetType]]))
const inputFacts = computed(() => facts([['Base Time', timeText(trace.value?.baseTime)], ['Input Start', timeText(trace.value?.inputWindowStart)], ['Input End', timeText(trace.value?.inputWindowEnd)], ['Forecast Horizon', `${trace.value?.horizonMinutes ?? '-'} min`]]))
const hashFacts = computed(() => facts([['Artifact Hash', trace.value?.artifactHash], ['Input Schema Hash', trace.value?.inputSchemaHash], ['Input Hash', trace.value?.inputHash], ['Run Result Hash', trace.value?.runResultHash], ['Batch Output Hash', trace.value?.outputHash], ['Event Result Hash', trace.value?.resultHash]]))
const gateDecision = computed(() => !trace.value?.predictionGateId ? 'Not Recorded' : trace.value.gateExecutionEligible ? 'Passed' : 'Blocked')
const gateFacts = computed(() => facts([['Gate Record', trace.value?.predictionGateId ? `#${trace.value.predictionGateId}` : '-'], ['Mode', trace.value?.gateExecutionMode], ['Decision', gateDecision.value], ['Evaluated At', timeText(trace.value?.gateEvaluatedAt)], ['Gate Hash', trace.value?.gateHash]]))
const gateIssues = computed<string[]>(() => {
  try {
    const parsed = JSON.parse(trace.value?.gateIssuesJson || '[]')
    return Array.isArray(parsed) ? parsed.map(String) : []
  } catch {
    return trace.value?.gateIssuesJson ? [trace.value.gateIssuesJson] : []
  }
})
const snapshotText = computed(() => { try { return JSON.stringify(JSON.parse(trace.value?.forecastSnapshotJson || '{}'), null, 2) } catch { return trace.value?.forecastSnapshotJson || '-' } })

watch(() => [props.modelValue, props.eventId], async () => {
  if (!props.modelValue || !props.eventId) return
  loading.value = true; error.value = ''
  try { trace.value = await getPredictionEventTrace(props.eventId) }
  catch (err) { trace.value = null; error.value = err instanceof Error ? err.message : 'Forecast evidence is unavailable' }
  finally { loading.value = false }
}, { immediate: true })
</script>

<style scoped>
.evidence-drawer { min-height: 320px; }
.evidence-summary { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 10px; margin-bottom: 16px; }
.evidence-summary article { padding: 12px; background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 7px; }
.evidence-summary span, .evidence-summary strong { display: block; }
.evidence-summary span { color: #64748b; font-size: 12px; }
.evidence-summary strong { margin-top: 5px; color: #172033; }
dl { display: grid; grid-template-columns: 150px minmax(0, 1fr); margin: 0; border-top: 1px solid #e2e8f0; }
dt, dd { margin: 0; padding: 10px; border-bottom: 1px solid #e2e8f0; }
dt { color: #64748b; background: #f8fafc; }
dd { color: #172033; overflow-wrap: anywhere; }
.hash-list dd { font-family: Consolas, monospace; font-size: 11px; }
pre { margin: 0; padding: 12px; overflow: auto; color: #334155; background: #f8fafc; border-radius: 7px; font-size: 11px; }
.gate-alert { margin-top: 12px; }
.gate-issues { margin: 12px 0 0; padding-left: 20px; color: #b45309; }
</style>
