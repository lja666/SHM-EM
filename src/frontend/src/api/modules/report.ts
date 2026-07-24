import { request } from '../http'
import type { ReportItem } from '../../types/engineering'

export function listReports(params?: { projectId?: number; limit?: number }) {
  return request<ReportItem[]>({ url: '/api/em/reports', method: 'GET', params })
}

export function reportDownloadUrl(id: number | string, format: 'docx' | 'pdf') {
  return `/api/em/reports/${id}/download?format=${encodeURIComponent(format)}`
}
