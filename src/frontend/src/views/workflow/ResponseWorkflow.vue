<template>
  <section class="response-workbench">
    <section class="response-two-column">
      <aside class="relation-card event-nav-card">
        <div class="object-nav-head">
          <div>
            <strong>Object Tree</strong>
          </div>
          <div class="object-nav-actions">
            <el-segmented v-model="navMode" :options="navModeOptions" size="small" />
            <el-button class="nav-refresh" :icon="Refresh" text @click="load">Refresh</el-button>
          </div>
        </div>
        <el-tree
          class="object-tree"
          :data="objectTreeData"
          node-key="id"
          default-expand-all
          highlight-current
          :props="{ children: 'children', label: 'label' }"
          @node-click="selectObjectNode"
        >
          <template #default="{ data }">
            <span class="tree-node">
              <strong>{{ data.label }}</strong>
              <small v-if="data.meta">{{ data.meta }}</small>
            </span>
            <span v-if="data.count !== undefined" class="tree-count">{{ data.count }}</span>
          </template>
        </el-tree>
      </aside>

      <main class="relation-card response-logic-card">
        <div class="panel-title response-logic-title">
          <div>
            <strong>Response Logic</strong>
          </div>
          <el-tag effect="plain">{{ responseEvents.length }} events</el-tag>
        </div>
        <div class="event-response-kpis">
          <article>
            <span>Event Source</span>
            <strong>{{ selectedEvent && isForecastEvent(selectedEvent) ? 'Forecast' : 'Observed' }}</strong>
          </article>
          <article>
            <span>Warning Level</span>
            <strong>{{ levelText(selectedEvent?.eventLevel) }}</strong>
          </article>
          <article>
            <span>Response Tasks</span>
            <strong>{{ responseTaskRows.length }} items</strong>
          </article>
          <article>
            <span>Evidence</span>
            <strong>{{ responseArchiveRows.length }} resources</strong>
          </article>
        </div>

        <section class="related-events-section">
          <el-input v-model="keyword" class="event-search" placeholder="Search metric / reason / status" clearable />
          <div class="response-event-list">
            <article
              v-for="row in eventActionRows"
              :key="row.key"
              class="response-event-item"
              :class="{ active: Number(row.event.id) === Number(selectedEvent?.id) }"
              @click="selectEvent(row.event)"
            >
              <button type="button" class="event-summary-button">
                <span :class="['level-pill', `level-${row.event.eventLevel || 'normal'}`]">{{ levelText(row.event.eventLevel) }}</span>
                <el-tag size="small" :type="isForecastEvent(row.event) ? 'warning' : 'info'">{{ isForecastEvent(row.event) ? 'Forecast' : 'Observed' }}</el-tag>
                <strong>{{ row.title }}</strong>
              </button>
              <div class="event-action-buttons">
                <el-button v-if="isForecastEvent(row.event)" size="small" @click.stop="openPredictionEvidence(row.event)">Model Evidence</el-button>
                <el-button :icon="Message" size="small" :disabled="row.notificationCount === 0" @click.stop="openEventNotification(row.event)">Notification {{ row.notificationCount }}</el-button>
                <el-button :icon="Document" size="small" :disabled="row.reportCount === 0" @click.stop="openEventReport(row.event)">Report {{ row.reportCount }}</el-button>
                <el-button :icon="FolderChecked" size="small" :disabled="row.evidenceCount === 0" @click.stop="openEventEvidence(row.event)">Evidence {{ row.evidenceCount }}</el-button>
              </div>
            </article>
            <el-empty v-if="!eventActionRows.length" description="No events for the current object" />
          </div>
        </section>

        <section class="chain-detail-section">
          <el-tabs v-model="activeChainTab" class="chain-tabs">
            <el-tab-pane label="Task Queue" name="tasks">
              <el-table :data="responseTaskRows" stripe height="100%" class="chain-table">
                <el-table-column label="Task Type" width="120">
                  <template #default="{ row }">{{ taskTypeText(row.type) }}</template>
                </el-table-column>
                <el-table-column prop="code" label="Task ID" width="150" show-overflow-tooltip />
                <el-table-column prop="title" label="Task Name" min-width="220" show-overflow-tooltip />
                <el-table-column label="Current Status" width="120">
                  <template #default="{ row }">
                    <el-tag :type="statusTagType(row.status)" effect="plain">{{ statusText(row.status) }}</el-tag>
                  </template>
                </el-table-column>
                <el-table-column label="Updated At" width="170" show-overflow-tooltip>
                  <template #default="{ row }">{{ timeText(row.time) }}</template>
                </el-table-column>
                <el-table-column label="Actions" width="96" fixed="right">
                  <template #default="{ row }">
                    <el-button text type="primary" @click="openTaskRow(row)">View</el-button>
                  </template>
                </el-table-column>
              </el-table>
            </el-tab-pane>
            <el-tab-pane label="Subscribers" name="subscribers">
              <el-table :data="relatedSubscribers" stripe height="100%" class="chain-table">
                <el-table-column label="Name" width="160" show-overflow-tooltip>
                  <template #default="{ row }">{{ row.subscriberName || row.name || row.receiverName || 'Subscribers' }}</template>
                </el-table-column>
                <el-table-column label="Channel" width="110">
                  <template #default="{ row }">{{ row.channelType || row.notifyType || row.roleName || '-' }}</template>
                </el-table-column>
                <el-table-column label="Email / Address" min-width="260" show-overflow-tooltip>
                  <template #default="{ row }">{{ row.email || row.contactEmail || row.mobile || row.webhookUrl || row.target || '-' }}</template>
                </el-table-column>
                <el-table-column label="Lowest Level" width="110">
                  <template #default="{ row }">{{ row.minEventLevel || row.eventLevel || '-' }}</template>
                </el-table-column>
                <el-table-column label="Enabled" width="90">
                  <template #default="{ row }">
                    <el-tag :type="Number(row.enabled ?? 1) === 1 ? 'success' : 'info'" effect="plain">{{ Number(row.enabled ?? 1) === 1 ? 'Enabled' : 'Disabled' }}</el-tag>
                  </template>
                </el-table-column>
              </el-table>
            </el-tab-pane>
            <el-tab-pane label="State Transitions" name="transitions">
              <el-table :data="relatedTransitions" stripe height="100%" class="chain-table">
                <el-table-column label="Source Status" width="120">
                  <template #default="{ row }">{{ statusText(row.fromState || row.sourceState) }}</template>
                </el-table-column>
                <el-table-column label="Target Status" width="120">
                  <template #default="{ row }">{{ statusText(row.toState || row.targetState || row.deliveryStatus || row.status) }}</template>
                </el-table-column>
                <el-table-column label="Transition Type" width="150" show-overflow-tooltip>
                  <template #default="{ row }">{{ row.transitionType || row.decision || '-' }}</template>
                </el-table-column>
                <el-table-column label="Reason" min-width="280" show-overflow-tooltip>
                  <template #default="{ row }">{{ row.reason || row.message || '-' }}</template>
                </el-table-column>
                <el-table-column label="Time" width="170" show-overflow-tooltip>
                  <template #default="{ row }">{{ timeText(row.transitionAt || row.createdAt || row.updatedAt) }}</template>
                </el-table-column>
              </el-table>
            </el-tab-pane>
            <el-tab-pane label="Delivery Logs" name="logs">
              <el-table :data="relatedDeliveryLogs" stripe height="100%" class="chain-table">
                <el-table-column label="Task" width="110">
                  <template #default="{ row }">{{ row.taskId || row.taskCode || '-' }}</template>
                </el-table-column>
                <el-table-column label="Channel" width="110">
                  <template #default="{ row }">{{ row.channelType || row.deliveryType || row.provider || '-' }}</template>
                </el-table-column>
                <el-table-column label="Recipients" min-width="240" show-overflow-tooltip>
                  <template #default="{ row }">{{ row.receiver || row.toEmail || row.toEmails || row.target || '-' }}</template>
                </el-table-column>
                <el-table-column label="Status" width="110">
                  <template #default="{ row }">
                    <el-tag :type="statusTagType(row.deliveryStatus || row.status)" effect="plain">{{ statusText(row.deliveryStatus || row.status) }}</el-tag>
                  </template>
                </el-table-column>
                <el-table-column label="Error" min-width="220" show-overflow-tooltip>
                  <template #default="{ row }">{{ row.errorMessage || row.failReason || '-' }}</template>
                </el-table-column>
                <el-table-column label="Time" width="170" show-overflow-tooltip>
                  <template #default="{ row }">{{ timeText(row.deliveredAt || row.sentAt || row.createdAt) }}</template>
                </el-table-column>
              </el-table>
            </el-tab-pane>
            <el-tab-pane label="Evidence Archive" name="evidence">
              <el-table :data="responseArchiveRows" stripe height="100%" class="chain-table">
                <el-table-column prop="type" label="Resource Type" width="120" />
                <el-table-column prop="title" label="Resource Name" min-width="240" show-overflow-tooltip />
                <el-table-column prop="time" label="Archived At" width="170" show-overflow-tooltip />
                <el-table-column label="Actions" width="96" fixed="right">
                  <template #default="{ row }">
                    <el-button text type="primary" @click="openArchiveRow(row)">View</el-button>
                  </template>
                </el-table-column>
              </el-table>
            </el-tab-pane>
          </el-tabs>
        </section>
      </main>
    </section>

    <ResponseDetailDialogs
      v-model:notification-visible="notificationDialogVisible"
      v-model:report-visible="reportDialogVisible"
      v-model:evidence-visible="evidenceDialogVisible"
      :selected-notification="selectedNotification"
      :selected-report="selectedReport"
      :selected-evidence="selectedEvidence"
      :notification-mail-html="notificationMailHtml"
      :report-mail-html="reportMailHtml"
      :evidence-detail-facts="evidenceDetailFacts"
      @download-report="downloadSelectedReport"
    />
    <PredictionEvidenceDrawer v-model="predictionEvidenceVisible" :event-id="predictionEvidenceEventId" />

  </section>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { Document, FolderChecked, Message, Refresh } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { listEvents } from '../../api/modules/event'
