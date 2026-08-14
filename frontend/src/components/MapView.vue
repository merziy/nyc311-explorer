<script setup>
import { ref, onMounted, onBeforeUnmount, watch } from 'vue'
import * as maplibregl from 'maplibre-gl' // see CLAUDE.md, "Map view"
import 'maplibre-gl/dist/maplibre-gl.css'

// see CLAUDE.md, "Map view" - MapLibre derives its worker URL from
// import.meta.url at runtime, relative to wherever its own bundled code is
// served from; Vite can't statically detect that to bundle the file (nor its
// own further static import of a sibling "shared" chunk), so the guessed URL
// 404s (silently falls back to index.html) unless set explicitly. Both files
// are copied verbatim into public/ by scripts/copy-maplibre-worker.mjs so
// their relative import of each other still resolves.
maplibregl.setWorkerUrl(`${import.meta.env.BASE_URL}maplibre-gl-worker.mjs`)
import { useTheme } from '../composables/useTheme'
import { fetchComplaintPoints, fetchComplaint } from '../api'
import AskBox from './AskBox.vue'
import FilterBar from './FilterBar.vue'
import ThemeToggle from './ThemeToggle.vue'
import TopComplaintTypes from './TopComplaintTypes.vue'
import ComplaintsTable from './ComplaintsTable.vue'

const props = defineProps({
  filters: { type: Object, required: true },
})
const emit = defineEmits(['filters-change'])

const leftPanel = ref(null)

const LIGHT_STYLE = 'https://tiles.openfreemap.org/styles/liberty'
const DARK_STYLE = 'https://tiles.openfreemap.org/styles/dark'
const POINTS_LIMIT = 3000

const MODES = {
  heatmap: {
    label: 'Heatmap',
    desc: "Plots every complaint's lat/long directly, blended into hot zones by density.",
    layers: ['heat'],
  },
  clusters: {
    label: 'Clusters',
    desc: 'Nearby complaints merge into a count badge that splits apart as you zoom in. Click an individual point for its details.',
    layers: ['cluster-circles', 'cluster-count', 'unclustered-points'],
  },
}
const ALL_LAYERS = Object.values(MODES).flatMap((m) => m.layers)

const { theme } = useTheme()
const mapContainer = ref(null)
const mode = ref('heatmap')
const loading = ref(false)
const error = ref(null)

let map = null
let ready = false
let pointsGeoJSON = { type: 'FeatureCollection', features: [] }

function cssVar(name) {
  return getComputedStyle(document.documentElement).getPropertyValue(name).trim()
}

function escapeHtml(value) {
  const div = document.createElement('div')
  div.textContent = value ?? ''
  return div.innerHTML
}

function styleUrl() {
  return theme.value === 'dark' ? DARK_STYLE : LIGHT_STYLE
}

function applyModeVisibility() {
  ALL_LAYERS.forEach((id) => {
    if (map.getLayer(id)) map.setLayoutProperty(id, 'visibility', 'none')
  })
  MODES[mode.value].layers.forEach((id) => {
    if (map.getLayer(id)) map.setLayoutProperty(id, 'visibility', 'visible')
  })
}

