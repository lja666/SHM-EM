import type { RouteRecordRaw } from 'vue-router'

export interface AppRouteMeta {
  title: string
  icon?: string
  group?: string
  groupOrder?: number
  rank?: number
  showLink?: boolean
  showParent?: boolean
  keepAlive?: boolean
  activePath?: string
}

export type AppRouteRecordRaw = RouteRecordRaw & {
  meta?: AppRouteMeta
  children?: AppRouteRecordRaw[]
}
