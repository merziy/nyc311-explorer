<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import { fetchSummary } from '../api'

const props = defineProps({
  filters: { type: Object, required: true },
})

const complaintTypes = ref([])
const loading = ref(false)
const error = ref(null)

const maxCount = computed(() => Math.max(1, ...complaintTypes.value.map((ct) => ct.count)))

async function load() {
  loading.value = true
  error.value = null
  try {
    const data = await fetchSummary(props.filters, 10)
    complaintTypes.value = data.complaint_types
  } catch (e) {
    error.value = e.message
  } finally {
    loading.value = false
  }
}

watch(() => props.filters, load, { deep: true })
onMounted(load)
</script>

<template>
  <div class="top-types card">
    <h2>Top complaint types</h2>
    <p v-if="error" class="error">{{ error }}</p>
    <ol>
      <li v-for="ct in complaintTypes" :key="ct.complaint_type">
        <div class="bar-row">
          <span class="label">{{ ct.complaint_type }}</span>
          <span class="count">{{ ct.count }}</span>
        </div>
        <div class="bar-track">
          <div class="bar-fill" :style="{ width: (ct.count / maxCount) * 100 + '%' }"></div>
        </div>
      </li>
    </ol>
  </div>
</template>

<style scoped>
ol {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.bar-row {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  font-size: 14px;
  margin-bottom: 4px;
}
.label {
  color: var(--text-h);
}
.count {
  color: var(--text);
  font-variant-numeric: tabular-nums;
}
.bar-track {
  background: var(--bg);
  border-radius: 6px;
  height: 8px;
  overflow: hidden;
}
.bar-fill {
  background: var(--accent);
  height: 100%;
  border-radius: 6px;
  transition: width 0.3s ease;
}
</style>