import { listEvidence } from '../../api/modules/evidence'
import { getProjectObjectTree } from '../../api/modules/project'
import { listReports, reportDownloadUrl } from '../../api/modules/report'
import {
  listEventResponseWorkflows,
  listNotificationDeliveryLogs,
  listNotificationSubscribers,
  listResponseNotifications,
  listNotificationTransitions
} from '../../api/modules/response'
import { useProjectContext } from '../../composables/useProjectContext'
import type { InstrumentNode, MonitoringEvent, ProjectObjectTree, StationNode } from '../../types/engineering'
import ResponseDetailDialogs from './components/ResponseDetailDialogs.vue'
import PredictionEvidenceDrawer from '../../components/PredictionEvidenceDrawer.vue'

type Row = Record<string, any>
type ChainTab = 'tasks' | 'subscribers' | 'transitions' | 'logs' | 'evidence'
interface ObjectTreeNode {
  id: string
  label: string
  meta?: string
  count?: number
  kind: 'project' | 'station' | 'instrumentType' | 'instrument'
  station?: StationNode
  stations?: StationNode[]
  instrumentType?: string
  instrument?: InstrumentNode
  children?: ObjectTreeNode[]
}

const route = useRoute()
const { projectId } = useProjectContext()
const keyword = ref('')
const events = ref<MonitoringEvent[]>([])
const workflows = ref<Row[]>([])
const notificationTasks = ref<Row[]>([])
const notificationSubscribers = ref<Row[]>([])
const notificationTransitions = ref<Row[]>([])
const notificationDeliveryLogs = ref<Row[]>([])
const reports = ref<Row[]>([])
const evidence = ref<Row[]>([])
const objectTree = ref<ProjectObjectTree | null>(null)
const selectedEventId = ref<number>()
const selectedWorkflowId = ref<number>()
const selectedObjectId = ref('project')
const notificationDialogVisible = ref(false)
const reportDialogVisible = ref(false)
const evidenceDialogVisible = ref(false)
const predictionEvidenceVisible = ref(false)
const predictionEvidenceEventId = ref<number>()
const selectedNotification = ref<Row>()
const selectedReport = ref<Row>()
const selectedEvidence = ref<Row>()
const activeChainTab = ref<ChainTab>(chainTab(route.query.tab))
const navMode = ref<'station' | 'instrument'>('station')
const navModeOptions = [
  { label: 'By Point', value: 'station' },
  { label: 'By Device', value: 'instrument' }
]

function chainTab(value: unknown): ChainTab {
  const tab = String(value || '') as ChainTab
  return ['tasks', 'subscribers', 'transitions', 'logs', 'evidence'].includes(tab) ? tab : 'tasks'
}

