<template>
  <v-app class="login-app">
    <v-container fluid class="fill-height pa-0">
      <v-row no-gutters class="fill-height">
        <v-col cols="12" md="6" class="d-none d-md-flex align-center justify-center login-bg">
          <div class="text-center pa-8">
            <img
              :src="avatarSrc"
              alt="灵笔司书"
              class="login-avatar mb-6"
            />
            <h1 class="text-h4 font-weight-bold mb-4 gradient-text">
              灵笔司书
            </h1>
            <p class="text-h6 text-medium-emphasis">
              AI 智能管家记忆系统
            </p>
            <p class="text-body-2 text-medium-emphasis mt-4" style="max-width: 400px;">
              Scriptor (灵笔司书)，是一个基于 Markdown 的长期记忆引擎，吸纳了 ReMe 的架构灵魂、CoPaw 的文件基因、Angel Memory 的人情味。目标是构建一个超级 AI 管家，为每个人提供个性化、可控制、透明的记忆系统。
            </p>
          </div>
        </v-col>

        <v-col cols="12" md="6" class="d-flex align-center justify-center">
          <v-card class="login-card mx-4" max-width="400" width="100%">
            <v-card-text class="pa-8">
              <div class="text-center mb-8 d-md-none">
                <img
                  :src="logoSrc"
                  alt="灵笔司书"
                  class="mb-4"
                  style="width: 64px; height: 64px; border-radius: 16px;"
                />
                <h2 class="text-h5 font-weight-bold">灵笔司书</h2>
              </div>

              <!-- 首次设置密码 -->
              <template v-if="needsSetup">
                <h3 class="text-h6 font-weight-medium mb-2 text-center">
                  首次使用
                </h3>
                <p class="text-body-2 text-medium-emphasis mb-6 text-center">
                  请设置您的登录密码
                </p>

                <v-form @submit.prevent="handleSetup">
                  <v-text-field
                    v-model="newPassword"
                    label="设置密码"
                    type="password"
                    variant="outlined"
                    :error-messages="error"
                    :loading="loading"
                    prepend-inner-icon="mdi-lock"
                    hint="密码长度至少 6 位"
                    class="mb-4"
                  />

                  <v-text-field
                    v-model="confirmPassword"
                    label="确认密码"
                    type="password"
                    variant="outlined"
                    :error-messages="error"
                    prepend-inner-icon="mdi-lock-check"
                    class="mb-4"
                  />

                  <v-btn
                    type="submit"
                    color="primary"
                    size="large"
                    block
                    :loading="loading"
                    :disabled="!newPassword || newPassword !== confirmPassword"
                  >
                    设置密码并登录
                  </v-btn>
                </v-form>
              </template>

              <!-- 正常登录 -->
              <template v-else>
                <h3 class="text-h6 font-weight-medium mb-2 text-center">
                  欢迎回来
                </h3>
                <p class="text-body-2 text-medium-emphasis mb-6 text-center">
                  请输入密码以访问系统
                </p>

                <v-form @submit.prevent="handleLogin">
                  <v-text-field
                    v-model="apiKey"
                    label="密码"
                    type="password"
                    variant="outlined"
                    :error-messages="error"
                    :loading="loading"
                    prepend-inner-icon="mdi-key"
                    autofocus
                    class="mb-4"
                  />

                  <v-btn
                    type="submit"
                    color="primary"
                    size="large"
                    block
                    :loading="loading"
                  >
                    安全登录
                  </v-btn>
                </v-form>
              </template>
            </v-card-text>
          </v-card>
        </v-col>
      </v-row>
    </v-container>
  </v-app>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useScriptorApi } from '@/composables/useScriptorApi'

const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()
const api = useScriptorApi()

const apiKey = ref('')
const newPassword = ref('')
const confirmPassword = ref('')
const loading = ref(false)
const error = ref('')
const needsSetup = ref(false)
const checkingSetup = ref(true)

const avatarSrc = '/api/static/icon/Scriptor.png'
const logoSrc = '/api/static/icon/Scriptor_icon.png'

onMounted(async () => {
  try {
    const status = await api.getSetupStatus()
    needsSetup.value = status.needs_setup
  } catch {
    needsSetup.value = false
  } finally {
    checkingSetup.value = false
  }
})

async function handleSetup() {
  if (!newPassword.value) {
    error.value = '请输入密码'
    return
  }
  if (newPassword.value.length < 6) {
    error.value = '密码长度至少 6 位'
    return
  }
  if (newPassword.value !== confirmPassword.value) {
    error.value = '两次输入的密码不一致'
    return
  }

  loading.value = true
  error.value = ''

  try {
    await api.setupFirstPassword(newPassword.value)
    const success = await authStore.login(newPassword.value)
    if (success) {
      const redirect = route.query.redirect as string
      router.push(redirect || '/')
    } else {
      error.value = '登录失败，请重试'
    }
  } catch (e: unknown) {
    const errorDetail = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail
    error.value = errorDetail || '设置密码失败'
  } finally {
    loading.value = false
  }
}

async function handleLogin() {
  if (!apiKey.value) {
    error.value = '请输入密码'
    return
  }

  loading.value = true
  error.value = ''

  try {
    const success = await authStore.login(apiKey.value)
    if (success) {
      const redirect = route.query.redirect as string
      router.push(redirect || '/')
    } else {
      error.value = authStore.error || '登录失败'
    }
  } catch (e) {
    error.value = e instanceof Error ? e.message : '登录失败'
  } finally {
    loading.value = false
  }
}
</script>

<style scoped lang="scss">
.login-app {
  background: var(--bg-color);
}

.login-bg {
  background: linear-gradient(135deg, rgba(10, 132, 255, 0.1) 0%, rgba(94, 92, 230, 0.1) 100%);
  position: relative;
  overflow: hidden;

  &::before {
    content: '';
    position: absolute;
    top: -50%;
    left: -50%;
    width: 200%;
    height: 200%;
    background: radial-gradient(circle, rgba(10, 132, 255, 0.05) 0%, transparent 50%);
    animation: pulse 15s ease-in-out infinite;
  }
}

@keyframes pulse {
  0%, 100% {
    transform: scale(1);
    opacity: 0.5;
  }
  50% {
    transform: scale(1.1);
    opacity: 0.8;
  }
}

.login-avatar {
  width: 200px;
  height: 200px;
  border-radius: 24px;
  box-shadow: 0 20px 60px rgba(10, 132, 255, 0.3);
  animation: float 6s ease-in-out infinite;
}

@keyframes float {
  0%, 100% {
    transform: translateY(0);
  }
  50% {
    transform: translateY(-10px);
  }
}

.login-card {
  background: var(--surface-color) !important;
  border: 1px solid var(--border-color) !important;
  border-radius: 16px !important;
}

.gradient-text {
  background: linear-gradient(135deg, var(--primary-color), var(--secondary-color));
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}
</style>
