<script setup>
import { ref, onMounted, onBeforeUnmount, watch } from 'vue'
// maplibre-gl has no default export, only named ones (Map, Popup, ...)
import * as maplibregl from 'maplibre-gl'
import 'maplibre-gl/dist/maplibre-gl.css'
import { useTheme } from '../composables/useTheme'
import { fetchComplaintPoints, fetchBoroughSummary } from '../api'

const props = defineProps({
  filters: { type: Object, required: true },
})

const LIGHT_STYLE = 'https://tiles.openfreemap.org/styles/liberty'
const DARK_STYLE = 'https://tiles.openfreemap.org/styles/dark'
const POINTS_LIMIT = 3000

const MODES = {
  heatmap: {
    label: 'Heatmap',
    desc: "Plots every complaint's lat/long directly, blended into hot zones by density.",
    layers: ['heat'],
  },
  choropleth: {
    label: 'Choropleth',
    desc: 'Shades the five boroughs by total complaints matching the current filters. Click a borough for its count.',
    layers: ['choropleth-fill', 'choropleth-line', 'choropleth-label'],
  },
  clusters: {
    label: 'Clusters',
    desc: 'Nearby complaints merge into a count badge that splits apart as you zoom in.',
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
let boroughsGeoJSON = null
let pointsGeoJSON = { type: 'FeatureCollection', features: [] }

function cssVar(name) {
  return getComputedStyle(document.documentElement).getPropertyValue(name).trim()
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
  if (map.getSource('boroughs')) map.getSource('boroughs').setData(boroughsGeoJSON)
  else map.addSource('boroughs', { type: 'geojson', data: boroughsGeoJSON })

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

  if (!map.getLayer('choropleth-fill')) {
    map.addLayer({
      id: 'choropleth-fill',
      type: 'fill',
      source: 'boroughs',
      paint: {
        'fill-color': [
          'interpolate', ['linear'], ['coalesce', ['get', 'count'], 0],
          0, cssVar('--heat-1'),
          1000, cssVar('--heat-4'),
        ],
        'fill-opacity': 0.55,
      },
      layout: { visibility: 'none' },
    })
    map.addLayer({
      id: 'choropleth-line',
      type: 'line',
      source: 'boroughs',
      paint: { 'line-color': cssVar('--text-h'), 'line-width': 1, 'line-opacity': 0.4 },
      layout: { visibility: 'none' },
    })
    map.addLayer({
      id: 'choropleth-label',
      type: 'symbol',
      source: 'boroughs',
      layout: {
        'text-field': ['format', ['get', 'name'], {}, '\n', {}, ['coalesce', ['get', 'count'], 0], { 'font-scale': 0.85 }],
        'text-size': 13,
        'text-font': ['Noto Sans Bold'],
        visibility: 'none',
      },
      paint: {
        'text-color': cssVar('--text-h'),
        'text-halo-color': cssVar('--surface'),
        'text-halo-width': 1.5,
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
  // getSource()?.setData() is safe even mid-style-load - isStyleLoaded() can
  // stay false well after sources exist and accept updates, so don't gate on it.
  map?.getSource('points')?.setData(pointsGeoJSON)
  map?.getSource('points-clustered')?.setData(pointsGeoJSON)
}

async function loadBoroughSummary() {
  const data = await fetchBoroughSummary(props.filters)
  const counts = Object.fromEntries(data.boroughs.map((b) => [b.borough, b.count]))
  boroughsGeoJSON.features.forEach((f) => {
    f.properties.count = counts[f.properties.name.toUpperCase()] || 0
  })
  map?.getSource('boroughs')?.setData(boroughsGeoJSON)
}

async function loadAll() {
  loading.value = true
  error.value = null
  try {
    await Promise.all([loadPoints(), loadBoroughSummary()])
  } catch (e) {
    error.value = e.message
  } finally {
    loading.value = false
  }
}

onMounted(async () => {
  const res = await fetch('/nyc-boroughs.geojson')
  boroughsGeoJSON = await res.json()

  map = new maplibregl.Map({
    container: mapContainer.value,
    style: styleUrl(),
    center: [-73.98, 40.72],
    zoom: 9.3,
    attributionControl: false,
  })
  map.addControl(new maplibregl.NavigationControl(), 'top-right')
  map.addControl(new maplibregl.AttributionControl({ compact: true }), 'bottom-right')
  if (import.meta.env.DEV) window.__map = map

  map.on('error', (e) => {
    error.value = e.error?.message || 'Map failed to load a resource'
  })

  map.on('load', () => {
    addSourcesAndLayers()
    ready = true
    loadAll()
  })

  map.on('click', 'choropleth-fill', (e) => {
    const p = e.features[0].properties
    new maplibregl.Popup()
      .setLngLat(e.lngLat)
      .setHTML(`<b>${p.name}</b><br>${p.count || 0} complaints`)
      .addTo(map)
  })
  map.on('mouseenter', 'choropleth-fill', () => (map.getCanvas().style.cursor = 'pointer'))
  map.on('mouseleave', 'choropleth-fill', () => (map.getCanvas().style.cursor = ''))
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
  <div class="map-view card">
    <div class="map-header">
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
    </div>
    <p class="mode-desc">{{ MODES[mode].desc }}{{ loading ? ' Loading…' : '' }}</p>
    <p v-if="error" class="error">{{ error }}</p>
    <div ref="mapContainer" class="map-container"></div>
    <p class="map-note">
      Basemap &copy;
      <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener">OpenStreetMap</a>
      contributors, tiles via
      <a href="https://openfreemap.org" target="_blank" rel="noopener">OpenFreeMap</a>.
    </p>
  </div>
</template>

<style scoped>
.map-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 4px;
  flex-wrap: wrap;
}
.map-header h2 {
  margin-bottom: 0;
}
.tabs {
  display: flex;
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
  padding: 6px 12px;
}
.tabs button.active {
  background: var(--accent);
  color: var(--accent-text);
}
.mode-desc {
  font-size: 13px;
  color: var(--text);
  margin: 12px 0;
  line-height: 1.5;
}
.map-container {
  height: 460px;
  border-radius: 8px;
  overflow: hidden;
  border: 1px solid var(--border);
}
.map-note {
  margin-top: 10px;
  font-size: 11.5px;
  color: var(--text);
}
</style>
