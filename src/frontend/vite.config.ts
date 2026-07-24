import { defineConfig, loadEnv } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  const target = env.VITE_API_BASE_URL || 'http://localhost:5101'
  return {
    plugins: [vue()],
    server: {
      port: 5173,
      proxy: {
        '/api': {
          target,
          changeOrigin: true
        }
      }
    },
    build: {
      rollupOptions: {
        output: {
          manualChunks(id) {
            const normalizedId = id.replace(/\\/g, '/')
            if (!normalizedId.includes('node_modules')) return undefined
            if (normalizedId.includes('/@element-plus/icons-vue/')) {
              return 'vendor-element-icons'
            }
            if (normalizedId.includes('/element-plus/')) {
              return 'vendor-element'
            }
            if (normalizedId.includes('/zrender/')) {
              return 'vendor-zrender'
            }
            if (normalizedId.includes('/echarts/')) {
              return 'vendor-echarts'
            }
            if (normalizedId.includes('/vue/') || normalizedId.includes('/vue-router/') || normalizedId.includes('/pinia/') || normalizedId.includes('/@vueuse/')) {
              return 'vendor-vue'
            }
            if (normalizedId.includes('/axios/')) {
              return 'vendor-http'
            }
            return 'vendor-runtime'
          }
        }
      }
    }
  }
})
