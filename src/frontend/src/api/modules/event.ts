import { request } from '../http'
import type { MonitoringEvent } from '../../types/engineering'

export function listEvents(params: { projectId: number; limit?: number }) {
  return request<MonitoringEvent[]>({
    url: `/api/em/projects/${params.projectId}/events`,
    method: 'GET',
    params: { limit: params.limit }
  })
}
