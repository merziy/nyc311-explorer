<script setup>
import { ref } from 'vue'
import MapView from './components/MapView.vue'

const filters = ref({ borough: '', complaint_type: '', start: '', end: '' })

function onFilterChange(newFilters) {
  filters.value = newFilters
}
</script>

<template>
  <MapView :filters="filters" @filters-change="onFilterChange" />
</template>
