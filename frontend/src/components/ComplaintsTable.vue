<script setup>
import { ref, watch, onMounted, onUnmounted } from 'vue'
import { fetchComplaints } from '../api'

const props = defineProps({
  filters: { type: Object, required: true },
})

const PAGE_SIZE = 100
const NEAR_BOTTOM_THRESHOLD = 300

const results = ref([])
const total = ref(0)
const offset = ref(0)
const loading = ref(false)
const error = ref(null)
const scrollDepth = ref(0)

async function loadPage(reset) {
  if (loading.value) return
  if (!reset && results.value.length > 0 && results.value.length >= total.value) return

  loading.value = true
  error.value = null
  try {
    const requestOffset = reset ? 0 : offset.value
    const data = await fetchComplaints(props.filters, PAGE_SIZE, requestOffset)
    results.value = reset ? data.results : results.value.concat(data.results)
    offset.value = requestOffset + data.results.length
    total.value = data.total
  } catch (e) {
    error.value = e.message
  } finally {
    loading.value = false
  }
}

function onScroll() {
  scrollDepth.value = window.scrollY + window.innerHeight
}

// Watches scrollDepth directly (not a derived near-bottom boolean): that
// boolean can stay true across several consecutive scroll events whenever
// the user stays pinned near the bottom, and watch() only fires on a value
// actually changing - so gating on the boolean would silently drop every
// load after the first threshold crossing.
watch(scrollDepth, (depth) => {
  const nearBottom = document.documentElement.scrollHeight - depth < NEAR_BOTTOM_THRESHOLD
  if (nearBottom) loadPage(false)
})

watch(
  () => props.filters,
  () => loadPage(true),
  { deep: true },
)

onMounted(() => {
  window.addEventListener('scroll', onScroll)
  loadPage(true)
})

onUnmounted(() => {
  window.removeEventListener('scroll', onScroll)
})
</script>

<template>
  <div class="complaints-table">
    <p v-if="error" class="error">{{ error }}</p>
    <table>
      <thead>
        <tr>
          <th>Date</th>
          <th>Type</th>
          <th>Borough</th>
          <th>Status</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="c in results" :key="c.unique_key">
          <td>{{ c.created_date?.slice(0, 10) }}</td>
          <td>{{ c.complaint_type }}</td>
          <td>{{ c.borough || '—' }}</td>
          <td>{{ c.status || '—' }}</td>
        </tr>
      </tbody>
    </table>
    <p v-if="loading">Loading…</p>
    <p v-if="!loading && results.length > 0 && results.length >= total">
      Showing all {{ total }} results.
    </p>
  </div>
</template>
