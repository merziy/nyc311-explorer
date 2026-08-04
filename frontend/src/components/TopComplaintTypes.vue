<script setup>
import { ref, watch, onMounted } from 'vue'
import { fetchSummary } from '../api'

const props = defineProps({
  filters: { type: Object, required: true },
})

const complaintTypes = ref([])
const loading = ref(false)
const error = ref(null)

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
  <div class="top-types">
    <h2>Top complaint types</h2>
    <p v-if="error" class="error">{{ error }}</p>
    <ol>
      <li v-for="ct in complaintTypes" :key="ct.complaint_type">
        {{ ct.complaint_type }} — {{ ct.count }}
      </li>
    </ol>
  </div>
</template>
