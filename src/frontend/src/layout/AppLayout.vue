<template>
  <el-container class="layout-shell shm-shell">
    <el-aside :width="app.collapsed ? '76px' : '248px'" class="app-sidebar shm-sidebar">
      <div class="brand" :class="{ compact: app.collapsed }">
        <div class="brand-logo">{{ platform.logoText }}</div>
        <div v-if="!app.collapsed" class="brand-text">
          <strong>{{ platform.title }}</strong>
          <span>{{ platform.subtitle }}</span>
        </div>
      </div>
      <SidebarMenu :routes="menuRoutes" :collapsed="app.collapsed" />
    </el-aside>
    <el-container class="layout-main">
      <NavBar :collapsed="app.collapsed" @toggle="app.toggleCollapsed" />
      <el-main class="main-panel">
        <router-view v-slot="{ Component, route }">
          <component :is="Component" :key="`${String(route.name || '')}:${route.fullPath}:${app.refreshKey}`" />
        </router-view>
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup lang="ts">
import { onBeforeUnmount, onMounted } from 'vue'
import { useAppStore } from '../stores/app'
import { menuRoutes } from '../router'
import { platformConfig as platform } from '../config/platform'
import SidebarMenu from './components/SidebarMenu.vue'
import NavBar from './components/NavBar.vue'

const app = useAppStore()

function clamp(value: number, min: number, max: number) {
  return Math.min(max, Math.max(min, value))
}

function updateUiScale() {
  const width = window.innerWidth
  const height = window.innerHeight
  const scale = clamp(Math.min(width / 1920, height / 1080), 0.68, 1.08)
  document.documentElement.style.setProperty('--shm-ui-scale', scale.toFixed(4))
  document.documentElement.style.setProperty('--shm-scaled-vh', `${height / scale}px`)
}

onMounted(() => {
  updateUiScale()
  window.addEventListener('resize', updateUiScale)
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', updateUiScale)
})
</script>
