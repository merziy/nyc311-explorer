<script setup>
import { ref } from 'vue'
import FilterBar from './components/FilterBar.vue'
import TopComplaintTypes from './components/TopComplaintTypes.vue'
import ComplaintsTable from './components/ComplaintsTable.vue'

const filters = ref({ borough: '', complaint_type: '', start: '', end: '' })

function onFilterChange(newFilters) {
  filters.value = newFilters
}
</script>

<template>
  <main>
    <h1>NYC 311 Explorer</h1>
    <FilterBar @change="onFilterChange" />
    <TopComplaintTypes :filters="filters" />
    <ComplaintsTable :filters="filters" />
  </main>
</template>
