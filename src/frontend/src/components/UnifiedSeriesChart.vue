<template><div ref="chartEl" class="unified-series-chart" /></template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { init, type ECharts, type EChartsOption } from '../utils/echarts'
import type { MetricSeriesPoint } from '../types/engineering'

const props = defineProps<{
  points: MetricSeriesPoint[]
  unit?: string
  warningThreshold?: number
  alarmThreshold?: number
  firstExceedanceTime?: string
}>()

const chartEl = ref<HTMLDivElement>()
let chart: ECharts | null = null
let observer: ResizeObserver | null = null

const observed = computed(() => props.points.filter(item => item.sourceType === 'OBSERVATION' && item.timestamp && item.value !== undefined))
const forecast = computed(() => props.points.filter(item => item.sourceType === 'PREDICTION' && item.timestamp && item.value !== undefined))
const baseTime = computed(() => forecast.value.find(item => item.originTime)?.originTime)
const hasBounds = computed(() => forecast.value.some(item => item.lowerBound !== undefined && item.upperBound !== undefined))

function render() {
  if (!chartEl.value) return
  if (!chart) chart = init(chartEl.value)
  const series: Record<string, unknown>[] = [
    line('Observed', observed.value, '#2563eb', 'solid'),
    line('Forecast', forecast.value, '#7c3aed', 'dashed')
  ]
  if (hasBounds.value) {
    series.unshift({ name: 'Forecast lower', type: 'line', stack: 'uncertainty', symbol: 'none', lineStyle: { opacity: 0 }, data: forecast.value.map(item => [item.timestamp, item.lowerBound]), tooltip: { show: false } })
    series.splice(1, 0, { name: 'Forecast uncertainty', type: 'line', stack: 'uncertainty', symbol: 'none', lineStyle: { opacity: 0 }, areaStyle: { color: 'rgba(124, 58, 237, .14)' }, data: forecast.value.map(item => [item.timestamp, Number(item.upperBound) - Number(item.lowerBound)]), tooltip: { show: false } })
  }
  const markLines: Record<string, unknown>[] = []
  if (props.warningThreshold !== undefined) markLines.push({ yAxis: props.warningThreshold, name: 'Warning threshold', lineStyle: { color: '#f59e0b', type: 'dashed' } })
  if (props.alarmThreshold !== undefined) markLines.push({ yAxis: props.alarmThreshold, name: 'Alarm threshold', lineStyle: { color: '#dc2626', type: 'dashed' } })
  if (baseTime.value) markLines.push({ xAxis: baseTime.value, name: 'Base time', lineStyle: { color: '#475569', type: 'dashed' } })
  ;(series.find(item => item.name === 'Observed') as Record<string, unknown>).markLine = { symbol: 'none', data: markLines, label: { color: '#475569', fontSize: 10 } }
  if (props.firstExceedanceTime) {
    const point = forecast.value.find(item => item.timestamp === props.firstExceedanceTime)
    if (point) (series.find(item => item.name === 'Forecast') as Record<string, unknown>).markPoint = { symbol: 'pin', symbolSize: 38, itemStyle: { color: '#dc2626' }, data: [{ name: 'First exceedance', coord: [point.timestamp, point.value] }] }
  }
  const option: EChartsOption = {
    animation: false,
    color: ['#2563eb', '#7c3aed'],
    tooltip: { trigger: 'axis' },
    legend: { top: 4, right: 10, itemWidth: 22 },
    grid: { left: 48, right: 24, top: 42, bottom: 48, containLabel: true },
    xAxis: { type: 'time', axisLabel: { color: '#64748b' }, splitLine: { show: false } },
    yAxis: { type: 'value', name: props.unit || '', scale: true, axisLabel: { color: '#64748b' }, splitLine: { lineStyle: { color: '#e8edf5' } } },
    dataZoom: [{ type: 'inside' }, { type: 'slider', height: 18, bottom: 8 }],
    series
  }
  chart.setOption(option, true)
}

function line(name: string, rows: MetricSeriesPoint[], color: string, type: 'solid' | 'dashed') {
  return { name, type: 'line', symbol: 'none', smooth: false, connectNulls: false, lineStyle: { color, width: 2.2, type }, itemStyle: { color }, data: rows.map(item => [item.timestamp, item.value]) }
}

onMounted(() => { render(); observer = new ResizeObserver(() => chart?.resize()); if (chartEl.value) observer.observe(chartEl.value) })
onBeforeUnmount(() => { observer?.disconnect(); chart?.dispose(); chart = null })
watch(() => [props.points, props.unit, props.warningThreshold, props.alarmThreshold, props.firstExceedanceTime], render, { deep: true })
</script>

<style scoped>.unified-series-chart { width: 100%; height: 100%; min-height: 280px; }</style>
