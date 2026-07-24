import { request } from '../http'
import type { EventRule, RuleEvaluationResult } from '../../types/engineering'

export interface RuleEvaluationPayload {
  ruleId?: number
  projectId?: number
  stationIds?: number[]
  instrumentIds?: number[]
  instrumentType?: string
  metricCode?: string
  startTime?: string
  endTime?: string
  runMode?: string
  customRule?: boolean
  eventLevel?: string
  operator?: string
  thresholdValue?: number
  thresholds?: Array<{ level: string; thresholdValue?: number }>
  thresholdUnit?: string
  inputSource?: 'OBSERVATION' | 'PREDICTION' | string
  predictionBatchId?: number
  predictionBatchCode?: string
  predictionModelCode?: string
  predictionTargetType?: string
  predictionFeatureCode?: string
  forecastHorizonMinutes?: number
  minimumConsecutiveSteps?: number
  seriesQualityFilter?: string
  predictionExecutionMode?: 'OPERATIONAL' | 'REPLAY' | string
}

export function listEventRules(params: { projectId: number; limit?: number }) {
  return request<EventRule[]>({
    url: `/api/em/projects/${params.projectId}/rules`,
    method: 'GET',
    params: { limit: params.limit }
  })
}

export function evaluateEventRule(data: RuleEvaluationPayload) {
  if (!data.projectId) throw new Error('projectId is required for rule evaluation')
  const suffix = data.ruleId ? `/${data.ruleId}/evaluate` : '/evaluate'
  return request<RuleEvaluationResult>(
    { url: `/api/em/projects/${data.projectId}/rules${suffix}`, method: 'POST', data }
  )
}

export function executeEventRule(data: RuleEvaluationPayload) {
  if (!data.projectId) throw new Error('projectId is required for rule execution')
  const suffix = data.ruleId ? `/${data.ruleId}/execute` : '/execute'
  return request<RuleEvaluationResult>(
    { url: `/api/em/projects/${data.projectId}/rules${suffix}`, method: 'POST', data }
  )
}

