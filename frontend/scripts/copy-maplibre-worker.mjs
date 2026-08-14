import { copyFileSync, mkdirSync } from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

// see CLAUDE.md, "Map view" - both files must keep their original names
const root = path.dirname(fileURLToPath(import.meta.url))
const src = path.join(root, '..', 'node_modules', 'maplibre-gl', 'dist')
const dest = path.join(root, '..', 'public')

mkdirSync(dest, { recursive: true })
for (const file of ['maplibre-gl-worker.mjs', 'maplibre-gl-shared.mjs']) {
  copyFileSync(path.join(src, file), path.join(dest, file))
}
