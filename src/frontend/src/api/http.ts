import axios, { AxiosRequestConfig } from 'axios'
import { ElMessage } from 'element-plus'
import type { ApiEnvelope } from '../types/api'
import { platformConfig } from '../config/platform'

/** Leave baseURL empty when using the Vite proxy in development; configure VITE_API_BASE_URL for production builds. */
const apiBaseURL = import.meta.env.DEV ? '' : platformConfig.apiBaseUrl

const service = axios.create({
  baseURL: apiBaseURL,
  timeout: 30000
})

service.interceptors.response.use(
  response => response,
  error => {
    const body = error?.response?.data
    const serverMsg = typeof body === 'object' && body
      ? (body.message || body.msg)
      : undefined
    ElMessage.error(serverMsg || error?.message || 'API request failed')
    return Promise.reject(error)
  }
)

export async function request<T>(config: AxiosRequestConfig): Promise<T> {
  const res = await service.request<ApiEnvelope<T> | T>(config)
  const body = res.data as ApiEnvelope<T>
  if (body && typeof body === 'object' && ('data' in body || 'success' in body || 'code' in body)) {
    if (body.code && body.code !== 200) throw new Error(body.message || 'Business API returned an error')
    if (body.success === false) throw new Error(body.message || 'Business API returned an error')
    return (body.data ?? body.rows ?? body) as T
  }
  return res.data as T
}

export async function rawRequest<T>(config: AxiosRequestConfig): Promise<T> {
  const res = await service.request<T>(config)
  return res.data
}


