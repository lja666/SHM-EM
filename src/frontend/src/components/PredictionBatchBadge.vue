<template>
  <div class="batch-badge" :class="statusClass">
    <span class="status-dot"></span>
    <div>
      <strong>{{ batch?.batchCode || 'No prediction batch' }}</strong>
      <small v-if="batch">{{ formatTime(batch.baseTime) }} · {{ batch.rollingSteps || 0 }} steps · {{ batch.horizonMinutes || 0 }} min</small>
    </div>
    <el-tag v-if="completeness" size="small" :type="completeness.executionEligible ? 'success' : 'warning'">
      {{ numberText(completeness.completenessPercent) }}%
    </el-tag>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { PredictionBatch, PredictionCompleteness } from '../types/engineering'

const props = defineProps<{ batch?: PredictionBatch | null; completeness?: PredictionCompleteness | null }>()
const statusClass = computed(() => `status-${String(props.batch?.status || 'empty').toLowerCase()}`)
const numberText = (value?: number) => Number.isFinite(Number(value)) ? Number(value).toFixed(1) : '0.0'
const formatTime = (value?: string) => value ? value.replace('T', ' ').slice(0, 19) : '-'
</script>

<style scoped>
.batch-badge { min-width: 0; display: grid; grid-template-columns: 10px minmax(0, 1fr) auto; align-items: center; gap: 10px; padding: 9px 11px; background: #f8fafc; border: 1px solid #dce4ef; border-radius: 7px; }
.status-dot { width: 8px; height: 8px; border-radius: 50%; background: #94a3b8; }
.batch-badge strong, .batch-badge small { display: block; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.batch-badge strong { color: #172033; font-size: 12px; }
.batch-badge small { margin-top: 2px; color: #64748b; font-size: 11px; }
.status-success .status-dot { background: #16a34a; }
.status-running .status-dot { background: #2563eb; }
.status-failed .status-dot { background: #dc2626; }
</style>
