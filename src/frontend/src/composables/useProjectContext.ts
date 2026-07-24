import { computed, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAppStore } from '../stores/app'

export function useProjectContext() {
  const route = useRoute()
  const router = useRouter()
  const app = useAppStore()
  const projectId = computed(() => Number(route.params.projectId || app.currentProjectId || 0))

  watch(projectId, id => {
    if (!id) {
      router.replace('/projects')
      return
    }
    app.setCurrentProject(id)
  }, { immediate: true })

  function projectPath(target: string) {
    const id = projectId.value || app.currentProjectId
    return id ? `/projects/${id}/${target.replace(/^\/+/, '')}` : '/projects'
  }

  function goProject(target: string) {
    const path = projectPath(target)
    if (path !== route.path) router.push(path)
  }

  function switchProject(nextProjectId: number) {
    const path = scopedProjectPath(route.path, nextProjectId)
    if (path !== route.path) router.push(path)
  }

  return {
    projectId,
    projectPath,
    goProject,
    switchProject,
    app
  }
}

export function scopedProjectPath(currentPath: string, nextProjectId: number) {
  if (!nextProjectId) return '/projects'
  if (!/^\/projects\/[^/]+/.test(currentPath)) return `/projects/${nextProjectId}/overview`

  const suffix = currentPath.replace(/^\/projects\/[^/]+/, '') || '/overview'
  if (/^\/events\/[^/]+/.test(suffix)) return `/projects/${nextProjectId}/events`
  if (/^\/response\/workflows\/[^/]+/.test(suffix)) return `/projects/${nextProjectId}/response/workflows`
  if (/^\/rules\/[^/]+\/replay/.test(suffix)) return `/projects/${nextProjectId}/rules`
  return `/projects/${nextProjectId}${suffix}`
}
