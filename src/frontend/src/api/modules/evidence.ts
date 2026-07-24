import { request } from '../http'
import type { EvidenceItem } from '../../types/engineering'

export function listEvidence(params?: { projectId?: number; limit?: number }) {
  return request<EvidenceItem[]>({ url: '/api/em/evidence', method: 'GET', params })
}
