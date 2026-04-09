<template>
  <v-app-bar
    color="surface"
    density="comfortable"
    elevation="0"
    border
  >
    <v-app-bar-nav-icon @click="appStore.toggleSidebar" />

    <v-toolbar-title class="d-flex align-center">
      <img
        :src="logoSrc"
        alt="灵笔司书"
        class="mr-3"
        style="width: 32px; height: 32px; border-radius: 8px;"
      />
      <span class="text-h6 font-weight-medium">灵笔司书</span>
    </v-toolbar-title>

    <v-spacer />

    <!-- Sudo 模式按钮 (从右到左：退出 -> 主题 -> Sudo) -->
    <v-btn
      v-if="authStore.isAuthenticated"
      :color="authStore.isSudo ? 'error' : 'default'"
      :variant="authStore.isSudo ? 'flat' : 'outlined'"
      class="mr-2"
      @click="handleSudoClick"
    >
      <v-icon start>{{ authStore.isSudo ? 'mdi-shield-check' : 'mdi-shield-account' }}</v-icon>
      <span v-if="authStore.isSudo" class="text-caption ml-1">{{ authStore.sudoRemainingTime }}</span>
      <span v-else>Sudo</span>
      <v-tooltip activator="parent" location="bottom">
        {{ authStore.isSudo ? `Sudo 模式已激活 (剩余 ${authStore.sudoRemainingTime})` : '点击进入 Sudo 模式以启用编辑权限' }}
      </v-tooltip>
    </v-btn>

    <v-btn
      icon
      variant="text"
      @click="toggleTheme"
    >
      <v-icon>{{ isDark ? 'mdi-weather-sunny' : 'mdi-weather-night' }}</v-icon>
      <v-tooltip activator="parent" location="bottom">
        {{ isDark ? '切换到浅色模式' : '切换到深色模式' }}
      </v-tooltip>
    </v-btn>

    <v-btn
      icon
      variant="text"
      @click="handleLogout"
    >
      <v-icon>mdi-logout</v-icon>
      <v-tooltip activator="parent" location="bottom">
        退出登录
      </v-tooltip>
    </v-btn>

    <!-- Sudo 密码验证对话框 -->
    <v-dialog v-model="showSudoDialog" max-width="400">
      <v-card>
        <v-card-title class="text-h6">
          <v-icon color="warning" class="mr-2">mdi-shield-account</v-icon>
          进入 Sudo 模式
        </v-card-title>
        <v-card-text>
          <p class="text-body-2 mb-4">
            请输入您的登录密码以启用编辑权限。Sudo 模式将在 30 分钟无操作后自动退出。
          </p>
          <v-text-field
            v-model="sudoPassword"
            label="密码"
            type="password"
            variant="outlined"
            :error-messages="sudoError"
            @keyup.enter="verifySudo"
          />
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn variant="text" @click="showSudoDialog = false">
            取消
          </v-btn>
          <v-btn color="primary" :loading="sudoLoading" @click="verifySudo">
            验证
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </v-app-bar>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useTheme } from 'vuetify'
import { useRouter } from 'vue-router'
import { useAppStore } from '@/stores/app'
import { useAuthStore } from '@/stores/auth'

const theme = useTheme()
const router = useRouter()
const appStore = useAppStore()
const authStore = useAuthStore()

// Sudo 对话框状态
const showSudoDialog = ref(false)
const sudoPassword = ref('')
const sudoError = ref('')
const sudoLoading = ref(false)

const logoSrc = computed(() => {
  return '/api/static/icon/Scriptor_icon.png'
})

const isDark = computed(() => {
  return theme.global.current.value.dark
})

function toggleTheme() {
  theme.global.name.value = isDark.value ? 'scriptorLight' : 'scriptorDark'
  localStorage.setItem('scriptor_theme', theme.global.name.value)
}

function handleLogout() {
  authStore.logout()
  router.push('/login')
}

function handleSudoClick() {
  if (authStore.isSudo) {
    // 已在 Sudo 模式，点击退出
    authStore.exitSudo()
  } else {
    // 未在 Sudo 模式，显示密码对话框
    sudoPassword.value = ''
    sudoError.value = ''
    showSudoDialog.value = true
  }
}

async function verifySudo() {
  if (!sudoPassword.value) {
    sudoError.value = '请输入密码'
    return
  }

  sudoLoading.value = true
  sudoError.value = ''

  try {
    const result = await authStore.enterSudo(sudoPassword.value)
    if (result.success) {
      showSudoDialog.value = false
      sudoPassword.value = ''
    } else {
      sudoError.value = result.message || '密码错误'
    }
  } catch (e) {
    sudoError.value = e instanceof Error ? e.message : '验证失败'
  } finally {
    sudoLoading.value = false
  }
}
</script>
