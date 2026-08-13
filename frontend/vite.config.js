import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// https://vite.dev/config/
export default defineConfig({
  plugins: [vue()],
  optimizeDeps: {
    // maplibre-gl spawns a Web Worker for tile/GeoJSON processing via a
    // relative new URL(..., import.meta.url); esbuild's dev-time dependency
    // pre-bundling doesn't preserve that as a separate fetchable chunk,
    // so the worker 404s and every GeoJSON-sourced layer silently never
    // renders. Excluding it from pre-bundling serves it as native ESM instead,
    // where the relative worker URL resolves correctly.
    exclude: ['maplibre-gl'],
  },
})
