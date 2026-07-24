<template>
  <article class="risk-indicator" :class="[`tone-${tone}`, { interactive }]" @click="emit('activate')">
    <span class="risk-icon">
      <el-icon><component :is="resolvedIcon" /></el-icon>
    </span>
    <div class="risk-copy">
      <span>{{ label }}</span>
      <strong>{{ value }}</strong>
      <small v-if="meta">{{ meta }}</small>
    </div>
    <el-icon v-if="interactive" class="risk-arrow"><ArrowRight /></el-icon>
  </article>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { ArrowRight, Clock, Coin, TrendCharts, WarningFilled } from '@element-plus/icons-vue'

const props = withDefaults(defineProps<{
  label: string
  value: string | number
  meta?: string
  tone?: 'danger' | 'warning' | 'forecast' | 'neutral' | 'success'
  icon?: 'risk' | 'forecast' | 'time' | 'batch'
  interactive?: boolean
}>(), { tone: 'neutral', icon: 'risk', interactive: false })

const emit = defineEmits<{ activate: [] }>()
const resolvedIcon = computed(() => ({
  risk: WarningFilled,
  forecast: TrendCharts,
  time: Clock,
  batch: Coin
}[props.icon]))
</script>

<style scoped>
.risk-indicator { min-width: 0; min-height: 88px; padding: 14px 16px; display: grid; grid-template-columns: 38px minmax(0, 1fr) auto; align-items: center; gap: 12px; background: #fff; border: 1px solid #dce4ef; border-radius: 8px; box-sizing: border-box; }
.risk-indicator.interactive { cursor: pointer; }
.risk-indicator.interactive:hover { border-color: #8fb3ff; box-shadow: 0 6px 18px rgba(37, 99, 235, .08); }
.risk-icon { width: 38px; height: 38px; display: grid; place-items: center; border-radius: 8px; color: #475569; background: #f1f5f9; font-size: 20px; }
.risk-copy { min-width: 0; }
.risk-copy span, .risk-copy small { display: block; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; color: #64748b; }
.risk-copy span { font-size: 12px; }
.risk-copy strong { display: block; margin-top: 4px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; color: #172033; font-size: 20px; line-height: 1.15; }
.risk-copy small { margin-top: 4px; font-size: 11px; }
.risk-arrow { color: #94a3b8; }
.tone-danger .risk-icon { color: #dc2626; background: #fff1f2; }
.tone-danger .risk-copy strong { color: #c81e1e; }
.tone-warning .risk-icon { color: #d97706; background: #fff7ed; }
.tone-warning .risk-copy strong { color: #b45309; }
.tone-forecast { border-style: dashed; border-color: #a78bfa; }
.tone-forecast .risk-icon { color: #7c3aed; background: #f5f3ff; }
.tone-forecast .risk-copy strong { color: #6d28d9; }
.tone-success .risk-icon { color: #15803d; background: #f0fdf4; }
.tone-success .risk-copy strong { color: #15803d; }
@media (max-width: 1380px) {
  .risk-indicator { padding: 12px; gap: 9px; }
  .risk-copy strong { font-size: 17px; }
  .risk-copy small { display: none; }
}
</style>
