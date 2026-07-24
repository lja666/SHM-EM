import { defineStore } from 'pinia'
import { platformConfig } from '../config/platform'

export const useAppStore = defineStore('app', {
  state: () => ({
    project: platformConfig.defaultProject,
    currentProjectId: Number(localStorage.getItem('shm-em-current-project-id') || 0),
    collapsed: false,
    refreshKey: 0
  }),
  actions: {
    setProject(project: string) {
      this.project = project || this.project
    },
    setCurrentProject(projectId: number, projectName?: string) {
      if (projectId > 0) {
        this.currentProjectId = projectId
        localStorage.setItem('shm-em-current-project-id', String(projectId))
      }
      if (projectName) this.setProject(projectName)
    },
    toggleCollapsed() {
      this.collapsed = !this.collapsed
    },
    refreshCurrentView() {
      this.refreshKey += 1
    }
  }
})