function projectDisplayName() {
  return objectTree.value?.project?.projectName || objectTree.value?.project?.projectCode || 'SHM-EM Project'
}

const stations = computed(() => objectTree.value?.stations || [])
const objectTreeData = computed<ObjectTreeNode[]>(() => buildObjectTree())
const selectedObject = computed(() => findObjectNode(selectedObjectId.value))
const selectedObjectLabel = computed(() => selectedObject.value?.label || 'All Objects')
const objectScopedEvents = computed(() => events.value.filter(event => isEventRelatedToObject(event, selectedObject.value)))
const responseEvents = computed(() => {
  const text = keyword.value.trim().toLowerCase()
  const rows = objectScopedEvents.value
  return text ? rows.filter(event => JSON.stringify(event).toLowerCase().includes(text)) : rows
})
const selectedEvent = computed(() => responseEvents.value.find(item => Number(item.id) === Number(selectedEventId.value)) || responseEvents.value[0] || events.value[0])
const selectedEventTitle = computed(() => selectedEvent.value ? warningEventTitleOfEvent(selectedEvent.value) : 'No Event Selected')
const selectedWorkflow = computed(() => {
  const eventId = Number(selectedEvent.value?.id)
  return workflows.value.find(item => Number(item.eventId) === eventId)
    || workflows.value.find(item => Number(item.id) === Number(selectedWorkflowId.value))
    || workflows.value[0]
})
const selectedEventObjectLabel = computed(() => objectLabelOfEvent(selectedEvent.value))
const eventDetailFacts = computed(() => [
  { label: 'Affected Object', value: selectedEventObjectLabel.value },
  { label: 'Monitoring Metric', value: String(selectedEvent.value?.metricCode || selectedEvent.value?.eventType || '-') },
  { label: 'Trigger / Threshold', value: `${valueText(selectedEvent.value?.triggerValue, selectedEvent.value?.unit)} / ${valueText(selectedEvent.value?.thresholdValue, selectedEvent.value?.unit)}` },
  { label: 'Event Status', value: statusText(selectedEvent.value?.eventStatus) },
  { label: 'Detected At', value: timeText(selectedEvent.value?.detectedAt) },
  { label: 'Response Workflow', value: String(selectedWorkflow.value?.workflowCode || 'Unmatched') }
])
const evidenceDetailFacts = computed(() => {
  const row = selectedEvidence.value || {}
  return [
    { label: 'Evidence ID', value: String(row.id || row.evidenceCode || '-') },
    { label: 'Event ID', value: String(row.relatedEventCode || row.eventCode || row.eventId || selectedEvent.value?.eventCode || '-') },
    { label: 'Evidence Type', value: String(row.evidenceType || row.resourceType || '-') },
    { label: 'Archive Status', value: statusText(row.status) },
    { label: 'Archived At', value: timeText(row.archivedAt || row.createdAt || row.updatedAt) },
    { label: 'Resource URL', value: String(row.resourceUrl || row.fileUrl || row.relativePath || '-') }
  ]
})
const notificationMailHtml = computed(() => {
  const row = selectedNotification.value || {}
  const html = row.content || row.htmlContent || row.mailContent
  if (isHtmlContent(html)) return String(html)
  return buildNotificationMailHtml(row)
})
const reportMailHtml = computed(() => {
  const row = selectedReport.value || {}
  const html = row.contentHtml || row.content || row.reportHtml || row.htmlContent || row.mailContent
  if (isHtmlContent(html)) return String(html)
  return buildReportMailHtml(row)
})

const eventActionRows = computed(() => responseEvents.value.map(event => {
  const notificationRows = rowsRelatedToEvent(notificationTasks.value, event)
  const reportRows = rowsRelatedToEvent(reports.value, event)
  const evidenceRows = rowsRelatedToEvent(evidence.value, event)
  return {
    key: String(event.id || event.eventCode),
    event,
    title: warningEventTitleOfEvent(event),
    notificationCount: notificationRows.length,
    reportCount: reportRows.length,
    evidenceCount: evidenceRows.length
  }
}))
const selectedNotificationRows = computed(() => rowsRelatedToEvent(notificationTasks.value, selectedEvent.value))
const selectedReportRows = computed(() => rowsRelatedToEvent(reports.value, selectedEvent.value))
const selectedEvidenceRows = computed(() => rowsRelatedToEvent(evidence.value, selectedEvent.value))
const responseTaskRows = computed(() => [
  ...selectedNotificationRows.value.map(row => taskRow('notification', row, 'Notification Task', Message, 'blue')),
  ...selectedReportRows.value.map(row => taskRow('report', row, 'Report Generation', Document, 'purple')),
  ...selectedEvidenceRows.value.map(row => taskRow('evidence', row, 'Evidence Archive', FolderChecked, 'orange'))
])
const relatedSubscribers = computed(() => {
  const taskRows = selectedNotificationRows.value
  const taskChannelIds = new Set(taskRows.map(row => String(row.channelId || row.notificationChannelId || '')).filter(Boolean))
  const taskChannelTypes = new Set(taskRows.map(row => String(row.channelType || row.notifyType || '')).filter(Boolean))
  const rows = notificationSubscribers.value.filter(row => {
    if (taskChannelIds.size && taskChannelIds.has(String(row.channelId || row.notificationChannelId || ''))) return true
    if (taskChannelTypes.size && taskChannelTypes.has(String(row.channelType || row.notifyType || ''))) return true
    return !taskChannelIds.size && !taskChannelTypes.size
  })
  return rows.slice(0, 12)
})
const relatedTransitions = computed(() => {
  const rows = notificationTransitions.value.filter(row => rowRelatedToSelectedTasks(row) || isRowRelatedToEvent(row, selectedEvent.value as MonitoringEvent))
  if (rows.length) return rows.slice(0, 20)
  return responseTaskRows.value.map<Row>((task, index) => ({
    id: `fallback-${task.key}-${index}`,
    fromState: index === 0 ? 'created' : 'queued',
    toState: task.status || 'pending',
    createdAt: task.time,
    message: task.title
  }))
})
const relatedDeliveryLogs = computed(() => notificationDeliveryLogs.value
  .filter(row => rowRelatedToSelectedTasks(row) || isRowRelatedToEvent(row, selectedEvent.value as MonitoringEvent))
  .slice(0, 20))
