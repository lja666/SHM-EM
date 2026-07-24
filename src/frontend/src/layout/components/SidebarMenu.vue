<template>
  <div class="sidebar-content" :class="{ collapsed }">
    <div v-if="!collapsed" class="current-project-card">
      <span class="current-label">Current Project</span>
      <strong>{{ app.project || 'SHM-EM Public Reproduction Sample' }}</strong>
      <div class="current-status">
        <i></i>
        <span>Running - online rate pending</span>
      </div>
    </div>

    <div v-if="!collapsed" class="menu-caption">Project Catalog</div>
    <el-menu router :default-active="activeMenu" :collapse="collapsed" class="side-menu">
      <el-menu-item v-for="item in mainMenus" :key="item.path" :index="item.path">
        <el-icon><component :is="item.icon" /></el-icon>
        <template #title>{{ item.title }}</template>
      </el-menu-item>
    </el-menu>

    <div v-if="!collapsed" class="sidebar-footer">
      <span>Release</span>
      <span>© SHM-EM Team</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { useAppStore } from '../../stores/app'

defineProps<{
  routes: unknown[]
  collapsed: boolean
}>()

const route = useRoute()
const app = useAppStore()

const projectId = computed(() => Number(route.params.projectId || app.currentProjectId || 0))
const projectScopedPath = (target: string) => projectId.value ? `/projects/${projectId.value}/${target}` : '/projects'
const mainMenus = computed(() => [
  { title: 'Project Catalog', icon: 'Grid', path: '/projects', match: /^\/projects$/ },
  { title: 'Project Workspace', icon: 'DataBoard', path: projectScopedPath('overview'), match: /^\/projects\/[^/]+\/overview/ },
  { title: 'Monitored Objects', icon: 'Cpu', path: projectScopedPath('topology'), match: /^\/projects\/[^/]+\/(topology|stations|instruments|metrics|registry)/ },
  { title: 'Observation & Prediction', icon: 'TrendCharts', path: projectScopedPath('data/low-frequency'), match: /^\/projects\/[^/]+\/data/ },
  { title: 'Prediction Runs', icon: 'Coin', path: projectScopedPath('predictions'), match: /^\/projects\/[^/]+\/predictions/ },
  { title: 'Rules and Events', icon: 'Bell', path: projectScopedPath('events'), match: /^\/projects\/[^/]+\/(rules|events)/ },
  { title: 'Response and Evidence', icon: 'FolderChecked', path: projectScopedPath('response/workflows'), match: /^\/projects\/[^/]+\/(response|reports|evidence)/ },
  { title: 'Project Settings', icon: 'Setting', path: projectScopedPath('settings'), match: /^\/projects\/[^/]+\/settings|^\/system\/settings/ }
])

const activeMenu = computed(() => {
  const found = mainMenus.value.find(item => item.match.test(route.path))
  return found?.path || '/projects'
})
</script>


