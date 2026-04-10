import { fileURLToPath, URL } from 'node:url'
import { defineConfig, loadEnv } from 'vite'
import vue from '@vitejs/plugin-vue'

// https://vitejs.dev/config/
export default defineConfig(({ mode }) => {
  // const env = loadEnv(mode, process.cwd(), '')

  // // Keep dev-server config separate from API env vars.
  // const host = env.VITE_DEV_HOST || '0.0.0.0'
  // const port = Number(env.VITE_DEV_PORT) || 5173

  return {
    server: {
      host: '0.0.0.0',
      port: 5001,
    },
    plugins: [vue()],
    resolve: {
      alias: {
        '@': fileURLToPath(new URL('./src', import.meta.url)),
      },
    },
  }
})