const responseArchiveRows = computed(() => [
  ...selectedReportRows.value.map(row => archiveRow('report', row, 'Report Instance')),
  ...selectedEvidenceRows.value.map(row => archiveRow('evidence', row, 'Evidence Resource'))
])
function downloadSelectedReport(format: 'docx' | 'pdf') {
  const id = selectedReport.value?.id
  if (!id) {
    ElMessage.warning('Select a report instance')
    return
  }
  const presetUrl = format === 'docx' ? selectedReport.value?.docxUrl : selectedReport.value?.pdfUrl
  window.open(String(presetUrl || reportDownloadUrl(id, format)), '_blank')
}

function openEventNotification(event: MonitoringEvent) {
  selectEvent(event)
  const row = rowsRelatedToEvent(notificationTasks.value, event)[0]
  if (!row) {
    ElMessage.warning('No notification task for the current event')
    return
  }
  selectedNotification.value = row
  notificationDialogVisible.value = true
}

function openEventReport(event: MonitoringEvent) {
  selectEvent(event)
  const row = rowsRelatedToEvent(reports.value, event)[0]
  if (!row) {
    ElMessage.warning('No report for the current event')
    return
  }
  selectedReport.value = row
  reportDialogVisible.value = true
}

function openEventEvidence(event: MonitoringEvent) {
  selectEvent(event)
  const row = rowsRelatedToEvent(evidence.value, event)[0]
  if (!row) {
    ElMessage.warning('No archived evidence for the current event')
    return
  }
  selectedEvidence.value = row
  evidenceDialogVisible.value = true
}

async function load() {
  const [
    eventRows,
    workflowRows,
    notificationRows,
    subscriberRows,
    transitionRows,
    deliveryLogRows,
    reportRows,
    evidenceRows,
    objectRows
  ] = await Promise.all([
    listEvents({ projectId: projectId.value, limit: 200 }),
    listEventResponseWorkflows({ projectId: projectId.value }),
    listResponseNotifications({ projectId: projectId.value }),
    listNotificationSubscribers({ projectId: projectId.value }),
    listNotificationTransitions({ projectId: projectId.value, limit: 200 }),
    listNotificationDeliveryLogs({ projectId: projectId.value, limit: 200 }),
    listReports({ projectId: projectId.value, limit: 200 }),
    listEvidence({ projectId: projectId.value, limit: 200 }),
    getProjectObjectTree(projectId.value)
  ])
  events.value = eventRows
  workflows.value = workflowRows
  notificationTasks.value = notificationRows
  notificationSubscribers.value = subscriberRows
  notificationTransitions.value = transitionRows
  notificationDeliveryLogs.value = deliveryLogRows
  reports.value = reportRows as Row[]
  evidence.value = evidenceRows as Row[]
  objectTree.value = objectRows
  const routeWorkflowId = Number(route.params.workflowId)
  const requestedEventId = Number(route.query.eventId)
  const matchedWorkflow = workflowRows.find(row => requestedEventId && Number(row.eventId) === requestedEventId)
    || workflowRows.find(row => Number(row.id) === routeWorkflowId)
    || workflowRows[0]
  selectedWorkflowId.value = matchedWorkflow?.id !== undefined ? Number(matchedWorkflow.id) : undefined
  selectedEventId.value = Number(requestedEventId || matchedWorkflow?.eventId || eventRows[0]?.id)
  selectedObjectId.value = objectKeyOfEvent(events.value.find(event => Number(event.id) === Number(selectedEventId.value))) || 'project'
}

function selectEvent(event: MonitoringEvent) {
  selectedEventId.value = Number(event.id)
  const workflow = workflows.value.find(row => Number(row.eventId) === Number(event.id))
  selectedWorkflowId.value = workflow?.id !== undefined ? Number(workflow.id) : undefined
}

function isForecastEvent(event: MonitoringEvent) {
  const source = String(event.sourceType || '').toUpperCase()
  return source === 'FORECAST' || source === 'PREDICTION'
}

function openPredictionEvidence(event: MonitoringEvent) {
  predictionEvidenceEventId.value = event.id !== undefined ? Number(event.id) : undefined
  predictionEvidenceVisible.value = Boolean(predictionEvidenceEventId.value)
}

function selectObjectNode(node: ObjectTreeNode) {
  selectedObjectId.value = node.id
  const firstEvent = events.value.find(event => isEventRelatedToObject(event, node))
  selectedEventId.value = firstEvent?.id !== undefined ? Number(firstEvent.id) : undefined
  const workflow = workflows.value.find(row => Number(row.eventId) === Number(selectedEventId.value))
  selectedWorkflowId.value = workflow?.id !== undefined ? Number(workflow.id) : undefined
}

function buildObjectTree(): ObjectTreeNode[] {
  const children = navMode.value === 'station' ? buildStationModeTree() : buildInstrumentModeTree()
  return [{
    id: 'project',
    label: objectTree.value?.project?.projectName || objectTree.value?.project?.projectCode || 'All Objects',
    kind: 'project',
    count: children.length,
    children
  }]
}

function buildStationModeTree(): ObjectTreeNode[] {
  const siteMap = new Map<string, { label: string; stations: StationNode[]; rows: Array<{ station: StationNode; instrument: InstrumentNode }> }>()
  for (const station of stations.value) {
    const key = stationGroupKey(station)
    const item = siteMap.get(key) || { label: stationDisplayLabel(station), stations: [], rows: [] }
    item.stations.push(station)
    for (const instrument of station.instruments || []) {
      item.rows.push({ station, instrument })
    }
    siteMap.set(key, item)
  }
  const stationNodes = Array.from(siteMap.entries()).sort((a, b) => stationGroupSortNo(a[0], a[1].label) - stationGroupSortNo(b[0], b[1].label)).map(([key, item]) => ({
    id: `station-group:${key}`,
    label: item.label,
    kind: 'station' as const,
    station: item.stations[0],
    stations: item.stations,
    count: item.rows.length,
    children: buildInstrumentTypeNodes(item.rows, key)
  }))
  return stationNodes
}

