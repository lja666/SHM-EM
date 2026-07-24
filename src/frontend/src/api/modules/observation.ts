import { request } from '../http'
import type { LowFrequencyObservation, ObservationQuery } from '../../types/engineering'

export function listLowFrequencyObservations(params: ObservationQuery) {
  return request<LowFrequencyObservation[]>({ url: '/api/em/observations/low-frequency/query', method: 'POST', data: params })
}
