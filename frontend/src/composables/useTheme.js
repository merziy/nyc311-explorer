import { ref } from 'vue'

const STORAGE_KEY = 'nyc311-theme'
const darkMediaQuery = window.matchMedia('(prefers-color-scheme: dark)')

function storedTheme() {
  return localStorage.getItem(STORAGE_KEY)
}

function systemTheme() {
  return darkMediaQuery.matches ? 'dark' : 'light'
}

const theme = ref(storedTheme() || systemTheme())

darkMediaQuery.addEventListener('change', (e) => {
  if (!storedTheme()) {
    theme.value = e.matches ? 'dark' : 'light'
  }
})

export function useTheme() {
  function toggle() {
    const next = theme.value === 'dark' ? 'light' : 'dark'
    theme.value = next
    localStorage.setItem(STORAGE_KEY, next)
    document.documentElement.dataset.theme = next
  }

  return { theme, toggle }
}
