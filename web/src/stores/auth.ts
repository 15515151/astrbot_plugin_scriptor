import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { useScriptorApi } from '@/composables/useScriptorApi'

export const useAuthStore = defineStore('auth', () => {
  const apiKey = ref<string | null>(null)
  const isAuthenticated = ref(false)
  const loading = ref(false)
  const error = ref<string | null>(null)

  // Sudo 状态
  const isSudo = ref(false)
  const sudoRemainingSeconds = ref(0)
  const sudoLastActive = ref<number | null>(null)
  let sudoCheckInterval: ReturnType<typeof setInterval> | null = null

  const api = useScriptorApi()

  const sudoRemainingTime = computed(() => {
    if (!isSudo.value || sudoRemainingSeconds.value <= 0) return ''
    const minutes = Math.floor(sudoRemainingSeconds.value / 60)
    const seconds = sudoRemainingSeconds.value % 60
    return `${minutes}:${seconds.toString().padStart(2, '0')}`
  })

  async function initialize() {
    const savedKey = api.getApiKey()
    if (savedKey) {
      try {
        api.setApiKey(savedKey)
        const valid = await api.verifyApiKey()
        
        if (valid) {
          apiKey.value = savedKey
          isAuthenticated.value = true
          await checkSudoStatus()
        } else {
          api.clearApiKey()
        }
      } catch {
        api.clearApiKey()
      }
    }
  }

  async function login(key: string): Promise<boolean> {
    loading.value = true
    error.value = null

    try {
      api.setApiKey(key)
      const valid = await api.verifyApiKey()
      
      if (valid) {
        apiKey.value = key
        isAuthenticated.value = true
        return true
      } else {
        api.clearApiKey()
        error.value = 'API 密钥无效'
        return false
      }
    } catch (e) {
      api.clearApiKey()
      error.value = e instanceof Error ? e.message : '登录失败'
      return false
    } finally {
      loading.value = false
    }
  }

  function logout() {
    api.clearApiKey()
    apiKey.value = null
    isAuthenticated.value = false
    exitSudoLocal()
  }

  // Sudo 相关方法
  async function checkSudoStatus(): Promise<void> {
    try {
      const status = await api.getSudoStatus()
      isSudo.value = status.is_sudo
      sudoRemainingSeconds.value = status.remaining_seconds
      
      if (status.is_sudo && !sudoCheckInterval) {
        startSudoTimer()
      } else if (!status.is_sudo && sudoCheckInterval) {
        stopSudoTimer()
      }
    } catch {
      isSudo.value = false
      sudoRemainingSeconds.value = 0
    }
  }

  async function enterSudo(password: string): Promise<{ success: boolean; message: string }> {
    try {
      const result = await api.verifySudo(password)
      isSudo.value = true
      sudoRemainingSeconds.value = result.timeout_minutes * 60
      sudoLastActive.value = Date.now()
      startSudoTimer()
      return { success: true, message: result.message }
    } catch (e) {
      const message = e instanceof Error ? e.message : '验证失败'
      return { success: false, message }
    }
  }

  async function exitSudo(): Promise<void> {
    try {
      await api.exitSudo()
    } catch {
      // 忽略错误
    }
    exitSudoLocal()
  }

  function exitSudoLocal() {
    isSudo.value = false
    sudoRemainingSeconds.value = 0
    sudoLastActive.value = null
    stopSudoTimer()
  }

  function startSudoTimer() {
    if (sudoCheckInterval) return
    
    sudoCheckInterval = setInterval(async () => {
      if (sudoRemainingSeconds.value > 0) {
        sudoRemainingSeconds.value--
      }
      
      if (sudoRemainingSeconds.value <= 0) {
        exitSudoLocal()
      }
      
      if (sudoRemainingSeconds.value > 0 && sudoRemainingSeconds.value % 60 === 0) {
        await checkSudoStatus()
      }
    }, 1000)
  }

  function stopSudoTimer() {
    if (sudoCheckInterval) {
      clearInterval(sudoCheckInterval)
      sudoCheckInterval = null
    }
  }

  // 更新 Sudo 活跃时间（用户操作时调用）
  async function refreshSudoOnActivity() {
    if (isSudo.value) {
      sudoLastActive.value = Date.now()
      await checkSudoStatus()
    }
  }

  return {
    apiKey,
    isAuthenticated,
    loading,
    error,
    isSudo,
    sudoRemainingSeconds,
    sudoRemainingTime,
    initialize,
    login,
    logout,
    checkSudoStatus,
    enterSudo,
    exitSudo,
    refreshSudoOnActivity,
  }
})
