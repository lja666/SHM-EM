<template>
  <div class="card kpi">
    <div>
      <div class="kpi-label">{{ label }}</div>
      <div class="kpi-value">{{ value }}</div>
    </div>
    <div class="kpi-note"><slot>{{ note }}</slot></div>
  </div>
</template>
<script setup lang="ts">
defineProps<{ label: string; value: string | number; note?: string }>()
</script>
