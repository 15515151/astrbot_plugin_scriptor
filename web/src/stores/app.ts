import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useAppStore = defineStore('app', () => {
  const sidebarOpen = ref(true)
  const loading = ref(false)
  const loadingText = ref('')
  const snackbar = ref(false)
  const snackbarText = ref('')
  const snackbarColor = ref<'success' | 'error' | 'warning' | 'info'>('info')

  function toggleSidebar() {
    sidebarOpen.value = !sidebarOpen.value
  }

  function setLoading(value: boolean, text: string = '') {
    loading.value = value
    loadingText.value = text
  }

  function showSnackbar(text: string, color: 'success' | 'error' | 'warning' | 'info' = 'info') {
    snackbarText.value = text
    snackbarColor.value = color
    snackbar.value = true
  }

  function hideSnackbar() {
    snackbar.value = false
  }

  return {
    sidebarOpen,
    loading,
    loadingText,
    snackbar,
    snackbarText,
    snackbarColor,
    toggleSidebar,
    setLoading,
    showSnackbar,
    hideSnackbar,
  }
})
