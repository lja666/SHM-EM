export interface ApiEnvelope<T> {
  code?: number
  success?: boolean
  message?: string
  data?: T
  rows?: T
  total?: number
}