function addSourcesAndLayers() {
  if (map.getSource('points')) map.getSource('points').setData(pointsGeoJSON)
  else map.addSource('points', { type: 'geojson', data: pointsGeoJSON })

  if (map.getSource('points-clustered')) map.getSource('points-clustered').setData(pointsGeoJSON)
  else {
    map.addSource('points-clustered', {
      type: 'geojson',
      data: pointsGeoJSON,
      cluster: true,
      clusterRadius: 45,
      clusterMaxZoom: 14,
    })
  }

  if (!map.getLayer('heat')) {
    map.addLayer({
      id: 'heat',
      type: 'heatmap',
      source: 'points',
      paint: {
        'heatmap-weight': 0.6,
        'heatmap-intensity': ['interpolate', ['linear'], ['zoom'], 9, 1, 14, 2.5],
        'heatmap-radius': ['interpolate', ['linear'], ['zoom'], 9, 14, 14, 34],
        'heatmap-opacity': 0.8,
        'heatmap-color': [
          'interpolate', ['linear'], ['heatmap-density'],
          0, 'rgba(0,0,0,0)',
          0.2, cssVar('--heat-1'),
          0.5, cssVar('--heat-2'),
          0.75, cssVar('--heat-3'),
          1, cssVar('--heat-4'),
        ],
      },
    })
  }

  if (!map.getLayer('cluster-circles')) {
    map.addLayer({
      id: 'cluster-circles',
      type: 'circle',
      source: 'points-clustered',
      filter: ['has', 'point_count'],
      paint: {
        'circle-radius': ['interpolate', ['linear'], ['get', 'point_count'], 1, 12, 200, 28],
        'circle-color': cssVar('--heat-2'),
        'circle-opacity': 0.85,
        'circle-stroke-width': 1.5,
        'circle-stroke-color': cssVar('--surface'),
      },
      layout: { visibility: 'none' },
    })
    map.addLayer({
      id: 'cluster-count',
      type: 'symbol',
      source: 'points-clustered',
      filter: ['has', 'point_count'],
      layout: {
        'text-field': '{point_count_abbreviated}',
        'text-size': 11,
        'text-font': ['Noto Sans Bold'],
        visibility: 'none',
      },
      paint: { 'text-color': '#ffffff' },
    })
    map.addLayer({
      id: 'unclustered-points',
      type: 'circle',
      source: 'points-clustered',
      filter: ['!', ['has', 'point_count']],
      paint: {
        'circle-radius': 5,
        'circle-color': cssVar('--heat-1'),
        'circle-opacity': 0.85,
        'circle-stroke-width': 1,
        'circle-stroke-color': cssVar('--surface'),
      },
      layout: { visibility: 'none' },
    })
  }

  applyModeVisibility()
}

async function loadPoints() {
  const data = await fetchComplaintPoints(props.filters, POINTS_LIMIT)
  pointsGeoJSON = {
    type: 'FeatureCollection',
    features: data.results.map((p) => ({
      type: 'Feature',
      properties: { unique_key: p.unique_key, complaint_type: p.complaint_type },
      geometry: { type: 'Point', coordinates: [p.longitude, p.latitude] },
    })),
  }
  // don't gate on map.isStyleLoaded() here - see CLAUDE.md, "Map view"
  map?.getSource('points')?.setData(pointsGeoJSON)
  map?.getSource('points-clustered')?.setData(pointsGeoJSON)
}

async function loadAll() {
  loading.value = true
  error.value = null
  try {
    await loadPoints()
  } catch (e) {
    error.value = e.message
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  map = new maplibregl.Map({
    container: mapContainer.value,
    style: styleUrl(),
    center: [-73.98, 40.72],
    zoom: 9.3,
    attributionControl: false,
  })
  map.addControl(new maplibregl.NavigationControl(), 'bottom-right')
  if (import.meta.env.DEV) window.__map = map

  map.on('error', (e) => {
    error.value = e.error?.message || 'Map failed to load a resource'
  })

  map.on('load', () => {
    addSourcesAndLayers()
    ready = true
    loadAll()
  })

  map.on('click', 'unclustered-points', async (e) => {
    const uniqueKey = e.features[0].properties.unique_key
    const popup = new maplibregl.Popup().setLngLat(e.lngLat).setHTML('Loading…').addTo(map)
    try {
      const c = await fetchComplaint(uniqueKey)
      const body = c.resolution_description
        || (c.status === 'Closed' ? 'No resolution notes recorded.' : 'Still open — no resolution notes yet.')
      popup.setHTML(`
        <div style="font: 13px system-ui, sans-serif; max-width: 260px; line-height: 1.5;">
          <div style="font-weight: 600; margin-bottom: 2px;">
            ${escapeHtml(c.complaint_type)}${c.descriptor ? ' — ' + escapeHtml(c.descriptor) : ''}
          </div>
          <div>${escapeHtml(body)}</div>
          <div style="margin-top: 6px; color: var(--text); font-size: 12px;">
            ${escapeHtml(c.borough || '')} &middot; ${escapeHtml(c.status || '')}<br>
            ${c.created_date ? escapeHtml(c.created_date.slice(0, 10)) : ''}
          </div>
        </div>
      `)
    } catch {
      popup.setHTML('Failed to load complaint details')
    }
  })
  map.on('mouseenter', 'unclustered-points', () => (map.getCanvas().style.cursor = 'pointer'))
  map.on('mouseleave', 'unclustered-points', () => (map.getCanvas().style.cursor = ''))
})

onBeforeUnmount(() => {
  map?.remove()
})

watch(mode, () => {
  applyModeVisibility()
})

watch(
  () => props.filters,
  () => {
    if (ready) loadAll()
  },
  { deep: true },
)

watch(theme, () => {
  if (!map) return
  map.setStyle(styleUrl())
  map.once('style.load', addSourcesAndLayers)
})
</script>

