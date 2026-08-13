import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// https://vite.dev/config/
export default defineConfig({
  plugins: [vue()],
  optimizeDeps: {
    // see CLAUDE.md, "Map view" - avoids a silent worker 404 in dev
    exclude: ['maplibre-gl'],
  },
})