function buildInstrumentModeTree(): ObjectTreeNode[] {
  const groups = new Map<string, Array<{ station: StationNode; instrument: InstrumentNode }>>()
  for (const station of stations.value) {
    for (const instrument of station.instruments || []) {
      const type = instrumentTypeKeyOf(instrument)
      const rows = groups.get(type) || []
      rows.push({ station, instrument })
      groups.set(type, rows)
    }
  }
  return Array.from(groups.entries()).map(([type, rows]) => {
    const stationGroups = new Map<string, { station: StationNode; stations: StationNode[]; instruments: InstrumentNode[] }>()
    for (const row of rows) {
      const key = stationGroupKey(row.station)
      const item = stationGroups.get(key) || { station: row.station, stations: [], instruments: [] }
      item.stations.push(row.station)
      item.instruments.push(row.instrument)
      stationGroups.set(key, item)
    }
    return {
      id: globalInstrumentTypeKey(type),
      label: instrumentTypeName(type),
      kind: 'instrumentType' as const,
      instrumentType: type,
      count: rows.length,
      children: Array.from(stationGroups.entries()).sort((a, b) => stationGroupSortNo(a[0], a[1].station.siteName || a[1].station.name || a[1].station.code || '') - stationGroupSortNo(b[0], b[1].station.siteName || b[1].station.name || b[1].station.code || '')).map(([stationGroup, item]) => ({
        id: instrumentTypeStationKey(type, stationGroup),
        label: stationDisplayLabel(item.station),
        kind: 'station' as const,
        station: item.station,
        stations: item.stations,
        count: item.instruments.length,
        children: item.instruments.map(instrument => ({
          id: instrumentKey(item.station, instrument),
          label: instrument.code || instrument.name || `Instrument-${instrument.id}`,
          kind: 'instrument' as const,
          station: item.station,
          instrumentType: type,
          instrument
        }))
      }))
    }
  })
}

function buildInstrumentTypeNodes(rows: Array<{ station: StationNode; instrument: InstrumentNode }>, stationGroup: string) {
  const groups = new Map<string, InstrumentNode[]>()
  for (const { instrument } of rows) {
    const typeKey = instrumentTypeKeyOf(instrument)
    const rows = groups.get(typeKey) || []
    rows.push(instrument)
    groups.set(typeKey, rows)
  }
  return Array.from(groups.entries()).map(([type, instruments]) => ({
    id: instrumentTypeKey(stationGroup, type),
    label: instrumentTypeName(type),
    kind: 'instrumentType' as const,
    station: rows[0]?.station,
    stations: rows.map(row => row.station),
    instrumentType: type,
    count: instruments.length,
    children: rows.filter(row => instrumentTypeKeyOf(row.instrument) === type).map(({ station, instrument }) => ({
      id: instrumentKey(station, instrument),
      label: instrument.code || instrument.name || `Instrument-${instrument.id}`,
      kind: 'instrument' as const,
      station,
      instrumentType: type,
      instrument
    }))
  }))
}

function findObjectNode(id: string) {
  const stack = [...objectTreeData.value]
  while (stack.length) {
    const node = stack.shift()
    if (!node) continue
    if (node.id === id) return node
    stack.push(...(node.children || []))
  }
  return objectTreeData.value[0]
}

function isEventRelatedToObject(event: MonitoringEvent, node?: ObjectTreeNode) {
  if (!node || node.kind === 'project') return true
  if (node.kind === 'station') return stationIdsOf(node).some(id => Number(event.stationId) === Number(id))
  if (node.kind === 'instrumentType') {
    if (node.stations?.length) {
      return node.stations.some(station => Number(event.stationId) === Number(station.id)
        && (station.instruments || []).some(instrument => instrumentTypeKeyOf(instrument) === node.instrumentType && Number(event.instrumentId) === Number(instrument.id)))
    }
    return stations.value.some(station => (station.instruments || []).some(instrument => (
      instrumentTypeKeyOf(instrument) === node.instrumentType
        && Number(event.stationId) === Number(station.id)
        && Number(event.instrumentId) === Number(instrument.id)
    )))
  }
  return Number(event.stationId) === Number(node.station?.id) && Number(event.instrumentId) === Number(node.instrument?.id)
}

function stationKey(station: StationNode) {
  return `station:${station.id || station.code}`
}

function stationIdsOf(node: ObjectTreeNode) {
  return (node.stations?.length ? node.stations : node.station ? [node.station] : []).map(station => station.id)
}

function sortedStations(rows: StationNode[]) {
  return [...rows].sort((a, b) => {
    const diff = stationSortNo(a) - stationSortNo(b)
    if (diff !== 0) return diff
    return stationLabel(a).localeCompare(stationLabel(b), 'zh-Hans-CN', { numeric: true })
  })
}

function stationSortNo(station: StationNode) {
  const no = stationNoOf(station)
  return no ? Number(no) : Number.MAX_SAFE_INTEGER
}

function stationLabel(station: StationNode) {
  return String(station.siteName || station.name || station.code || `Point-${station.id}`)
}

function stationDisplayLabel(station: StationNode) {
  if (station.siteName) return String(station.siteName)
  const no = stationNoOf(station)
  return no ? `Point No. ${no}` : stationLabel(station)
}

function stationGroupKey(station: StationNode) {
  const no = stationNoOf(station)
  return no ? `point-${no}` : stationKey(station)
}

function stationGroupSortNo(key: string, label = '') {
  const no = stationNoOfText(`${key} ${label}`)
  return no ? Number(no) : Number.MAX_SAFE_INTEGER
}

function stationNoOf(station: StationNode) {
  if (station.siteNo) return String(station.siteNo)
  return stationNoOfText(`${station.siteName || ''} ${station.name || ''} ${station.code || ''} ${station.stationType || ''}`)
}

