import { copyFileSync, mkdirSync } from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

// maplibre-gl's worker imports a sibling chunk via a static relative import
// ("./maplibre-gl-shared.mjs"), so both files must be copied to public/
// together, under their original names, for that import to resolve — see
// CLAUDE.md, "Map view".
const root = path.dirname(fileURLToPath(import.meta.url))
const src = path.join(root, '..', 'node_modules', 'maplibre-gl', 'dist')
const dest = path.join(root, '..', 'public')

mkdirSync(dest, { recursive: true })
for (const file of ['maplibre-gl-worker.mjs', 'maplibre-gl-shared.mjs']) {
  copyFileSync(path.join(src, file), path.join(dest, file))
}
