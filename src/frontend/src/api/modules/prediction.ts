import { request } from '../http'
import type {
  PredictionBatch,
  PredictionDisplay,
  PredictionFeatureMapping,
  PredictionBatchDetail,
  PredictionExecutionGate,
  MetricSeriesPoint,
  EventPredictionTrace,
  PredictionQuery
} from '../../types/engineering'

export function listPredictionBatches(params?: PredictionQuery) {
  return request<PredictionBatch[]>({ url: '/api/em/predictions/batches', method: 'GET', params })
}

export function listPredictionFeatures(params?: PredictionQuery) {
  return request<PredictionFeatureMapping[]>({ url: '/api/em/predictions/features', method: 'GET', params })
}

export function listLatestPredictions(params?: PredictionQuery) {
  return request<PredictionDisplay[]>({ url: '/api/em/predictions/latest', method: 'GET', params })
}

export function getPredictionBatchDetail(batchId: number) {
  return request<PredictionBatchDetail>({ url: `/api/em/predictions/batches/${batchId}`, method: 'GET' })
}

export function getPredictionExecutionGate(batchId: number, params?: {
  mode?: 'OPERATIONAL' | 'REPLAY'
  referenceTime?: string
}) {
  return request<PredictionExecutionGate>({ url: `/api/em/predictions/batches/${batchId}/execution-gate`, method: 'GET', params })
}

export function listUnifiedSeries(params: PredictionQuery) {
  return request<MetricSeriesPoint[]>({ url: '/api/em/predictions/series', method: 'GET', params })
}

export function getPredictionEventTrace(eventId: number) {
  return request<EventPredictionTrace>({ url: `/api/em/predictions/events/${eventId}/trace`, method: 'GET' })
}
