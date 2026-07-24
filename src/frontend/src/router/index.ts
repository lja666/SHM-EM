import { createRouter, createWebHashHistory, RouteRecordRaw } from 'vue-router'
import AppLayout from '../layout/AppLayout.vue'
import projectWorkflowRouter from './modules/projectWorkflow'
import type { AppRouteRecordRaw } from './types'

export const menuRoutes: AppRouteRecordRaw[] = [
  projectWorkflowRouter
].sort((a, b) => Number(a.meta?.rank || 99) - Number(b.meta?.rank || 99))

const routes: RouteRecordRaw[] = [
  {
    path: '/',
    component: AppLayout,
    redirect: '/projects',
    children: menuRoutes.flatMap(route => route.children || [])
  },
  { path: '/:pathMatch(.*)*', redirect: '/projects' }
]

const router = createRouter({
  history: createWebHashHistory(),
  routes
})

export default router

