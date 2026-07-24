import { request } from '../http'

export function listResponseNotifications(params?: { projectId?: number; status?: string; limit?: number }) {
  return request<Record<string, unknown>[]>({ url: '/api/em/notification-tasks', method: 'GET', params })
}

export function listNotificationSubscribers(params?: { projectId?: number; channelType?: string; enabled?: number }) {
  return request<Record<string, unknown>[]>({ url: '/api/em/notification-subscribers', method: 'GET', params })
}

export function listNotificationTransitions(params?: { projectId?: number; transitionType?: string; deliveryStatus?: string; limit?: number }) {
  return request<Record<string, unknown>[]>({ url: '/api/em/notification-state-transitions', method: 'GET', params })
}

export function listNotificationDeliveryLogs(params?: { projectId?: number; taskId?: number; limit?: number }) {
  return request<Record<string, unknown>[]>({ url: '/api/em/notification-delivery-logs', method: 'GET', params })
}

export function listEventResponseWorkflows(params?: { projectId?: number }) {
  return request<Record<string, unknown>[]>({ url: '/api/em/event-response-workflows', method: 'GET', params })
}