<template>
  <div class="map-shell">
    <div ref="mapContainer" class="map-canvas"></div>

    <div ref="leftPanel" class="overlay overlay-left">
      <div class="app-title">
        <h1>NYC 311 Explorer</h1>
        <ThemeToggle />
      </div>
      <AskBox />
      <FilterBar @change="emit('filters-change', $event)" />
      <TopComplaintTypes :filters="filters" />
      <ComplaintsTable :filters="filters" :scroll-container="leftPanel" />
    </div>

    <div class="overlay overlay-right card">
      <h2>Map view</h2>
      <div class="tabs">
        <button
          v-for="(m, key) in MODES"
          :key="key"
          type="button"
          :class="{ active: mode === key }"
          @click="mode = key"
        >
          {{ m.label }}
        </button>
      </div>
      <p class="mode-desc">{{ MODES[mode].desc }}{{ loading ? ' Loading…' : '' }}</p>
      <p v-if="error" class="error">{{ error }}</p>

      <div class="legend">
        <div v-if="mode === 'heatmap'" class="legend-scale">
          <span>Fewer</span>
          <div class="bar"></div>
          <span>More</span>
        </div>
        <div v-else class="type-legend">
          <span><i class="dot dot-cluster"></i>Cluster (zoom in to split)</span>
          <span><i class="dot dot-single"></i>Individual complaint (click for details)</span>
        </div>
      </div>

      <p class="map-note">
        Basemap &copy;
        <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener">OpenStreetMap</a>
        contributors, tiles via
        <a href="https://openfreemap.org" target="_blank" rel="noopener">OpenFreeMap</a>.
      </p>
    </div>
  </div>
</template>

<style scoped>
.map-shell {
  position: fixed;
  inset: 0;
}
.map-canvas {
  position: absolute;
  inset: 0;
}

.app-title {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}
.app-title h1 {
  font-size: 20px;
  letter-spacing: -0.3px;
}

.overlay {
  position: absolute;
  top: 16px;
  z-index: 5;
  display: flex;
  flex-direction: column;
  gap: 12px;
  max-height: calc(100% - 32px);
  overflow-y: auto;
}
.overlay-left {
  left: 16px;
  width: 400px;
  max-width: calc(100% - 32px);
}
.overlay-right {
  right: 16px;
  width: 260px;
  max-width: calc(100% - 32px);
  padding: 16px;
}

.overlay-right h2 {
  margin-bottom: 10px;
}
.tabs {
  display: flex;
  flex-direction: column;
  background: var(--bg);
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 3px;
  gap: 3px;
}
.tabs button {
  background: transparent;
  color: var(--text);
  font-size: 13px;
  font-weight: 550;
  padding: 7px 10px;
  text-align: left;
}
.tabs button.active {
  background: var(--accent);
  color: var(--accent-text);
}
.mode-desc {
  font-size: 12.5px;
  color: var(--text);
  margin: 10px 0 0;
  line-height: 1.5;
}
.legend {
  margin-top: 12px;
  padding-top: 10px;
  border-top: 1px solid var(--border);
}
.legend-scale {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 11.5px;
  color: var(--text);
}
.legend-scale .bar {
  flex: 1;
  height: 7px;
  border-radius: 4px;
  background: linear-gradient(90deg, var(--heat-1), var(--heat-2), var(--heat-3), var(--heat-4));
}
.type-legend {
  display: flex;
  flex-direction: column;
  gap: 6px;
  font-size: 12px;
  color: var(--text);
}
.type-legend span {
  display: flex;
  align-items: center;
  gap: 6px;
}
.dot {
  width: 9px;
  height: 9px;
  border-radius: 50%;
  display: inline-block;
  flex-shrink: 0;
}
.dot-cluster {
  background: var(--heat-2);
}
.dot-single {
  background: var(--heat-1);
}
.map-note {
  margin-top: 12px;
  padding-top: 10px;
  border-top: 1px solid var(--border);
  font-size: 11px;
  color: var(--text);
}

@media (max-width: 760px) {
  .map-shell {
    position: static;
    display: flex;
    flex-direction: column;
  }
  .map-canvas {
    position: relative;
    height: 420px;
  }
  .overlay {
    position: static;
    width: auto;
    max-height: none;
    overflow-y: visible;
  }
  .overlay-right {
    border-radius: 0;
    border-left: none;
    border-right: none;
    border-bottom: none;
  }
}
</style>
