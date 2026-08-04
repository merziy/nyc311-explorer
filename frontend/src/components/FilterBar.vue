<script setup>
import { ref, watch } from 'vue'

const emit = defineEmits(['change'])

const borough = ref('')
const complaintType = ref('')
const start = ref('')
const end = ref('')

const boroughs = ['MANHATTAN', 'BRONX', 'BROOKLYN', 'QUEENS', 'STATEN ISLAND']

watch([borough, complaintType, start, end], () => {
  emit('change', {
    borough: borough.value,
    complaint_type: complaintType.value,
    start: start.value,
    end: end.value,
  })
})
</script>

<template>
  <div class="filter-bar">
    <select v-model="borough">
      <option value="">All boroughs</option>
      <option v-for="b in boroughs" :key="b" :value="b">{{ b }}</option>
    </select>
    <input v-model="complaintType" type="text" placeholder="Complaint type (e.g. Noise - Residential)" />
    <label>
      From
      <input v-model="start" type="date" />
    </label>
    <label>
      To
      <input v-model="end" type="date" />
    </label>
  </div>
</template>

<style scoped>
.filter-bar {
  display: flex;
  gap: 0.75rem;
  align-items: center;
  flex-wrap: wrap;
  padding: 1rem 0;
}
</style>