function stationNoOfText(text: string) {
  const match = String(text).match(/(?:ST[-_ ]?|station|Point|point)?0*([1-9]\d*)(?:No.|#|points|[^0-9]|$)/i)
  return match?.[1]
}

function instrumentKey(station: StationNode, instrument: InstrumentNode) {
  return `instrument:${station.id || station.code}:${instrument.id || instrument.code}`
}

function instrumentTypeKey(stationGroup: string, type: string) {
  return `instrument-type:${stationGroup}:${type}`
}

function globalInstrumentTypeKey(type: string) {
  return `instrument-type:${type}`
}

function instrumentTypeStationKey(type: string, stationGroup: string) {
  return `instrument-type:${type}:station:${stationGroup}`
}

function instrumentTypeKeyOf(instrument: InstrumentNode) {
  return String(instrument.instrumentType || instrument.type || 'unknown')
}

function objectKeyOfEvent(event?: MonitoringEvent) {
  if (!event) return ''
  for (const station of stations.value) {
    for (const instrument of station.instruments || []) {
      if (Number(station.id) === Number(event.stationId) && Number(instrument.id) === Number(event.instrumentId)) {
        return instrumentKey(station, instrument)
      }
    }
    if (Number(station.id) === Number(event.stationId)) return stationKey(station)
  }
  return ''
}

function objectLabelOfEvent(event?: MonitoringEvent) {
  if (!event) return '-'
  for (const station of stations.value) {
    const stationLabel = station.siteName || station.name || station.code || `Point-${station.id}`
    const instrument = (station.instruments || []).find(item => Number(item.id) === Number(event.instrumentId))
    if (Number(station.id) === Number(event.stationId) && instrument) {
      return `${stationLabel} / ${instrumentTypeName(instrumentTypeKeyOf(instrument))} / ${instrument.code || instrument.name || `Instrument-${instrument.id}`}`
    }
    if (Number(station.id) === Number(event.stationId)) return stationLabel
  }
  return '-'
}

function instrumentTypeName(type?: string) {
  const map: Record<string, string> = {
    displacement: 'Inclinometer',
    pressure_water_level: 'Water Level Gauge',
    static_level: 'Static Level Gauge',
    earth_pressure: 'Earth Pressure Cell',
    accelerometer: 'Accelerometer'
  }
  return map[String(type || '')] || type || ''
}

function rowsRelatedToEvent(rows: Row[], event?: MonitoringEvent) {
  if (!event) return []
  return rows.filter(row => isRowRelatedToEvent(row, event))
}

function taskRow(type: string, row: Row, fallbackTitle: string, icon: unknown, tone: string) {
  const code = String(row.taskCode || row.notificationTaskCode || row.workflowCode || row.reportCode || row.evidenceCode || row.id || '-')
  return {
    key: `${type}-${code}`,
    type,
    row,
    icon,
    tone,
    title: String(row.taskName || row.title || row.reportName || row.evidenceType || fallbackTitle),
    code,
    status: String(row.status || row.deliveryStatus || row.taskStatus || row.generateStatus || '-'),
    time: row.updatedAt || row.createdAt || row.sentAt || row.generatedAt || row.archivedAt
  }
}

function archiveRow(type: string, row: Row, fallbackTitle: string) {
  return {
    key: `${type}-${row.id || row.evidenceCode || row.reportCode || row.relativePath || row.resourceUrl}`,
    type: fallbackTitle,
    row,
    title: String(row.fileName || row.reportName || row.evidenceCode || row.resourceType || fallbackTitle),
    time: timeText(row.archivedAt || row.generatedAt || row.capturedAt || row.createdAt || row.updatedAt)
  }
}

function rowRelatedToSelectedTasks(row: Row) {
  const taskIds = new Set(selectedNotificationRows.value.map(item => String(item.id || item.taskId || '')).filter(Boolean))
  const taskCodes = new Set(selectedNotificationRows.value.map(item => String(item.taskCode || item.notificationTaskCode || '')).filter(Boolean))
  const rowTaskId = String(row.taskId || row.notificationTaskId || row.id || '')
  const rowTaskCode = String(row.taskCode || row.notificationTaskCode || row.sourceTaskCode || '')
  return Boolean((rowTaskId && taskIds.has(rowTaskId)) || (rowTaskCode && taskCodes.has(rowTaskCode)))
}

function openTaskRow(task: ReturnType<typeof taskRow>) {
  if (task.type === 'notification') {
    selectedNotification.value = task.row
    notificationDialogVisible.value = true
  } else if (task.type === 'report') {
    selectedReport.value = task.row
    reportDialogVisible.value = true
  } else if (task.type === 'evidence') {
    selectedEvidence.value = task.row
    evidenceDialogVisible.value = true
  }
}

function openArchiveRow(item: ReturnType<typeof archiveRow>) {
  if (item.type === 'Report Instance') {
    selectedReport.value = item.row
    reportDialogVisible.value = true
  } else {
    selectedEvidence.value = item.row
    evidenceDialogVisible.value = true
  }
}

function warningEventTitleOfEvent(event?: MonitoringEvent) {
  if (!event) return 'Warning Event'
  if (isForecastEvent(event)) return `Forecast Warning: ${metricLabel(event.metricCode)}`
  const eventRow = event as Row
  const rawTitle = String(eventRow.warningEventName || event.triggerReason || eventRow.eventName || 'Warning Event')
  const directTitle = isEventIdentifierText(rawTitle) ? 'Warning Event' : rawTitle
  if (directTitle.includes('Warning')) return directTitle
  return `${levelText(event.eventLevel)} Warning: ${directTitle}`
}

function metricLabel(value?: string) {
  return String(value || 'Metric').split('_').filter(Boolean).map(word => word.charAt(0).toUpperCase() + word.slice(1)).join(' ')
}

function isEventIdentifierText(value?: string) {
  const text = String(value || '').trim()
  return /^(?:SIM-)?F?EVT[-_]\w+/i.test(text) || /^\d{6,}$/.test(text)
}

function isRowRelatedToEvent(row: Row, event: MonitoringEvent) {
  if (!event) return false
  const rowEventId = row.eventId ?? row.event_id
  if (rowEventId !== undefined && event.id !== undefined && Number(rowEventId) === Number(event.id)) return true
  const relatedCode = String(row.relatedEventCode || row.eventCode || row.event_code || '')
  return Boolean(relatedCode && event.eventCode && relatedCode === event.eventCode)
}

function isHtmlContent(value: unknown) {
  return /<\/?[a-z][\s\S]*>/i.test(String(value || ''))
}

function escapeHtml(value: unknown) {
  return String(value ?? '-')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;')
}

function parseJsonLike(value: unknown): Row {
  if (!value) return {}
  if (typeof value === 'object') return value as Row
  try {
    return JSON.parse(String(value))
  } catch (error) {
    return {}
  }
}

function buildNotificationMailHtml(row: Row) {
  const event = selectedEvent.value
  const target = parseJsonLike(row.targetJson)
  return `
    <h2 style="color:#b00000;">${escapeHtml(row.subject || 'Engineering Monitoring Warning Notice')}</h2>
    <p><b>Period: </b>${escapeHtml(timeText(row.createdAt || row.sentAt))} to ${escapeHtml(timeText(row.sentAt || row.updatedAt || row.createdAt))}</p>
    <p><b>Channel: </b>${escapeHtml(row.channelName || row.channelType || '-')} ; <b>Recipient: </b>${escapeHtml(target.to || target.receiver || target.channel || '-')}</p>
    <p><b>Rule: </b>${escapeHtml(event?.triggerReason || row.message || row.content || '-')}</p>
    <table border="1" cellspacing="0" cellpadding="6" style="border-collapse:collapse;min-width:980px;">
      <tr style="background:#f2f2f2;">
        <th>Level</th><th>Event ID</th><th>Point/Instrument</th><th>Metric</th><th>Trigger Value</th><th>Threshold</th><th>Collected At</th><th>Reason</th>
      </tr>
      <tr>
        <td>${escapeHtml(levelText(event?.eventLevel))}</td>
        <td>${escapeHtml(event?.eventCode || row.eventId || '-')}</td>
        <td>${escapeHtml(selectedEventObjectLabel.value)}</td>
        <td>${escapeHtml(event?.metricCode || event?.eventType || '-')}</td>
        <td>${escapeHtml(valueText(event?.triggerValue, event?.unit))}</td>
        <td>${escapeHtml(valueText(event?.thresholdValue, event?.unit))}</td>
        <td>${escapeHtml(timeText(event?.detectedAt || row.createdAt))}</td>
        <td>${escapeHtml(event?.triggerReason || row.message || '-')}</td>
      </tr>
    </table>
    <p><b>Handling advice: </b>Check the related monitoring point, sensor, and site condition promptly; arrange site review, drainage, or maintenance when necessary.</p>
    <p style="color:#666;">This email is automatically generated by the structural health monitoring system.</p>
  `
}

function reportPeriodText(row: Row) {
  if (row.periodStart || row.periodEnd) return `${timeText(row.periodStart)} to ${timeText(row.periodEnd)}`
  const generated = timeText(row.generatedAt || row.createdAt || row.updatedAt)
  if (String(row.reportType || '').toLowerCase().includes('week')) return `${generated} Week of`
  return generated
}

function buildReportMailHtml(row: Row) {
  const type = String(row.reportType || '').toLowerCase()
  const reportKind = type.includes('week') ? 'Weekly Report' : type.includes('daily') || type.includes('day') ? 'Daily Report' : 'Monitoring Report'
  const title = row.reportTitle || row.reportName || `${projectDisplayName()} ${reportKind}`
  const eventRows = responseEvents.value.slice(0, 8)
  const eventTableRows = eventRows.length ? eventRows.map(event => `
    <tr>
      <td>${escapeHtml(levelText(event.eventLevel))}</td>
      <td>${escapeHtml(event.eventCode || event.id || '-')}</td>
      <td>${escapeHtml(objectLabelOfEvent(event))}</td>
      <td>${escapeHtml(event.metricCode || event.eventType || '-')}</td>
      <td>${escapeHtml(valueText(event.triggerValue, event.unit))}</td>
      <td>${escapeHtml(valueText(event.thresholdValue, event.unit))}</td>
      <td>${escapeHtml(timeText(event.detectedAt))}</td>
      <td>${escapeHtml(event.triggerReason || '-')}</td>
    </tr>
  `).join('') : `
    <tr>
      <td colspan="8" style="text-align:center;color:#666;">No related warning events in the reporting period</td>
    </tr>
  `
  return `
    <h2 style="color:#b00000;">${escapeHtml(title)}Email${escapeHtml(reportKind)}</h2>
    <p><b>Period: </b>${escapeHtml(reportPeriodText(row))}</p>
    <p><b>Project name: </b>${escapeHtml(projectDisplayName())} ; <b>Report type: </b>${escapeHtml(reportKind)} ; <b>Generated at: </b>${escapeHtml(timeText(row.generatedAt || row.createdAt || row.updatedAt))}</p>
    <p><b>Report summary: </b>${escapeHtml(row.summary || row.message || 'This report summarizes monitored objects, warning events, response handling, and evidence archiving during the reporting period.')}</p>
    <table border="1" cellspacing="0" cellpadding="6" style="border-collapse:collapse;min-width:980px;">
      <tr style="background:#f2f2f2;">
        <th>Level</th><th>Event ID</th><th>Point/Instrument</th><th>Metric</th><th>Trigger Value</th><th>Threshold</th><th>Collected At</th><th>Reason</th>
      </tr>
      ${eventTableRows}
    </table>
    <p><b>Handling advice: </b>Review open items using abnormal events, monitoring trends, and site evidence from the daily/weekly report, then create handling records.</p>
    <p><b>Report resource: </b>${escapeHtml(row.reportUrl || row.fileUrl || row.resourceUrl || '-')}</p>
    <p style="color:#666;">This email is automatically generated by the structural health monitoring system.</p>
  `
}

function isDone(status?: string) {
  return ['finished', 'completed', 'generated', 'archived', 'sent', 'success', 'closed'].includes(String(status || '').toLowerCase())
}

function statusClass(status?: string) {
  if (isDone(status)) return 'done'
  if (['failed', 'error'].includes(String(status || '').toLowerCase())) return 'error'
  if (['running', 'pending'].includes(String(status || '').toLowerCase())) return 'running'
  return 'waiting'
}

function statusTagType(status?: string) {
  if (isDone(status)) return 'success'
  if (['failed', 'error'].includes(String(status || '').toLowerCase())) return 'danger'
  if (['running', 'pending'].includes(String(status || '').toLowerCase())) return 'warning'
  return 'info'
}

function statusText(status?: string) {
  const map: Record<string, string> = {
    finished: 'Completed',
    completed: 'Completed',
    generated: 'Generated',
    archived: 'Archived',
    sent: 'Sent',
    success: 'Success',
    created: 'Created',
    open: 'New Event',
    new: 'New Event',
    acknowledged: 'Acknowledged',
    resolved: 'Resolved',
    closed: 'Closed',
    running: 'Running',
    pending: 'Pending',
    no_recipient: 'No Recipient',
    no_state_change: 'Record Only',
    failed: 'Failed',
    error: 'Abnormal'
  }
  return map[String(status || '').toLowerCase()] || status || '-'
}

function taskTypeText(type?: string) {
  const map: Record<string, string> = {
    notification: 'Notification Task',
    report: 'Report Generation',
    evidence: 'Evidence Archive'
  }
  return map[String(type || '')] || type || '-'
}

function levelText(level?: string) {
  return String(level || 'normal').toUpperCase()
}

function levelTagType(level?: string) {
  if (level === 'red') return 'danger'
  if (level === 'orange') return 'warning'
  if (level === 'yellow') return 'success'
  return 'info'
}

function valueText(value?: number, unit?: string) {
  if (value === undefined || value === null) return '-'
  return `${value}${unit ? ` ${unit}` : ''}`
}

function timeText(value?: string) {
  return value ? String(value).replace('T', ' ').slice(0, 19) : '-'
}

watch(projectId, load, { immediate: true })
watch(() => route.query.tab, value => { activeChainTab.value = chainTab(value) })
</script>

<style scoped>
:global(.main-panel:has(.response-workbench)) { overflow-x: auto; }
.response-workbench {
  display: flex;
  flex-direction: column;
  gap: 16px;
  min-width: 1320px;
  min-height: calc(100vh - 48px);
}
.relation-card {
  border: 1px solid var(--softx-border);
  border-radius: 8px;
  background: #fff;
}
.response-two-column {
  display: grid;
  grid-template-columns: 320px minmax(0, 1fr);
  gap: 16px;
  height: max(900px, calc(100vh - 58px));
  min-height: 900px;
}
.related-events-section,
.chain-detail-section {
  display: flex;
  flex-direction: column;
  min-width: 0;
  min-height: 0;
  padding: 12px;
  border: 1px solid #e5ebf3;
  border-radius: 8px;
  background: #fbfdff;
}
.chain-detail-section {
  background: #fff;
}
.relation-card {
  display: flex;
  flex-direction: column;
  min-width: 0;
  min-height: 0;
  padding: 16px;
  overflow: hidden;
}
.relation-card.response-logic-card {
  display: grid;
  grid-template-rows: auto auto minmax(260px, .72fr) minmax(520px, 1.28fr);
  gap: 12px;
}
.panel-title {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  align-items: flex-start;
  margin-bottom: 14px;
}
.panel-title > div {
  min-width: 0;
}
.panel-title strong {
  display: block;
  color: var(--softx-text);
  font-size: 16px;
}
.panel-title span {
  display: block;
  max-width: 100%;
  margin-top: 4px;
  overflow: hidden;
  color: var(--softx-muted);
  font-size: 12px;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.object-nav-head {
  display: flex;
  justify-content: space-between;
  gap: 10px;
  align-items: center;
  margin-bottom: 8px;
}
.object-nav-head strong,
.object-nav-head span {
  display: block;
}
.object-nav-head strong {
  color: var(--softx-text);
  font-size: 16px;
}
.object-nav-head :deep(.el-segmented) {
  flex-shrink: 0;
}
.object-nav-actions {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-shrink: 0;
}
.nav-refresh {
  padding: 0 4px;
}
.event-search {
  flex: none;
  margin-bottom: 10px;
}
.event-response-kpis {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 8px;
  flex: none;
  margin-bottom: 10px;
}
.event-response-kpis article {
  min-width: 0;
  padding: 9px 10px;
  border: 1px solid #e5ebf3;
  border-radius: 8px;
  background: #f8fafc;
}
.event-response-kpis span,
.event-response-kpis strong {
  display: block;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.event-response-kpis span {
  color: var(--softx-muted);
  font-size: 12px;
}
.event-response-kpis strong {
  margin-top: 4px;
  color: var(--softx-text);
  font-size: 14px;
}
.related-events-section .response-event-list {
  flex: 1;
  min-height: 0;
  overflow: auto;
}
.chain-tabs {
  display: flex;
  flex: 1;
  min-height: 0;
  flex-direction: column;
}
.chain-detail-section .chain-tabs {
  margin-top: 0;
}
.chain-tabs :deep(.el-tabs__content) {
  flex: 1;
  min-height: 0;
  overflow: auto;
}
.chain-tabs :deep(.el-tab-pane) {
  height: 100%;
  min-height: 0;
}
.chain-table {
  height: 100%;
}
.object-tree,
.response-event-list {
  flex: 1;
  min-height: 0;
  overflow: auto;
}
.object-tree {
  padding: 8px;
  border: 1px solid #e5ebf3;
  border-radius: 8px;
  background: #f8fafc;
}
.object-tree :deep(.el-tree-node__content) {
  min-height: 36px;
  border-radius: 8px;
}
.object-tree :deep(.el-tree-node__content:hover),
.object-tree :deep(.el-tree-node.is-current > .el-tree-node__content) {
  background: #eef5ff;
}
.tree-node {
  display: grid;
  min-width: 0;
}
.tree-node strong,
.tree-node small {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.tree-node strong {
  color: var(--softx-text);
}
.tree-node small {
  color: var(--softx-muted);
}
.tree-count {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 26px;
  height: 22px;
  margin-left: auto;
  padding: 0 8px;
  border-radius: 999px;
  background: #eef5ff;
  color: #2457d6;
  font-size: 12px;
  font-weight: 750;
}
.response-event-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.response-event-item {
  min-width: 0;
  padding: 10px;
  border: 1px solid #e5ebf3;
  border-radius: 8px;
  background: #f8fafc;
  text-align: left;
  cursor: pointer;
}
.response-event-item {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 8px 12px;
  align-items: center;
}
.response-event-item.active,
.response-event-item:hover {
  border-color: #2457d6;
  background: #f5f8ff;
}
.event-summary-button strong {
  display: block;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.event-summary-button strong {
  color: var(--softx-text);
}
.event-summary-button {
  position: relative;
  display: grid;
  grid-template-columns: 82px 74px minmax(0, 1fr);
  gap: 8px;
  align-items: center;
  min-width: 0;
  padding: 0;
  border: 0;
  background: transparent;
  text-align: left;
  cursor: pointer;
}
.event-action-buttons {
  display: flex;
  flex-wrap: wrap;
  justify-content: flex-end;
  gap: 6px;
  max-width: 520px;
}
.event-action-buttons :deep(.el-button + .el-button) {
  margin-left: 0;
}
.status-dot {
  width: 12px;
  height: 12px;
  border-radius: 999px;
}
.done { background: #22c55e; box-shadow: 0 0 0 3px rgba(34,197,94,.14); }
.running { background: #f59e0b; box-shadow: 0 0 0 3px rgba(245,158,11,.14); }
.error { background: #ef4444; box-shadow: 0 0 0 3px rgba(239,68,68,.14); }
.waiting { background: #94a3b8; box-shadow: 0 0 0 3px rgba(148,163,184,.14); }
.level-pill {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: fit-content;
  min-width: 72px;
  height: 26px;
  margin-bottom: 6px;
  padding: 0 10px;
  border-radius: 999px;
  background: #eef2f6;
  color: #42526d;
  font-size: 12px;
  font-weight: 750;
}
.level-red { background: #fff1f0; color: #d92d20; }
.level-orange { background: #fff4e5; color: #b55d00; }
.level-yellow { background: #fff9db; color: #8a6100; }
</style>


