import { request } from '../http'
import type { ProjectContext, ProjectFutureState, ProjectObjectTree, ProjectOverview } from '../../types/engineering'

export function getProjectOverview() {
  return request<ProjectOverview>({ url: '/api/em/projects/overview', method: 'GET' })
}

export function getProjectContext(id: number) {
  return request<ProjectContext>({ url: `/api/em/projects/${id}/context`, method: 'GET' })
}

export function getProjectObjectTree(id: number) {
  return request<ProjectObjectTree>({ url: `/api/em/projects/${id}/object-tree`, method: 'GET' })
}

export function getProjectFutureState(id: number, params?: {
  batchId?: number
  horizonMinutes?: number
  executionMode?: 'OPERATIONAL' | 'REPLAY' | 'REPRODUCTION'
  referenceTime?: string
}) {
  return request<ProjectFutureState>({ url: `/api/em/projects/${id}/future-state`, method: 'GET', params })
}
