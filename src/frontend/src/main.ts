import { createApp } from 'vue'
import { createPinia } from 'pinia'
import {
  ElAlert,
  ElAside,
  ElBreadcrumb,
  ElBreadcrumbItem,
  ElButton,
  ElCheckbox,
  ElContainer,
  ElDatePicker,
  ElDescriptions,
  ElDescriptionsItem,
  ElDialog,
  ElDrawer,
  ElEmpty,
  ElHeader,
  ElIcon,
  ElInput,
  ElInputNumber,
  ElLink,
  ElLoading,
  ElMain,
  ElMenu,
  ElMenuItem,
  ElOption,
  ElProgress,
  ElRadioButton,
  ElRadioGroup,
  ElScrollbar,
  ElSegmented,
  ElSelect,
  ElTabPane,
  ElTable,
  ElTableColumn,
  ElTabs,
  ElTag,
  ElTree
} from 'element-plus'
import { Bell, Connection, Cpu, DataBoard, FolderChecked, Grid, Setting, TrendCharts } from '@element-plus/icons-vue'
import 'element-plus/dist/index.css'
import './style/index.css'
import App from './App.vue'
import router from './router'

const app = createApp(App)
const elementComponents = [
  ElAlert,
  ElAside,
  ElBreadcrumb,
  ElBreadcrumbItem,
  ElButton,
  ElCheckbox,
  ElContainer,
  ElDatePicker,
  ElDescriptions,
  ElDescriptionsItem,
  ElDialog,
  ElDrawer,
  ElEmpty,
  ElHeader,
  ElIcon,
  ElInput,
  ElInputNumber,
  ElLink,
  ElMain,
  ElMenu,
  ElMenuItem,
  ElOption,
  ElProgress,
  ElRadioButton,
  ElRadioGroup,
  ElScrollbar,
  ElSegmented,
  ElSelect,
  ElTabPane,
  ElTable,
  ElTableColumn,
  ElTabs,
  ElTag,
  ElTree
]
for (const component of elementComponents) {
  app.use(component)
}
app.use(ElLoading)
const dynamicIcons = { Bell, Connection, Cpu, DataBoard, FolderChecked, Grid, Setting, TrendCharts }
for (const [key, component] of Object.entries(dynamicIcons)) {
  app.component(key, component)
}
app.use(createPinia())
app.use(router)
app.mount('#app')
