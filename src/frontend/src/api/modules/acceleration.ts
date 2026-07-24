import { request } from '../http'
import type { AccelerationWaveform, ObservationQuery } from '../../types/engineering'

export function listAccelerationWaveforms(params: ObservationQuery) {
  return request<AccelerationWaveform[]>({ url: '/api/em/acceleration/waveform', method: 'POST', data: params })
}
