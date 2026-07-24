<template>
  <el-dialog :model-value="notificationVisible" title="Notification Details" width="1080px" class="notification-dialog" @update:model-value="emit('update:notificationVisible', $event)">
    <section v-if="selectedNotification" class="notification-detail">
      <div class="notification-summary">
        <div>
          <span>Subject</span>
          <strong>{{ selectedNotification.subject || selectedNotification.notificationType || 'Notification Task' }}</strong>
        </div>
        <el-tag :type="isDone(selectedNotification.status) ? 'success' : 'warning'" effect="plain">
          {{ statusText(selectedNotification.status) }}
        </el-tag>
      </div>
      <article class="mail-preview" v-html="notificationMailHtml"></article>
    </section>
  </el-dialog>

  <el-dialog :model-value="reportVisible" title="Report Details" width="1080px" class="notification-dialog" @update:model-value="emit('update:reportVisible', $event)">
    <section v-if="selectedReport" class="notification-detail">
      <div class="notification-summary">
        <div>
          <span>Report Name</span>
          <strong>{{ selectedReport.reportTitle || selectedReport.reportName || selectedReport.reportType || 'Report Instance' }}</strong>
        </div>
        <div class="report-summary-actions">
          <el-tag :type="isDone(selectedReport.status) ? 'success' : 'warning'" effect="plain">
            {{ statusText(selectedReport.status) }}
          </el-tag>
          <el-button :icon="Download" @click="emit('downloadReport', 'docx')">Download Word</el-button>
          <el-button :icon="Download" type="primary" @click="emit('downloadReport', 'pdf')">Download PDF</el-button>
        </div>
      </div>
      <article class="mail-preview" v-html="reportMailHtml"></article>
    </section>
  </el-dialog>

  <el-dialog :model-value="evidenceVisible" title="Evidence Archive Details" width="920px" class="notification-dialog" @update:model-value="emit('update:evidenceVisible', $event)">
    <section v-if="selectedEvidence" class="notification-detail">
      <div class="notification-summary">
        <div>
          <span>Evidence Name</span>
          <strong>{{ selectedEvidence.evidenceCode || selectedEvidence.evidenceType || selectedEvidence.resourceName || 'Evidence Resource' }}</strong>
        </div>
        <el-tag :type="isDone(selectedEvidence.status) ? 'success' : 'info'" effect="plain">
          {{ statusText(selectedEvidence.status) }}
        </el-tag>
      </div>
      <div class="notification-facts">
        <article v-for="item in evidenceDetailFacts" :key="item.label">
          <span>{{ item.label }}</span>
          <strong>{{ item.value }}</strong>
        </article>
      </div>
      <pre class="evidence-raw">{{ prettyText(selectedEvidence) }}</pre>
    </section>
  </el-dialog>
</template>

<script setup lang="ts">
import { Download } from '@element-plus/icons-vue'

type Row = Record<string, any>
interface FactItem {
  label: string
  value: string
}

defineProps<{
  notificationVisible: boolean
  reportVisible: boolean
  evidenceVisible: boolean
  selectedNotification?: Row
  selectedReport?: Row
  selectedEvidence?: Row
  notificationMailHtml: string
  reportMailHtml: string
  evidenceDetailFacts: FactItem[]
}>()

const emit = defineEmits<{
  'update:notificationVisible': [value: boolean]
  'update:reportVisible': [value: boolean]
  'update:evidenceVisible': [value: boolean]
  downloadReport: [format: 'docx' | 'pdf']
}>()

function isDone(status?: string) {
  return ['finished', 'completed', 'generated', 'archived', 'sent', 'success', 'closed'].includes(String(status || '').toLowerCase())
}

function statusText(status?: string) {
  const value = String(status || '').toLowerCase()
  const map: Record<string, string> = {
    pending: 'Pending',
    created: 'Created',
    running: 'Running',
    finished: 'Completed',
    completed: 'Completed',
    generated: 'Generated',
    archived: 'Archived',
    sent: 'Sent',
    success: 'Success',
    failed: 'Failed',
    closed: 'Closed'
  }
  return map[value] || String(status || '-')
}

function prettyText(value: unknown) {
  try {
    return JSON.stringify(value, null, 2)
  } catch {
    return String(value || '')
  }
}
</script>

