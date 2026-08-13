<script setup>
import { ref } from 'vue'
import TopComplaintTypes from './components/TopComplaintTypes.vue'
import ComplaintsTable from './components/ComplaintsTable.vue'
import ThemeToggle from './components/ThemeToggle.vue'
import MapView from './components/MapView.vue'

const filters = ref({ borough: '', complaint_type: '', start: '', end: '' })

function onFilterChange(newFilters) {
  filters.value = newFilters
}
</script>

<template>
  <div class="page">
    <header class="page-header">
      <h1>NYC 311 Explorer</h1>
      <ThemeToggle />
    </header>
  </div>
  <div class="map-section">
    <MapView :filters="filters" @filters-change="onFilterChange" />
  </div>
  <div class="page">
    <TopComplaintTypes :filters="filters" />
    <ComplaintsTable :filters="filters" />
  </div>
</template>

<style scoped>
.page {
  max-width: 880px;
  margin: 0 auto;
  padding: 12px 20px;
  display: flex;
  flex-direction: column;
  gap: 20px;
}
.page:first-child {
  padding-top: 32px;
}
.page:last-child {
  padding-bottom: 64px;
}

.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.map-section {
  width: 100vw;
  max-width: 1300px;
  margin-left: 50%;
  transform: translateX(-50%);
  padding: 12px 20px;
  box-sizing: border-box;
}
</style>
