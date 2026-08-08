<script setup>
import { ref } from 'vue'
import { askQuestion } from '../api'

const question = ref('')
const answer = ref(null)
const loading = ref(false)
const error = ref(null)

async function onSubmit() {
  const q = question.value.trim()
  if (!q || loading.value) return

  loading.value = true
  error.value = null
  answer.value = null
  try {
    answer.value = await askQuestion(q)
  } catch (e) {
    error.value = e.message
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="ask-box card">
    <h2>Ask a question</h2>
    <form @submit.prevent="onSubmit">
      <input
        v-model="question"
        type="text"
        placeholder="e.g. What are the top complaints in Bushwick this summer?"
      />
      <button type="submit" :disabled="loading || !question.trim()">
        {{ loading ? 'Asking…' : 'Ask' }}
      </button>
    </form>
    <p v-if="error" class="error">{{ error }}</p>
    <p v-if="answer" class="answer">{{ answer.answer }}</p>
  </div>
</template>

<style scoped>
form {
  display: flex;
  gap: 0.75rem;
}
input {
  flex: 1;
}
.answer {
  margin-top: 0.9rem;
  line-height: 1.6;
}
.error {
  margin-top: 0.75rem;
}
</style>
