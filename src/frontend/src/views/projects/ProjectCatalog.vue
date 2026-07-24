<template>
  <section class="em-page project-directory">
    <el-alert
      v-if="errorMessage"
      type="error"
      show-icon
      :closable="false"
      :title="errorMessage"
    />
    <section class="directory-kpis">
      <article class="directory-kpi">
        <span class="kpi-icon blue"><el-icon><Grid /></el-icon></span>
        <div>
          <p>Total Projects</p>
          <strong>{{ overview.projectCount || projects.length }}</strong>
          <small>Persisted Project Records</small>
        </div>
      </article>
      <article class="directory-kpi">
        <span class="kpi-icon green"><el-icon><VideoPlay /></el-icon></span>
        <div>
          <p>Running Projects</p>
          <strong>{{ runningProjectCount }}</strong>
          <small>Active monitoring projects</small>
        </div>
      </article>
      <article class="directory-kpi">
        <span class="kpi-icon orange"><el-icon><Bell /></el-icon></span>
        <div>
          <p>Projects in Warning</p>
          <strong>{{ warningProjectCount }}</strong>
          <small>Open events exist</small>
        </div>
      </article>
      <article class="directory-kpi">
        <span class="kpi-icon purple"><el-icon><Histogram /></el-icon></span>
        <div>
          <p>Active Events</p>
          <strong>{{ total('openEventCount') }}</strong>
          <small>{{ total('eventCount') }} total</small>
        </div>
      </article>
    </section>

    <section class="filter-bar">
      <el-input v-model="keyword" class="filter-search" clearable placeholder="Search project name or location">
        <template #prefix><el-icon><Search /></el-icon></template>
      </el-input>
      <label class="filter-item">
        <span>Project Type</span>
        <el-select v-model="typeFilter" class="filter-select" placeholder="All" clearable>
          <el-option label="All" value="" />
          <el-option label="Excavation Project" value="excavation" />
          <el-option label="Bridge Project" value="bridge" />
          <el-option label="Tunnel Project" value="tunnel" />
          <el-option label="Slope Project" value="slope" />
          <el-option label="Water Conservancy Project" value="dam" />
        </el-select>
      </label>
      <label class="filter-item">
        <span>Status</span>
        <el-select v-model="statusFilter" class="filter-select" placeholder="All" clearable>
          <el-option label="All" value="" />
          <el-option label="Running" value="active" />
          <el-option label="Disabled" value="inactive" />
        </el-select>
      </label>
      <label class="filter-item">
        <span>Risk Level</span>
        <el-select v-model="riskFilter" class="filter-select" placeholder="All">
          <el-option label="All" value="all" />
          <el-option label="Warning" value="risk" />
          <el-option label="No Open Events" value="normal" />
        </el-select>
      </label>
      <label class="filter-item date-filter">
        <span>Created At</span>
        <el-date-picker
          v-model="dateRange"
          type="daterange"
          start-placeholder="Start Date"
          end-placeholder="End Date"
          range-separator="~"
          value-format="YYYY-MM-DD"
          clearable
        />
      </label>
      <el-button class="reset-button" :icon="RefreshLeft" @click="resetFilters">Reset</el-button>
    </section>

    <section class="directory-body">
      <main class="project-list-panel">
        <div class="directory-section-head">
          <div>
            <h2>Project List</h2>
            <span>Total {{ filteredProjects.length }} items</span>
          </div>
          <div class="view-tools" aria-label="View Switch">
            <button type="button" :class="{ active: projectViewMode === 'grid' }" @click="projectViewMode = 'grid'"><el-icon><Grid /></el-icon></button>
            <button type="button" :class="{ active: projectViewMode === 'compact' }" @click="projectViewMode = 'compact'"><el-icon><Document /></el-icon></button>
          </div>
        </div>
        <div :class="['project-card-grid', `mode-${projectViewMode}`]">
          <article
            v-for="project in filteredProjects"
            :key="`card-${projectKey(project)}`"
            :class="['project-card', { active: isSelectedProject(project), favorite: isFavoriteProject(project), warning: numberOf(project.openEventCount) > 0 }]"
            tabindex="0"
            @click="activateProject(project)"
            @dblclick="enter(project)"
            @keydown.enter.prevent="enter(project)"
          >
            <div class="project-card-top">
              <button type="button" class="project-card-name" @click.stop="enter(project)">
                {{ displayName(project) }}
              </button>
              <button
                type="button"
                :class="['icon-button', { active: isFavoriteProject(project) }]"
                :aria-label="isFavoriteProject(project) ? 'Unfavorite Project' : 'Favorite Project'"
                @click.stop="toggleFavoriteProject(project)"
              >
                <el-icon><Star /></el-icon>
              </button>
            </div>
            <div class="project-card-body">
              <button type="button" :class="['project-thumb', projectThumbClass(project)]" @click.stop="selectProject(project)">
                <span class="thumb-label">{{ typeName(project.infrastructureType).slice(0, 2) }}</span>
              </button>
              <div class="project-card-meta">
                <el-tag size="small" effect="light" :type="typeTagType(project.infrastructureType)">
                  {{ typeShortName(project.infrastructureType) }}
                </el-tag>
                <p class="status-row">
                  <span><i :class="['status-dot', projectStatusClass(project)]"></i>{{ projectStatusLabel(project) }}</span>
                </p>
                <p><span>Event</span><strong>{{ numberOf(project.openEventCount) }}</strong></p>
                <p><span>Updated</span><strong>{{ formatShortTime(project.latestObservationTime || project.latestEventTime) }}</strong></p>
                <p><span>Version</span><strong>{{ projectVersion(project) }}</strong></p>
              </div>
            </div>
            <div class="project-card-actions">
              <button type="button" title="Project Workspace" aria-label="Project Workspace" @click.stop="go(project, 'overview')"><el-icon><Histogram /></el-icon></button>
              <button type="button" title="Project Details" aria-label="Project Details" @click.stop="selectProject(project)"><el-icon><Document /></el-icon></button>
              <button type="button" title="Event Center" aria-label="Event Center" @click.stop="go(project, 'events')"><el-icon><Bell /></el-icon></button>
              <button type="button" title="Project Settings" aria-label="Project Settings" @click.stop="go(project, 'settings')"><el-icon><MoreFilled /></el-icon></button>
            </div>
          </article>
        </div>
      </main>

      <main class="map-panel">
        <div class="directory-section-head">
          <h2>Project Spatial Distribution</h2>
          <button type="button" class="map-fullscreen" title="Fullscreen Map" aria-label="Fullscreen Map" @click="toggleMapFullscreen"><el-icon><FullScreen /></el-icon></button>
        </div>
        <div class="map-surface" :class="{ empty: !coordinateProjects.length }">
          <div ref="mapContainer" class="real-map-layer"></div>
          <div class="map-status">
            <span>AMap</span>
            <strong>{{ mapStatusText }}</strong>
          </div>
          <div v-if="!coordinateProjects.length || mapStatus !== 'ready'" class="map-empty compact">
            <strong>{{ mapEmptyTitle }}</strong>
            <span>{{ mapEmptyDescription }}</span>
          </div>
          <div class="map-legend">
            <strong>Project Count</strong>
            <span><i class="red"></i>≥ 20</span>
            <span><i class="orange"></i>10 - 19</span>
            <span><i class="yellow"></i>5 - 9</span>
            <span><i class="green"></i>1 - 4</span>
          </div>
          <div class="map-zoom-tools" aria-label="Map Controls">
            <button type="button" title="Zoom In" aria-label="Zoom In" @click="zoomMap(1)"><el-icon><Plus /></el-icon></button>
            <button type="button" title="Zoom Out" aria-label="Zoom Out" @click="zoomMap(-1)"><el-icon><Minus /></el-icon></button>
          </div>
          <button type="button" class="map-locate" title="Fit Project Markers" aria-label="Fit Project Markers" @click="fitProjectMarkers"><el-icon><Aim /></el-icon></button>
        </div>
      </main>

    </section>

    <section class="project-table-panel">
      <div class="table-panel-head">
        <div>
          <h2>Project Inventory</h2>
        </div>
        <div class="table-actions">
          <el-button size="small" :icon="Download" @click="exportProjects">Export CSV</el-button>
        </div>
      </div>
      <el-table :data="filteredProjects" height="100%" class="project-table">
        <el-table-column label="Project Code" min-width="150" show-overflow-tooltip>
          <template #default="{ row }">{{ row.projectCode || '-' }}</template>
        </el-table-column>
        <el-table-column label="Project Name" min-width="160" show-overflow-tooltip>
          <template #default="{ row }">{{ displayName(row) }}</template>
        </el-table-column>
        <el-table-column label="Infrastructure Type" min-width="120">
          <template #default="{ row }">{{ typeName(row.infrastructureType) }}</template>
        </el-table-column>
        <el-table-column label="Location" min-width="170" show-overflow-tooltip>
          <template #default="{ row }">{{ row.locationText || 'Location pending' }}</template>
        </el-table-column>
        <el-table-column label="Monitoring Points" width="105">
          <template #default="{ row }">{{ monitoringPointCount(row) }}</template>
        </el-table-column>
        <el-table-column label="Active Events" width="105">
          <template #default="{ row }">{{ numberOf(row.openEventCount) }}</template>
        </el-table-column>
        <el-table-column label="Updated At" min-width="150">
          <template #default="{ row }">{{ formatTime(row.latestObservationTime || row.latestEventTime) }}</template>
        </el-table-column>
        <el-table-column label="Status" width="100">
          <template #default="{ row }">
            <el-tag size="small" effect="light" :type="numberOf(row.openEventCount) ? 'warning' : 'success'">
              {{ numberOf(row.openEventCount) ? 'Warning' : 'Running' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="Actions" width="108" fixed="right">
          <template #default="{ row }">
            <el-button text type="primary" @click="enter(row)">Open</el-button>
          </template>
        </el-table-column>
      </el-table>
    </section>

    <el-dialog v-model="detailVisible" title="Project Details" width="560px">
      <div v-if="selectedProject" class="detail-grid">
        <span>Project Name</span><strong>{{ displayName(selectedProject) }}</strong>
        <span>Project Code</span><strong>{{ selectedProject.projectCode || '-' }}</strong>
        <span>Project Type</span><strong>{{ typeName(selectedProject.infrastructureType) }}</strong>
        <span>Location</span><strong>{{ selectedProject.locationText || 'Location pending' }}</strong>
        <span>Field Points / Sensors</span><strong>{{ monitoringPointCount(selectedProject) }} / {{ numberOf(selectedProject.instrumentCount) }}</strong>
        <span>Event</span><strong>{{ numberOf(selectedProject.openEventCount) }} open / {{ numberOf(selectedProject.eventCount) }} total</strong>
        <span>Latest Observation</span><strong>{{ formatTime(selectedProject.latestObservationTime) }}</strong>
      </div>
      <template #footer>
        <el-button @click="detailVisible = false">Close</el-button>
        <el-button v-if="selectedProject" type="primary" @click="enter(selectedProject)">Open Project</el-button>
      </template>
    </el-dialog>
  </section>
</template>

<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { Aim, Bell, Document, Download, FullScreen, Grid, Histogram, Minus, MoreFilled, Plus, RefreshLeft, Search, Star, VideoPlay } from '@element-plus/icons-vue'
import { getProjectOverview } from '../../api/modules/project'
import { useAppStore } from '../../stores/app'
import { platformConfig } from '../../config/platform'
import type { ProjectCard, ProjectOverview } from '../../types/engineering'

const router = useRouter()
const app = useAppStore()
const loading = ref(false)
const errorMessage = ref('')
const keyword = ref('')
const typeFilter = ref('')
const statusFilter = ref('')
const riskFilter = ref<'all' | 'risk' | 'normal'>('all')
const dateRange = ref<[string, string] | ''>('')
const overview = ref<ProjectOverview>({ projects: [] })
const selectedProject = ref<ProjectCard | null>(null)
const detailVisible = ref(false)
const mapContainer = ref<HTMLDivElement | null>(null)
const mapStatus = ref<'pending' | 'ready' | 'missing-key' | 'failed'>('pending')
const projectViewMode = ref<'grid' | 'compact'>('grid')
const favoriteProjectKeys = ref<Set<string>>(new Set())
let mapInstance: unknown = null
let mapMarkers: unknown[] = []
let mapInfoWindow: unknown = null
const projects = computed(() => overview.value.projects || [])
const filteredProjects = computed(() => projects.value.filter(project => {
  const text = `${displayName(project)} ${project.projectCode || ''} ${project.locationText || ''}`.toLowerCase()
  const matchesKeyword = !keyword.value || text.includes(keyword.value.toLowerCase())
  const matchesType = !typeFilter.value || project.infrastructureType === typeFilter.value
  const status = String(project.projectStatus || project.status || '')
  const matchesStatus = !statusFilter.value || status === statusFilter.value
  const open = numberOf(project.openEventCount)
  const matchesRisk = riskFilter.value === 'all' || (riskFilter.value === 'risk' ? open > 0 : open === 0)
  const matchesDate = matchesCreatedDate(project)
  return matchesKeyword && matchesType && matchesStatus && matchesRisk && matchesDate
}))
const coordinateProjects = computed(() => filteredProjects.value.filter(hasCoordinate))
const mapStatusText = computed(() => {
  if (mapStatus.value === 'ready') return coordinateProjects.value.length ? `${coordinateProjects.value.length} projects located` : 'Base map loaded; project coordinates pending'
  if (mapStatus.value === 'missing-key') return 'Map key not configured'
  if (mapStatus.value === 'failed') return 'Map failed to load'
  return 'Initializing map'
})
const mapEmptyTitle = computed(() => {
  if (mapStatus.value === 'missing-key') return 'Map key not configured'
  if (mapStatus.value === 'failed') return 'Map failed to load'
  return 'Project coordinates pending'
})
const mapEmptyDescription = computed(() => {
  if (mapStatus.value === 'missing-key') return 'Map unavailable in this deployment.'
  if (mapStatus.value === 'failed') return 'Map service unavailable.'
  return 'No project coordinates are available.'
})
const runningProjectCount = computed(() => projects.value.filter(project => {
  const status = String(project.projectStatus || project.status || '').toLowerCase()
  return !status || status === 'active' || status === 'running'
}).length)
const warningProjectCount = computed(() => projects.value.filter(project => numberOf(project.openEventCount) > 0).length)

async function load() {
  loading.value = true
  errorMessage.value = ''
  try {
    overview.value = await getProjectOverview()
    selectedProject.value = projects.value.find(project => projectId(project) === app.currentProjectId) || projects.value[0] || null
    if (!app.currentProjectId && selectedProject.value) app.setCurrentProject(projectId(selectedProject.value), displayName(selectedProject.value))
    await nextTick()
    await initProjectMap()
    renderProjectMarkers()
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : 'Project catalog API request failed'
    overview.value = { projects: [] }
    selectedProject.value = null
  } finally {
    loading.value = false
  }
}

function resetFilters() {
  keyword.value = ''
  typeFilter.value = ''
  statusFilter.value = ''
  riskFilter.value = 'all'
  dateRange.value = ''
}

function selectProject(project: ProjectCard) {
  activateProject(project)
  selectedProject.value = project
  detailVisible.value = true
}

function activateProject(project: ProjectCard) {
  selectedProject.value = project
  const id = projectId(project)
  if (id) app.setCurrentProject(id, displayName(project))
}

function isSelectedProject(project: ProjectCard) {
  return projectKey(project) === projectKey(selectedProject.value || {})
}

function isFavoriteProject(project: ProjectCard) {
  return favoriteProjectKeys.value.has(projectKey(project))
}

function toggleFavoriteProject(project: ProjectCard) {
  const key = projectKey(project)
  const next = new Set(favoriteProjectKeys.value)
  if (next.has(key)) next.delete(key)
  else next.add(key)
  favoriteProjectKeys.value = next
}

function enter(project: ProjectCard) {
  go(project, 'overview')
}

function go(project: ProjectCard, target: string) {
  const id = projectId(project)
  if (!id) return
  app.setCurrentProject(id, displayName(project))
  router.push(`/projects/${id}/${target}`)
}

function total(field: keyof ProjectCard) {
  return projects.value.reduce((sum, project) => sum + numberOf(project[field]), 0)
}

function projectKey(project: ProjectCard) {
  return String(project.projectId || project.id || project.projectCode || project.projectName)
}

function projectId(project?: ProjectCard | null) {
  return numberOf(project?.projectId ?? project?.id)
}

function displayName(project?: ProjectCard | null) {
  return String(project?.displayName || project?.projectName || project?.projectCode || 'Unnamed Project')
}

function typeName(type?: unknown) {
  const map: Record<string, string> = { excavation: 'Excavation Project', bridge: 'Bridge Project', tunnel: 'Tunnel Project', slope: 'Slope Project', dam: 'Water Conservancy Project', building: 'Building Project', unknown: 'Unclassified Project' }
  const key = String(type || 'unknown')
  return map[key] || key
}

function typeShortName(type?: unknown) {
  const map: Record<string, string> = { excavation: 'Excavation', bridge: 'Bridge', tunnel: 'Tunnel', slope: 'Slope', dam: 'Water Conservancy', building: 'Building' }
  const key = String(type || 'unknown')
  return map[key] || typeName(type).slice(0, 4)
}

function typeTagType(type?: unknown) {
  const key = String(type || 'unknown')
  if (key === 'bridge' || key === 'building') return 'primary'
  if (key === 'dam') return 'success'
  if (key === 'tunnel') return 'info'
  if (key === 'slope') return 'warning'
  return 'success'
}

function projectThumbClass(project: ProjectCard) {
  const type = String(project.infrastructureType || 'unknown')
  return `type-${type.replace(/[^a-z0-9_-]/gi, '').toLowerCase() || 'unknown'}`
}

function projectStatusLabel(project: ProjectCard) {
  const status = String(project.projectStatus || project.status || '').toLowerCase()
  if (numberOf(project.openEventCount) > 0) return 'Alarm'
  if (status === 'inactive' || status === 'disabled' || status === 'stopped') return 'Disabled'
  return 'Running'
}

function projectStatusClass(project: ProjectCard) {
  const label = projectStatusLabel(project)
  if (label === 'Alarm') return 'warning'
  if (label === 'Disabled') return 'muted'
  return 'running'
}

function projectVersion(project: ProjectCard) {
  return String(project.version || project.softwareVersion || project.releaseVersion || '1.0.0')
}

function matchesCreatedDate(project: ProjectCard) {
  if (!dateRange.value) return true
  const createdAt = String(project.createdAt || project.startTime || project.latestObservationTime || '')
  if (!createdAt) return true
  const day = createdAt.slice(0, 10)
  return day >= dateRange.value[0] && day <= dateRange.value[1]
}

function hasCoordinate(project: ProjectCard) {
  return Number.isFinite(Number(project.longitude)) && Number.isFinite(Number(project.latitude))
}

function numberOf(value: unknown) {
  const number = Number(value)
  return Number.isFinite(number) ? number : 0
}

function monitoringPointCount(project?: ProjectCard | null) {
  return numberOf(project?.siteCount ?? project?.stationCount)
}

function formatTime(value?: unknown) {
  if (!value) return '-'
  return String(value).replace('T', ' ').slice(0, 19)
}

function formatShortTime(value?: unknown) {
  const text = formatTime(value)
  return text === '-' ? '-' : text.slice(5, 16)
}

async function initProjectMap() {
  if (!platformConfig.amapKey) {
    mapStatus.value = 'missing-key'
    return
  }
  if (!mapContainer.value) return
  try {
    await loadAmapScript()
    const AMap = (window as unknown as { AMap?: any }).AMap
    if (!AMap) throw new Error('AMap SDK unavailable')
    if (!mapInstance) {
      mapInstance = new AMap.Map(mapContainer.value, {
        zoom: 4,
        center: [104.1954, 35.8617],
        viewMode: '2D',
        mapStyle: 'amap://styles/normal'
      })
    }
    mapStatus.value = 'ready'
  } catch {
    mapStatus.value = 'failed'
  }
}

function loadAmapScript() {
  const win = window as unknown as { AMap?: unknown; _AMapSecurityConfig?: Record<string, string> }
  if (win.AMap) return Promise.resolve()
  if (platformConfig.amapSecurityJsCode) {
    win._AMapSecurityConfig = { securityJsCode: platformConfig.amapSecurityJsCode }
  }
  const existed = document.getElementById('amap-sdk')
  if (existed) {
    return new Promise<void>((resolve, reject) => {
      existed.addEventListener('load', () => resolve(), { once: true })
      existed.addEventListener('error', () => reject(new Error('AMap SDK load failed')), { once: true })
    })
  }
  return new Promise<void>((resolve, reject) => {
    const script = document.createElement('script')
    script.id = 'amap-sdk'
    script.src = `https://webapi.amap.com/maps?v=2.0&key=${encodeURIComponent(platformConfig.amapKey)}`
    script.async = true
    script.onload = () => resolve()
    script.onerror = () => reject(new Error('AMap SDK load failed'))
    document.head.appendChild(script)
  })
}

function renderProjectMarkers() {
  const AMap = (window as unknown as { AMap?: any }).AMap
  const map = mapInstance as any
  if (!AMap || !map) return
  map.remove(mapMarkers)
  if (!mapInfoWindow) {
    mapInfoWindow = new AMap.InfoWindow({
      isCustom: true,
      offset: new AMap.Pixel(0, -30)
    })
  }
  mapMarkers = coordinateProjects.value.map(project => {
    const marker = new AMap.Marker({
      position: [Number(project.longitude), Number(project.latitude)],
      title: displayName(project),
      label: {
        content: displayName(project),
        direction: 'top'
      }
    })
    marker.on('mouseover', () => {
      const content = createMapProjectPopup(project)
      ;(mapInfoWindow as any).setContent(content)
      ;(mapInfoWindow as any).open(map, marker.getPosition())
    })
    marker.on('click', () => enter(project))
    return marker
  })
  if (mapMarkers.length) {
    map.add(mapMarkers)
    map.setFitView(mapMarkers, false, [70, 70, 70, 70], 12)
  } else {
    map.setZoomAndCenter(4, [104.1954, 35.8617])
  }
}

function zoomMap(delta: number) {
  const map = mapInstance as { getZoom?: () => number; setZoom?: (zoom: number) => void } | null
  const zoom = map?.getZoom?.()
  if (typeof zoom === 'number') map?.setZoom?.(Math.max(3, Math.min(20, zoom + delta)))
}

function fitProjectMarkers() {
  const map = mapInstance as { setFitView?: (markers: unknown[], immediate?: boolean, padding?: number[], maxZoom?: number) => void; setZoomAndCenter?: (zoom: number, center: number[]) => void } | null
  if (mapMarkers.length) map?.setFitView?.(mapMarkers, false, [70, 70, 70, 70], 12)
  else map?.setZoomAndCenter?.(4, [104.1954, 35.8617])
}

async function toggleMapFullscreen() {
  const surface = mapContainer.value?.parentElement
  if (!surface) return
  if (document.fullscreenElement) await document.exitFullscreen()
  else await surface.requestFullscreen()
  window.setTimeout(() => (mapInstance as { resize?: () => void } | null)?.resize?.(), 50)
}

function exportProjects() {
  const header = ['Project Code', 'Project Name', 'Infrastructure Type', 'Location', 'Monitoring Points', 'Active Events', 'Updated At', 'Status']
  const rows = filteredProjects.value.map(project => [
    project.projectCode || '',
    displayName(project),
    typeName(project.infrastructureType),
    project.locationText || '',
    monitoringPointCount(project),
    numberOf(project.openEventCount),
    formatTime(project.latestObservationTime || project.latestEventTime),
    projectStatusLabel(project)
  ])
  const csv = [header, ...rows].map(row => row.map(csvCell).join(',')).join('\r\n')
  const url = URL.createObjectURL(new Blob(['\uFEFF', csv], { type: 'text/csv;charset=utf-8' }))
  const link = document.createElement('a')
  link.href = url
  link.download = 'shm-em-project-inventory.csv'
  link.click()
  URL.revokeObjectURL(url)
}

function csvCell(value: unknown) {
  return `"${String(value ?? '').replace(/"/g, '""')}"`
}

function createMapProjectPopup(project: ProjectCard) {
  const popup = document.createElement('div')
  popup.className = 'amap-project-popup'
  popup.innerHTML = `
    <div class="popup-head">
      <div>
        <strong>${escapeHtml(displayName(project))}</strong>
        <span>${escapeHtml(project.projectCode || 'Project code pending')}</span>
      </div>
      <em>${numberOf(project.openEventCount) ? 'Warning' : 'Running'}</em>
      <button type="button" class="popup-close" data-action="close" aria-label="Close Popup">×</button>
    </div>
    <div class="popup-meta">
      <dl><dt>Project Type</dt><dd>${escapeHtml(typeName(project.infrastructureType))}</dd></dl>
      <dl><dt>Project Status</dt><dd>${escapeHtml(String(project.projectStatus || project.status || 'active'))}</dd></dl>
      <dl><dt>Spatial Location</dt><dd>${escapeHtml(project.locationText || 'Location pending')}</dd></dl>
      <dl><dt>Coordinates</dt><dd>${Number(project.longitude).toFixed(6)}, ${Number(project.latitude).toFixed(6)}</dd></dl>
      <dl><dt>Latest Observation</dt><dd>${escapeHtml(formatTime(project.latestObservationTime))}</dd></dl>
    </div>
    <div class="popup-kpis">
      <button type="button" data-action="stations"><span>Point</span><strong>${monitoringPointCount(project)}</strong></button>
      <button type="button" data-action="instruments"><span>Sensors</span><strong>${numberOf(project.instrumentCount)}</strong></button>
      <button type="button" data-action="events"><span>Open</span><strong>${numberOf(project.openEventCount)}</strong></button>
      <button type="button" data-action="events"><span>Total Events</span><strong>${numberOf(project.eventCount)}</strong></button>
    </div>
    <div class="popup-actions">
      <button type="button" data-action="enter">Open Project</button>
      <button type="button" data-action="data">Observation Data</button>
    </div>
  `
  popup.querySelectorAll<HTMLButtonElement>('[data-action]').forEach(button => {
    button.addEventListener('click', event => {
      event.stopPropagation()
      const action = button.dataset.action
      if (action === 'close') (mapInfoWindow as any)?.close?.()
      else if (action === 'detail') selectProject(project)
      else if (action === 'stations' || action === 'instruments') go(project, 'topology')
      else if (action === 'events') go(project, 'events')
      else if (action === 'data') go(project, 'data/low-frequency')
      else enter(project)
    })
  })
  return popup
}

function escapeHtml(value: unknown) {
  return String(value ?? '').replace(/[&<>"']/g, char => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[char] || char))
}

watch(coordinateProjects, () => {
  renderProjectMarkers()
})

onMounted(async () => {
  await load()
  await initProjectMap()
  renderProjectMarkers()
})

onBeforeUnmount(() => {
  const map = mapInstance as { destroy?: () => void } | null
  map?.destroy?.()
  mapInstance = null
  mapMarkers = []
  mapInfoWindow = null
})
</script>

<style scoped>
.project-directory {
  gap: 10px;
  min-height: calc(var(--shm-scaled-vh) - 112px);
}
.directory-kpis {
  display: grid;
  grid-template-columns: repeat(4, minmax(128px, 1fr));
  gap: 12px;
  min-width: 0;
}
.directory-kpi {
  display: flex;
  align-items: center;
  gap: clamp(8px, .9vw, 14px);
  min-width: 0;
  min-height: 76px;
  padding: clamp(10px, .9vw, 14px) clamp(10px, 1vw, 16px);
  border: 1px solid var(--shm-border);
  border-radius: 12px;
  background: #fff;
  box-shadow: var(--shm-card-shadow);
}
.directory-kpi > div {
  min-width: 0;
}
.kpi-icon {
  display: grid;
  place-items: center;
  flex: 0 0 auto;
  width: clamp(32px, 2.8vw, 42px);
  height: clamp(32px, 2.8vw, 42px);
  border-radius: 12px;
  color: #fff;
  font-size: clamp(16px, 1.4vw, 21px);
}
.kpi-icon.blue { background: linear-gradient(135deg, #2f6bff, #165dff); }
.kpi-icon.green { background: linear-gradient(135deg, #2ccf74, #16a34a); }
.kpi-icon.orange { background: linear-gradient(135deg, #ff9a2e, #f97316); }
.kpi-icon.purple { background: linear-gradient(135deg, #8b5cf6, #5b5cf6); }
.directory-kpi p,
.directory-kpi strong,
.directory-kpi small {
  display: block;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.directory-kpi p { margin: 0 0 5px; color: var(--shm-text-main); font-size: 13px; font-weight: 650; }
.directory-kpi strong { color: var(--shm-text-title); font-size: clamp(18px, 1.55vw, 24px); line-height: 1; font-weight: 800; }
.directory-kpi small { margin-top: 5px; color: var(--shm-text-secondary); font-size: 12px; }
.filter-bar {
  display: grid;
  grid-template-columns: minmax(150px, 1.25fr) repeat(4, minmax(116px, 1fr)) 84px;
  gap: 8px;
  align-items: center;
  min-width: 0;
  width: 100%;
  padding: 10px;
  border: 1px solid var(--shm-border);
  border-radius: 12px;
  background: #fff;
  box-shadow: var(--shm-card-shadow);
}
.filter-search {
  display: grid;
  grid-template-rows: 14px minmax(34px, auto);
  gap: 4px;
  align-items: end;
  width: 100%;
  min-width: 0;
}
.filter-search::before {
  content: "";
  display: block;
  height: 14px;
}
.filter-item {
  display: grid;
  grid-template-columns: auto minmax(72px, 1fr);
  align-items: center;
  gap: 6px;
  width: 100%;
  min-width: 0;
  overflow: hidden;
}
.filter-item > span {
  flex: 0 0 auto;
  color: var(--shm-text-main);
  font-size: 12px;
  font-weight: 650;
  white-space: nowrap;
}
.filter-select {
  width: 100%;
  min-width: 0;
}
.date-filter :deep(.el-date-editor) {
  width: 100%;
  min-width: 0;
}
.filter-bar :deep(.el-input),
.filter-bar :deep(.el-select),
.filter-bar :deep(.el-date-editor),
.filter-bar :deep(.el-input__wrapper),
.filter-bar :deep(.el-select__wrapper) {
  width: 100%;
  min-width: 0;
  box-sizing: border-box;
}
.filter-bar :deep(.el-input__wrapper),
.filter-bar :deep(.el-select__wrapper),
.filter-bar :deep(.el-date-editor.el-input__wrapper) {
  min-height: 34px;
}
.filter-bar :deep(.el-range-input) {
  min-width: 0;
}
.reset-button {
  width: 84px;
  min-width: 0;
}
.directory-body {
  display: grid;
  grid-template-columns: minmax(560px, 1.55fr) minmax(360px, .85fr);
  gap: 12px;
  align-items: stretch;
  min-width: 0;
}
.project-list-panel,
.map-panel {
  min-width: 0;
  padding: 12px;
  border: 1px solid var(--shm-border);
  border-radius: 12px;
  background: #fff;
  box-shadow: var(--shm-card-shadow);
}
.project-list-panel {
  display: grid;
  grid-template-rows: auto minmax(0, 1fr);
  gap: 10px;
}
.directory-section-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  min-height: 26px;
}
.directory-section-head h2 {
  margin: 0;
  color: var(--shm-text-title);
  font-size: 15px;
  font-weight: 760;
}
.directory-section-head > div:first-child {
  display: flex;
  align-items: baseline;
  gap: 8px;
  min-width: 0;
}
.directory-section-head span {
  color: var(--shm-text-secondary);
  font-size: 12px;
  font-weight: 650;
}
.view-tools {
  display: inline-flex;
  gap: 6px;
}
.view-tools button,
.icon-button,
.project-card-actions button,
.map-fullscreen,
.map-zoom-tools button,
.map-locate {
  display: inline-grid;
  place-items: center;
  border: 1px solid var(--shm-border);
  border-radius: 7px;
  background: #fff;
  color: #5b6b82;
  cursor: pointer;
}
.view-tools button {
  width: 26px;
  height: 26px;
  border: 0;
}
.view-tools button.active {
  color: var(--shm-primary);
  background: #eaf2ff;
}
.project-card-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(162px, 1fr));
  grid-auto-rows: 160px;
  align-items: start;
  gap: 10px;
  min-width: 0;
  max-height: 332px;
  overflow-y: auto;
  padding-right: 2px;
}
.project-card {
  position: relative;
  display: block;
  min-width: 0;
  width: 100%;
  height: 160px;
  min-height: 160px;
  padding: 10px 10px 32px;
  border: 1px solid #e3eaf3;
  border-radius: 8px;
  background:
    linear-gradient(180deg, #fff, #fbfdff 100%),
    #fff;
  box-shadow: 0 1px 2px rgba(15, 23, 42, .025), 0 8px 22px rgba(15, 23, 42, .045);
  cursor: pointer;
  transition: border-color .18s ease, box-shadow .18s ease, transform .18s ease, background .18s ease;
}
.project-card:hover,
.project-card:focus-visible {
  border-color: rgba(47, 107, 255, .42);
  box-shadow: 0 10px 22px rgba(15, 23, 42, .08);
  transform: translateY(-1px);
  outline: none;
}
.project-card.active {
  border-color: var(--shm-primary);
  box-shadow: 0 0 0 2px rgba(47, 107, 255, .12), 0 14px 30px rgba(47, 107, 255, .12);
}
.project-card.warning {
  border-color: #fde7c7;
  background: linear-gradient(180deg, #fffaf2, #fff 46%);
}
.project-card.favorite .project-card-name::after {
  content: "";
}
.project-card-top {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 22px;
  gap: 6px;
  align-items: center;
  height: 22px;
}
.project-card-name {
  min-width: 0;
  padding: 0;
  border: 0;
  background: transparent;
  color: #1e293b;
  font-size: 13px;
  font-weight: 780;
  line-height: 22px;
  text-align: left;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  cursor: pointer;
}
.icon-button {
  width: 22px;
  height: 22px;
  border: 0;
  color: #98a6ba;
  font-size: 15px;
  background: transparent;
}
.icon-button:hover,
.icon-button.active {
  color: #f59e0b;
  background: #fff7ed;
}
.project-card-body {
  display: grid;
  grid-template-columns: 58px minmax(0, 1fr);
  gap: 10px;
  align-items: start;
  min-width: 0;
  height: 86px;
  margin-top: 8px;
}
.project-thumb {
  position: relative;
  width: 58px;
  height: 48px;
  align-self: start;
  margin-top: 10px;
  overflow: hidden;
  border: 0;
  border-radius: 5px;
  background:
    linear-gradient(180deg, rgba(255,255,255,.42), transparent 38%),
    linear-gradient(160deg, #9ccfff, #2872bd 54%, #1c4f87);
  color: #fff;
  cursor: pointer;
  box-shadow: inset 0 -18px 24px rgba(15, 23, 42, .24), 0 6px 12px rgba(30, 64, 105, .16);
}
.project-thumb::before,
.project-thumb::after {
  position: absolute;
  content: "";
  z-index: 1;
  pointer-events: none;
}
.project-thumb::after {
  inset: auto 0 0;
  height: 15px;
  background: linear-gradient(180deg, rgba(255,255,255,.16), rgba(15, 23, 42, .22));
}
.project-thumb::before {
  left: 7px;
  right: 7px;
  top: 21px;
  height: 2px;
  border-radius: 999px;
  background: rgba(255,255,255,.86);
  box-shadow:
    0 6px 0 rgba(255,255,255,.5),
    0 -6px 0 rgba(255,255,255,.35);
}
.project-thumb .thumb-label {
  position: absolute;
  left: 6px;
  bottom: 5px;
  z-index: 2;
  font-size: 10px;
  font-weight: 800;
  letter-spacing: .5px;
  text-shadow: 0 1px 3px rgba(0,0,0,.24);
}
.project-thumb:hover {
  filter: saturate(1.08) contrast(1.04);
}
.project-thumb.type-excavation {
  background:
    linear-gradient(180deg, #acd9ff 0 38%, #d8c3a1 39% 100%);
}
.project-thumb.type-excavation::before {
  left: 8px;
  right: 8px;
  top: 18px;
  height: 18px;
  border: 2px solid rgba(92, 64, 39, .5);
  border-top: 0;
  border-radius: 0 0 3px 3px;
  background: linear-gradient(135deg, rgba(120, 86, 54, .55), rgba(210, 174, 120, .58));
  box-shadow: inset 0 5px 0 rgba(255,255,255,.16);
}
.project-thumb.type-bridge {
  background:
    linear-gradient(180deg, #b9ddff 0 54%, #6fb3d4 55% 100%);
}
.project-thumb.type-bridge::before {
  left: 7px;
  right: 7px;
  top: 25px;
  height: 2px;
  background: #fff;
  box-shadow:
    10px -15px 0 -1px rgba(255,255,255,.9),
    31px -15px 0 -1px rgba(255,255,255,.8),
    10px -8px 0 -1px rgba(255,255,255,.62),
    31px -8px 0 -1px rgba(255,255,255,.55);
}
.project-thumb.type-tunnel {
  background: linear-gradient(135deg, #d5dae4, #5f6c7e);
}
.project-thumb.type-tunnel::before {
  left: 13px;
  right: 13px;
  top: 10px;
  height: 28px;
  border-radius: 22px 22px 4px 4px;
  background: radial-gradient(circle at 50% 72%, #1f2937 0 28%, #6b7280 29% 54%, #e5e7eb 55%);
  box-shadow: none;
}
.project-thumb.type-dam {
  background: linear-gradient(180deg, #d7f0ff 0 44%, #7ab5c9 45% 100%);
}
.project-thumb.type-dam::before {
  left: 9px;
  right: 8px;
  top: 16px;
  height: 23px;
  transform: skewX(-13deg);
  border-radius: 2px;
  background: linear-gradient(90deg, #d8dee7, #8b98a7);
  box-shadow: inset -7px 0 0 rgba(255,255,255,.25);
}
.project-thumb.type-slope {
  background: linear-gradient(180deg, #d9f6c7 0 36%, #7fb35b 37% 100%);
}
.project-thumb.type-slope::before {
  left: 4px;
  right: 2px;
  top: 17px;
  height: 28px;
  clip-path: polygon(0 100%, 100% 30%, 100% 100%);
  background: linear-gradient(135deg, #7aa34d, #425f2a);
  box-shadow: none;
}
.project-thumb.type-building {
  background: linear-gradient(135deg, #d8e8fb, #5f7fa9);
}
.project-thumb.type-building::before {
  left: 10px;
  top: 9px;
  width: 34px;
  height: 31px;
  border-radius: 2px;
  background:
    linear-gradient(90deg, rgba(255,255,255,.78) 1px, transparent 1px),
    linear-gradient(0deg, rgba(255,255,255,.78) 1px, transparent 1px),
    rgba(255,255,255,.25);
  background-size: 8px 8px;
  box-shadow: none;
}
.project-card-meta {
  display: grid;
  align-content: start;
  gap: 3px;
  min-width: 0;
}
.project-card-meta p {
  display: grid;
  grid-template-columns: 26px minmax(0, 1fr);
  align-items: center;
  gap: 6px;
  min-width: 0;
  margin: 0;
  color: #64748b;
  font-size: 11px;
  line-height: 13px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.project-card-meta p span {
  min-width: 0;
  color: #64748b;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.project-card-meta .status-row {
  display: block;
}
.project-card-meta .status-row span {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  color: #334155;
}
.project-card-meta :deep(.el-tag) {
  justify-self: start;
  height: 19px;
  max-width: 70px;
  padding: 0 8px;
  border-radius: 5px;
  font-size: 11px;
  font-weight: 700;
  line-height: 17px;
}
.project-card-meta strong {
  min-width: 0;
  color: #1e293b;
  font-weight: 780;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.status-dot {
  flex: 0 0 auto;
  width: 6px;
  height: 6px;
  border-radius: 999px;
  background: var(--shm-success);
}
.status-dot.warning { background: var(--shm-orange); }
.status-dot.muted { background: #94a3b8; }
.project-card-actions {
  position: absolute;
  left: 0;
  right: 0;
  bottom: 0;
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  height: 32px;
  margin: 0;
  border-top: 1px solid #edf2f7;
  background: linear-gradient(180deg, #fbfdff, #f7faff);
  border-radius: 0 0 8px 8px;
  overflow: hidden;
}
.project-card-actions button {
  height: 32px;
  border: 0;
  border-right: 1px solid #edf2f7;
  border-radius: 0;
  background: transparent;
  color: #4f6076;
  font-size: 14px;
  transition: background .16s ease, color .16s ease;
}
.project-card-actions button:hover {
  background: #edf5ff;
  color: var(--shm-primary);
}
.project-card-actions button:last-child {
  border-right: 0;
}
.project-card-grid.mode-compact {
  grid-template-columns: repeat(4, minmax(162px, 1fr));
}
.project-card-grid.mode-compact .project-card {
  height: 160px;
  min-height: 160px;
}
.map-panel {
  display: grid;
  grid-template-rows: auto minmax(0, 1fr);
  gap: 10px;
}
.panel-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 10px;
  margin-bottom: 10px;
}
.panel-head.compact {
  margin-bottom: 12px;
}
.panel-head h2 {
  margin: 0;
  color: var(--shm-text-title);
  font-size: 16px;
  font-weight: 750;
}
.panel-head p {
  margin: 5px 0 0;
  color: var(--shm-text-secondary);
  font-size: 12px;
  line-height: 1.45;
}
.map-surface {
  position: relative;
  min-height: 315px;
  overflow: hidden;
  border: 1px solid var(--shm-border);
  border-radius: 12px;
  background:
    radial-gradient(circle at 70% 45%, rgba(221, 245, 255, .75), transparent 34%),
    linear-gradient(135deg, #f9fbff, #eef7fb 56%, #e7f2fb);
}
.map-surface::after {
  display: none;
}
.real-map-layer {
  position: absolute;
  inset: 0;
  z-index: 0;
  background:
    radial-gradient(circle at 24% 22%, rgba(68, 190, 92, .18), transparent 9%),
    radial-gradient(circle at 48% 42%, rgba(68, 190, 92, .18), transparent 8%),
    radial-gradient(circle at 73% 24%, rgba(255, 180, 44, .2), transparent 8%),
    radial-gradient(circle at 75% 52%, rgba(239, 68, 68, .18), transparent 8%),
    linear-gradient(90deg, rgba(148,163,184,.1) 1px, transparent 1px),
    linear-gradient(0deg, rgba(148,163,184,.1) 1px, transparent 1px),
    transparent;
  background-size: auto, auto, auto, auto, 34px 34px, 34px 34px;
}
.map-fullscreen {
  grid-auto-flow: column;
  gap: 5px;
  height: 28px;
  padding: 0 9px;
  color: #5b6b82;
  font-size: 12px;
}
.map-status {
  position: absolute;
  left: 12px;
  top: 12px;
  z-index: 3;
  display: flex;
  align-items: center;
  gap: 8px;
  max-width: calc(100% - 28px);
  padding: 8px 11px;
  border: 1px solid rgba(226, 232, 240, .92);
  border-radius: 999px;
  background: rgba(255,255,255,.92);
  box-shadow: 0 8px 20px rgba(15,23,42,.08);
  color: var(--shm-text-secondary);
  font-size: 12px;
}
.map-status span {
  color: var(--shm-primary);
  font-weight: 750;
}
.map-status strong {
  overflow: hidden;
  color: var(--shm-text-main);
  font-weight: 650;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.project-pin {
  position: absolute;
  z-index: 2;
  transform: translate(-50%, -50%);
  display: grid;
  place-items: center;
  width: 34px;
  height: 34px;
  border: 3px solid #fff;
  border-radius: 999px;
  background: var(--shm-success);
  color: #fff;
  font-size: 13px;
  font-weight: 800;
  box-shadow: 0 12px 24px rgba(15, 23, 42, .18);
  cursor: pointer;
}
.project-pin.warning {
  background: var(--shm-orange);
}
.map-empty {
  position: absolute;
  inset: 0;
  z-index: 2;
  display: grid;
  place-content: center;
  justify-items: center;
  gap: 12px;
  max-width: 620px;
  margin: auto;
  padding: 24px;
  text-align: center;
  pointer-events: none;
}
.map-empty.compact {
  max-width: 360px;
  padding: 18px;
}
.map-empty.compact strong {
  font-size: 16px;
}
.map-empty.compact span {
  font-size: 12px;
}
.map-legend {
  position: absolute;
  left: 12px;
  bottom: 16px;
  z-index: 3;
  display: grid;
  gap: 6px;
  min-width: 94px;
  padding: 10px 12px;
  border: 1px solid rgba(226, 232, 240, .9);
  border-radius: 8px;
  background: rgba(255,255,255,.9);
  box-shadow: 0 10px 24px rgba(15, 23, 42, .08);
}
.map-legend strong,
.map-legend span {
  display: flex;
  align-items: center;
  gap: 7px;
  color: #526173;
  font-size: 11px;
  white-space: nowrap;
}
.map-legend strong {
  color: #64748b;
  font-weight: 760;
}
.map-legend i {
  width: 8px;
  height: 8px;
  border-radius: 999px;
}
.map-legend i.red { background: #ef4444; }
.map-legend i.orange { background: #f97316; }
.map-legend i.yellow { background: #facc15; }
.map-legend i.green { background: #22c55e; }
.map-zoom-tools {
  position: absolute;
  right: 14px;
  bottom: 58px;
  z-index: 3;
  display: grid;
  overflow: hidden;
  border: 1px solid rgba(226, 232, 240, .9);
  border-radius: 8px;
  background: rgba(255,255,255,.94);
  box-shadow: 0 10px 24px rgba(15, 23, 42, .08);
}
.map-zoom-tools button {
  width: 32px;
  height: 32px;
  border: 0;
  border-bottom: 1px solid #e2e8f0;
  border-radius: 0;
}
.map-zoom-tools button:last-child {
  border-bottom: 0;
}
.map-locate {
  position: absolute;
  right: 14px;
  bottom: 16px;
  z-index: 3;
  width: 32px;
  height: 32px;
  box-shadow: 0 10px 24px rgba(15, 23, 42, .08);
}
.map-empty > * {
  pointer-events: auto;
}
.map-empty strong {
  color: var(--shm-text-title);
  font-size: 20px;
}
.map-empty span {
  color: var(--shm-text-secondary);
  line-height: 1.7;
}
.map-project-list {
  display: grid;
  gap: 10px;
  width: min(720px, 100%);
  margin-top: 8px;
}
.map-project-unit {
  display: grid;
  gap: 10px;
  padding: 12px;
  border: 1px solid rgba(226, 232, 240, .92);
  border-radius: 12px;
  background: rgba(255,255,255,.9);
  box-shadow: 0 8px 22px rgba(15, 23, 42, .045);
}
.unit-main {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 14px;
  width: 100%;
  min-width: 0;
  padding: 0;
  border: 0;
  background: transparent;
  color: var(--shm-text-main);
  text-align: left;
  cursor: pointer;
}
.unit-main > span {
  min-width: 0;
}
.unit-main strong,
.unit-main small,
.unit-kpis span,
.unit-kpis strong {
  display: block;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.unit-main strong {
  color: var(--shm-text-title);
  font-size: 15px;
  font-weight: 760;
}
.unit-main small {
  margin-top: 4px;
  color: var(--shm-text-secondary);
}
.unit-kpis {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 0;
  padding: 9px 0;
  border-top: 1px solid var(--shm-border);
  border-bottom: 1px solid var(--shm-border);
}
.unit-kpis div {
  min-width: 0;
  padding: 0 10px;
  border-right: 1px solid var(--shm-border);
}
.unit-kpis div:last-child {
  border-right: 0;
}
.unit-kpis span {
  color: var(--shm-text-secondary);
  font-size: 12px;
}
.unit-kpis strong {
  margin-top: 4px;
  color: var(--shm-text-title);
  font-size: 15px;
}
.unit-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}
:global(.amap-project-popup) {
  width: 360px;
  padding: 14px;
  border: 1px solid rgba(226, 232, 240, .94);
  border-radius: 12px;
  background: rgba(255, 255, 255, .96);
  box-shadow: 0 16px 38px rgba(15, 23, 42, .16);
  color: #334155;
  font-family: inherit;
}
:global(.amap-project-popup .popup-head) {
  position: relative;
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 12px;
  padding-right: 28px;
}
:global(.amap-project-popup .popup-head div) {
  min-width: 0;
}
:global(.amap-project-popup .popup-head strong),
:global(.amap-project-popup .popup-head span) {
  display: block;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
:global(.amap-project-popup .popup-head strong) {
  color: #0f172a;
  font-size: 15px;
  font-weight: 760;
}
:global(.amap-project-popup .popup-head span) {
  margin-top: 5px;
  color: #64748b;
  font-size: 12px;
}
:global(.amap-project-popup .popup-head em) {
  flex: 0 0 auto;
  padding: 3px 8px;
  border-radius: 999px;
  background: #fff7ed;
  color: #ea580c;
  font-size: 12px;
  font-style: normal;
  font-weight: 700;
}
:global(.amap-project-popup .popup-close) {
  position: absolute;
  right: 0;
  top: -2px;
  display: grid;
  place-items: center;
  width: 24px;
  height: 24px;
  border: 1px solid #dbe5f1;
  border-radius: 7px;
  background: #fff;
  color: #64748b;
  font-size: 18px;
  line-height: 1;
  cursor: pointer;
}
:global(.amap-project-popup .popup-close:hover) {
  border-color: #fecaca;
  background: #fff5f5;
  color: #ef4444;
}
:global(.amap-project-popup .popup-meta) {
  display: grid;
  gap: 7px;
  margin-bottom: 12px;
  padding: 10px;
  border: 1px solid #eef2f7;
  border-radius: 9px;
  background: #f8fafc;
}
:global(.amap-project-popup .popup-meta dl) {
  display: grid;
  grid-template-columns: 68px minmax(0, 1fr);
  gap: 8px;
  margin: 0;
  min-width: 0;
}
:global(.amap-project-popup .popup-meta dt),
:global(.amap-project-popup .popup-meta dd) {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
:global(.amap-project-popup .popup-meta dt) {
  color: #64748b;
  font-size: 12px;
}
:global(.amap-project-popup .popup-meta dd) {
  margin: 0;
  color: #1e293b;
  font-size: 12px;
  font-weight: 650;
}
:global(.amap-project-popup .popup-kpis) {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  border-top: 1px solid #e2e8f0;
  border-bottom: 1px solid #e2e8f0;
}
:global(.amap-project-popup .popup-kpis button) {
  min-width: 0;
  padding: 9px 6px;
  border: 0;
  border-right: 1px solid #e2e8f0;
  background: transparent;
  color: inherit;
  text-align: center;
  cursor: pointer;
}
:global(.amap-project-popup .popup-kpis button:last-child) {
  border-right: 0;
}
:global(.amap-project-popup .popup-kpis button:hover) {
  background: #f8fafc;
}
:global(.amap-project-popup .popup-kpis span),
:global(.amap-project-popup .popup-kpis strong) {
  display: block;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
:global(.amap-project-popup .popup-kpis span) {
  color: #64748b;
  font-size: 12px;
}
:global(.amap-project-popup .popup-kpis strong) {
  margin-top: 5px;
  color: #0f172a;
  font-size: 14px;
  font-weight: 780;
}
:global(.amap-project-popup .popup-actions) {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  margin-top: 12px;
}
:global(.amap-project-popup .popup-actions button) {
  height: 30px;
  padding: 0 12px;
  border: 1px solid #dbe5f1;
  border-radius: 7px;
  background: #fff;
  color: #334155;
  font-size: 12px;
  cursor: pointer;
}
:global(.amap-project-popup .popup-actions button:first-child) {
  border-color: #165dff;
  background: #165dff;
  color: #fff;
}
.project-table-panel {
  display: grid;
  flex: 1 1 360px;
  grid-template-rows: auto minmax(320px, 1fr);
  gap: 10px;
  min-width: 0;
  min-height: 360px;
  width: 100%;
  padding: 12px;
  border: 1px solid var(--shm-border);
  border-radius: 12px;
  background: #fff;
  box-shadow: var(--shm-card-shadow);
}
.table-panel-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  min-width: 0;
}
.table-panel-head h2 {
  margin: 0;
  color: var(--shm-text-title);
  font-size: 15px;
  font-weight: 760;
}
.table-panel-head span {
  display: block;
  margin-top: 4px;
  color: var(--shm-text-secondary);
  font-size: 12px;
}
.table-actions {
  display: inline-flex;
  flex: 0 0 auto;
  gap: 8px;
}
.project-table {
  min-height: 320px;
  width: 100%;
  height: 100%;
}
.type-stat-table {
  min-width: 0;
  overflow-x: auto;
}
.type-stat-table table {
  width: 100%;
  min-width: 520px;
  border-collapse: collapse;
  table-layout: fixed;
}
.type-stat-table th,
.type-stat-table td {
  height: 38px;
  padding: 0 10px;
  border-bottom: 1px solid var(--shm-border);
  color: var(--shm-text-main);
  font-size: 13px;
  text-align: right;
  white-space: nowrap;
}
.type-stat-table th {
  height: 34px;
  background: #f8fafc;
  color: var(--shm-text-secondary);
  font-size: 12px;
  font-weight: 700;
}
.type-stat-table th:first-child,
.type-stat-table td:first-child {
  text-align: left;
}
.type-stat-table tbody tr:last-child td {
  border-bottom: 0;
}
.type-label {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  max-width: 100%;
  min-width: 0;
}
.type-label i {
  flex: 0 0 auto;
  width: 9px;
  height: 9px;
  border-radius: 999px;
  background: var(--shm-primary);
}
.type-label i.bridge { background: var(--shm-success); }
.type-label i.tunnel { background: var(--shm-purple); }
.type-label i.slope { background: var(--shm-info); }
.type-label i.dam { background: var(--shm-orange); }
.type-label i.unknown { background: var(--shm-gray); }
.activity-list { display: grid; gap: 10px; }
.activity-item {
  display: grid;
  grid-template-columns: 30px minmax(0, 1fr) auto;
  gap: 9px;
  align-items: start;
}
.activity-dot {
  display: grid;
  place-items: center;
  width: 28px;
  height: 28px;
  border-radius: 999px;
  background: #eaf2ff;
  color: var(--shm-primary);
}
.activity-dot.warning {
  background: #fff7ed;
  color: var(--shm-orange);
}
.activity-item strong {
  display: block;
  color: var(--shm-text-main);
  font-size: 13px;
}
.activity-item p {
  margin: 4px 0 0;
  color: var(--shm-text-secondary);
  font-size: 12px;
  line-height: 1.45;
}
.activity-item time {
  color: var(--shm-text-muted);
  font-size: 12px;
  white-space: nowrap;
}
.detail-grid {
  display: grid;
  grid-template-columns: 96px minmax(0, 1fr);
  gap: 12px 14px;
}
.detail-grid span { color: var(--shm-text-secondary); }
.detail-grid strong { color: var(--shm-text-main); word-break: break-word; }
@media (max-width: 1600px) {
  .directory-kpis {
    grid-template-columns: repeat(4, minmax(120px, 1fr)) !important;
    gap: 10px !important;
  }
  .directory-body {
    grid-template-columns: minmax(520px, 1.45fr) minmax(350px, .9fr) !important;
    gap: 10px !important;
  }
  .project-card-grid {
    grid-template-columns: repeat(4, minmax(162px, 1fr));
  }
  .filter-bar {
    grid-template-columns: minmax(140px, 1.2fr) repeat(4, minmax(106px, 1fr)) 80px !important;
  }
  .reset-button { width: 80px; }
}
@media (max-width: 1500px) {
  .directory-body { grid-template-columns: minmax(500px, 1.38fr) minmax(340px, .92fr) !important; }
  .project-card-grid {
    grid-template-columns: repeat(4, minmax(162px, 1fr));
    overflow-x: auto;
  }
}
@media (max-width: 1180px) {
  .directory-kpis {
    grid-template-columns: repeat(4, minmax(96px, 1fr)) !important;
    gap: 8px !important;
  }
  .directory-kpi {
    gap: 7px;
    min-height: 68px;
    padding: 9px 8px;
  }
  .kpi-icon {
    width: 30px;
    height: 30px;
    border-radius: 9px;
    font-size: 15px;
  }
  .directory-kpi p { font-size: 12px; }
  .directory-kpi strong { font-size: 18px; }
  .directory-kpi small { font-size: 11px; }
  .directory-body {
    grid-template-columns: minmax(500px, 1.35fr) minmax(330px, .95fr) !important;
    min-width: 840px;
  }
  .project-card-grid {
    grid-template-columns: repeat(4, minmax(162px, 1fr));
    grid-auto-rows: 160px;
    gap: 8px;
    overflow-x: auto;
  }
  .project-card {
    height: 160px;
    min-height: 160px;
    padding: 10px 10px 0;
    padding-bottom: 32px;
  }
  .filter-bar {
    grid-template-columns: minmax(118px, 1.15fr) repeat(4, minmax(88px, 1fr)) 36px !important;
    gap: 6px;
    padding: 8px;
  }
  .filter-search { min-width: 0; }
  .filter-item {
    width: 100%;
    grid-template-columns: minmax(0, 1fr);
    gap: 4px;
  }
  .filter-item > span {
    display: block;
    height: 14px;
    overflow: hidden;
    color: var(--shm-text-main);
    font-size: 11px;
    line-height: 14px;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .filter-select,
  .date-filter :deep(.el-date-editor) {
    width: 100%;
  }
  .reset-button {
    width: 36px;
    padding-right: 0;
    padding-left: 0;
  }
  .reset-button :deep(span) { display: none; }
}
@media (max-width: 760px) {
  .project-directory {
    overflow-x: auto;
  }
  .directory-kpis {
    grid-template-columns: repeat(4, minmax(92px, 1fr)) !important;
    min-width: 420px;
  }
  .filter-bar {
    grid-template-columns: minmax(112px, 1.15fr) repeat(4, minmax(84px, 1fr)) 36px !important;
    min-width: 560px;
    align-items: center;
  }
  .filter-item {
    gap: 6px;
  }
  .filter-search,
  .filter-select,
  .reset-button,
  .date-filter :deep(.el-date-editor) {
    width: 100%;
  }
  .reset-button {
    width: 36px;
  }
  .directory-body {
    min-width: 820px;
  }
  .map-surface { min-height: 300px; }
  .unit-kpis {
    grid-template-columns: repeat(2, minmax(0, 1fr));
    row-gap: 8px;
  }
  .unit-kpis div:nth-child(2n) {
    border-right: 0;
  }
  .unit-actions {
    justify-content: stretch;
  }
  .unit-actions .el-button {
    flex: 1;
  }
}
</style>


