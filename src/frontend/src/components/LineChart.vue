<template>
  <div ref="el" class="chart"></div>
</template>

<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { graphic, init, type ECharts } from '../utils/echarts'

const props = defineProps<{
  title?: string
  xData: string[]
  series: Array<{ name: string; data: Array<number | null> }>
  yName?: string
  threshold?: number
  eventPoints?: Array<{ name: string; xAxis: string; yAxis: number }>
  variant?: 'default' | 'trend' | 'rate' | 'waveform'
}>()

const el = ref<HTMLDivElement>()
let chart: ECharts | null = null

function render() {
  if (!el.value) return
  if (!chart) chart = init(el.value)
  const variant = props.variant || 'default'
  const isRate = variant === 'rate'
  const isTrend = variant === 'trend'
  const isWaveform = variant === 'waveform'
  const colors = isWaveform
    ? ['#2563eb', '#16a34a', '#f97316']
    : isRate
      ? ['#3b82f6']
      : ['#2563eb', '#16a34a', '#f97316', '#ef4444']
  chart.clear()
  chart.setOption({
    title: { text: props.title || '', left: 8, top: 2, textStyle: { fontSize: 14 } },
    color: colors,
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'cross', label: { backgroundColor: '#64748b' } }
    },
    legend: { top: 4, right: 8, itemWidth: 18, itemHeight: 8 },
    grid: { left: 46, right: isRate ? 18 : 28, top: isRate ? 30 : 46, bottom: isRate ? 44 : 38, containLabel: true },
    xAxis: {
      type: 'category',
      data: props.xData,
      boundaryGap: false,
      axisLabel: { hideOverlap: true, showMinLabel: true, showMaxLabel: true, color: '#64748b' },
      axisLine: { lineStyle: { color: '#dbe3ef' } },
      axisTick: { show: false }
    },
    yAxis: {
      type: 'value',
      name: props.yName || '',
      scale: true,
      boundaryGap: isRate ? ['25%', '25%'] : ['10%', '10%'],
      nameTextStyle: { color: '#475569', fontWeight: 650 },
      axisLabel: { color: '#64748b' },
      splitLine: { lineStyle: { color: '#e8edf5' } }
    },
    series: props.series.map((item, index) => {
      const seriesName = String(item.name || '').toLowerCase()
      const isDashed = ['warning', 'alarm', 'forecast', 'prediction'].some(token => seriesName.includes(token))
      return {
        ...item,
        type: 'line',
        smooth: !isWaveform,
        symbol: isTrend && (index === 0 || isDashed) ? 'circle' : 'none',
        symbolSize: isTrend && isDashed ? 4 : isTrend && index === 0 ? 5 : 0,
        showSymbol: false,
        lineStyle: {
          width: isDashed ? 2 : isRate ? 1.7 : 2.2,
          type: isDashed ? 'dashed' : 'solid'
        },
        areaStyle: isRate ? {
          color: new graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: 'rgba(59, 130, 246, .22)' },
            { offset: 1, color: 'rgba(59, 130, 246, 0)' }
          ])
        } : undefined,
        emphasis: { focus: 'series' },
        markLine: index === 0 && props.threshold !== undefined ? {
          symbol: 'none',
          lineStyle: { color: '#f97316', type: 'dashed', width: 1.4 },
          data: [{ yAxis: props.threshold, name: 'Rule Threshold' }],
          label: { formatter: 'Threshold {c}', color: '#f97316' }
        } : undefined,
        markPoint: index === 0 && props.eventPoints?.length ? {
          symbol: 'pin',
          symbolSize: 34,
          label: { color: '#fff', fontSize: 11 },
          itemStyle: { color: '#ef4444' },
          data: props.eventPoints
        } : undefined
      }
    })
  }, true)
  chart.resize()
}

const onResize = () => chart?.resize()
onMounted(() => {
  render()
  window.addEventListener('resize', onResize)
})
onBeforeUnmount(() => {
  window.removeEventListener('resize', onResize)
  chart?.dispose()
  chart = null
})
watch(() => [props.xData, props.series, props.title, props.yName, props.threshold, props.eventPoints, props.variant], render, { deep: true })
</script>

