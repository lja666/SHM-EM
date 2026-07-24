<template>
  <el-header class="app-navbar">
    <div class="navbar-left">
      <el-breadcrumb separator="/" class="breadcrumb">
        <el-breadcrumb-item>{{ parentTitle }}</el-breadcrumb-item>
        <el-breadcrumb-item>{{ currentTitle }}</el-breadcrumb-item>
      </el-breadcrumb>
    </div>
    <div class="navbar-right">
      <el-input v-model="searchText" class="global-search" placeholder="Global search: point / instrument / event / file" clearable>
        <template #prefix>
          <el-icon><Search /></el-icon>
        </template>
      </el-input>
      <div class="project-status-pill">
        <i></i>
        <span>Project status: {{ app.currentProjectId ? 'Running' : 'Not Selected' }}</span>
      </div>
      <button class="icon-btn" type="button" title="Refresh current page" @click="app.refreshCurrentView">
        <el-icon><Refresh /></el-icon>
      </button>
      <button class="icon-btn" type="button" title="Notification">
        <el-icon><Bell /></el-icon>
      </button>
    </div>
  </el-header>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRoute } from 'vue-router'
import { Bell, Refresh, Search } from '@element-plus/icons-vue'
import { useAppStore } from '../../stores/app'

defineEmits<{ toggle: [] }>()
defineProps<{ collapsed: boolean }>()

const route = useRoute()
const app = useAppStore()
const searchText = ref('')

const currentTitle = computed(() => String(route.meta?.title || 'Project Catalog'))
const parentTitle = computed(() => route.path === '/projects' ? 'Project Catalog' : 'Project Catalog')
</script>

