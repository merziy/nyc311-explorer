<script setup>
import { ref } from 'vue'
import FilterBar from './components/FilterBar.vue'
import TopComplaintTypes from './components/TopComplaintTypes.vue'
import ComplaintsTable from './components/ComplaintsTable.vue'
import AskBox from './components/AskBox.vue'
import ThemeToggle from './components/ThemeToggle.vue'

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
    <AskBox />
    <FilterBar @change="onFilterChange" />
    <TopComplaintTypes :filters="filters" />
    <ComplaintsTable :filters="filters" />
  </div>
</template>

<style scoped>
.page {
  max-width: 880px;
  margin: 0 auto;
  padding: 32px 20px 64px;
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
</style>
