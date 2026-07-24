import type { AppRouteRecordRaw } from '../types'

const projectWorkflowRouter: AppRouteRecordRaw = {
  path: '/projects',
  redirect: '/projects',
  meta: { title: 'Engineering Monitoring Workflow', icon: 'Menu', rank: 1 },
  children: [
    { path: '/projects', name: 'ProjectCatalog', component: () => import('../../views/projects/ProjectCatalog.vue'), meta: { title: 'Project Overview', icon: 'Grid', group: 'Project Overview', groupOrder: 1 } },
    { path: '/projects/:projectId/overview', name: 'ProjectWorkspace', component: () => import('../../views/projects/ProjectWorkspace.vue'), meta: { title: 'Project Workspace', icon: 'Monitor', group: 'Current Project', groupOrder: 2 } },
    { path: '/projects/:projectId/topology', name: 'ProjectTopology', component: () => import('../../views/projects/ProjectTopology.vue'), meta: { title: 'Object Topology', icon: 'Share', group: 'Engineering Model', groupOrder: 3 } },
    { path: '/projects/:projectId/data', redirect: to => `/projects/${to.params.projectId}/data/low-frequency`, meta: { title: 'Observation Data', icon: 'DataLine', showLink: false } },
    { path: '/projects/:projectId/data/low-frequency', name: 'ProjectLowFrequency', component: () => import('../../views/workflow/LowFrequencyBrowse.vue'), meta: { title: 'Observation & Prediction', icon: 'DataLine', group: 'Prediction Analysis', groupOrder: 4 } },
    { path: '/projects/:projectId/predictions', name: 'ProjectPredictionRuns', component: () => import('../../views/workflow/PredictionRuns.vue'), meta: { title: 'Prediction Runs', icon: 'Coin', group: 'Prediction Analysis', groupOrder: 4 } },
    { path: '/projects/:projectId/events', name: 'ProjectEvents', component: () => import('../../views/workflow/EventCenter.vue'), meta: { title: 'Rules & Events', icon: 'Warning', group: 'Rules and Events', groupOrder: 5 } },
    { path: '/projects/:projectId/response/workflows', name: 'ProjectResponseWorkflows', component: () => import('../../views/workflow/ResponseWorkflow.vue'), meta: { title: 'Response and Evidence', icon: 'Operation', group: 'Response Evidence', groupOrder: 6 } },
    { path: '/projects/:projectId/response/workflows/:workflowId', name: 'ProjectResponseWorkflowDetail', component: () => import('../../views/workflow/ResponseWorkflow.vue'), meta: { title: 'Response Workflow Detail', icon: 'Operation', showLink: false } },
    { path: '/projects/:projectId/settings', name: 'ProjectSettings', component: () => import('../../views/projects/ProjectSettings.vue'), meta: { title: 'Project Settings', icon: 'Setting', group: 'Project Settings', groupOrder: 8 } }
  ]
}

export default projectWorkflowRouter


