<template>
  <div>
    <h1 class="page-title">系统概览</h1>
    <p class="page-subtitle">查看灵笔司书系统的整体运行状态</p>

    <v-row class="mb-6">
      <v-col cols="12" sm="6" md="3">
        <StatCard
          title="运行状态"
          :value="status?.status || '加载中...'"
          icon="mdi-circle"
          :icon-color="status?.status === 'running' ? 'success' : 'error'"
          :loading="loading"
        />
      </v-col>
      <v-col cols="12" sm="6" md="3">
        <StatCard
          title="用户画像"
          :value="status?.profiles_count ?? 0"
          icon="mdi-account"
          icon-color="primary"
          :loading="loading"
        />
      </v-col>
      <v-col cols="12" sm="6" md="3">
        <StatCard
          title="群体数量"
          :value="status?.groups_count ?? 0"
          icon="mdi-account-group"
          icon-color="secondary"
          :loading="loading"
        />
      </v-col>
      <v-col cols="12" sm="6" md="3">
        <StatCard
          title="记忆文件"
          :value="status?.total_memory_files ?? 0"
          icon="mdi-file-document"
          icon-color="warning"
          :loading="loading"
        />
      </v-col>
    </v-row>

    <v-row>
      <v-col cols="12" md="6">
        <v-card>
          <v-card-title class="d-flex align-center">
            <v-icon class="mr-2" color="primary">mdi-folder</v-icon>
            数据目录
          </v-card-title>
          <v-card-text>
            <v-text-field
              :model-value="status?.data_dir || '-'"
              readonly
              variant="outlined"
              density="compact"
              hide-details
              class="font-monospace"
            />
          </v-card-text>
        </v-card>
      </v-col>

      <v-col cols="12" md="6">
        <v-card>
          <v-card-title class="d-flex align-center">
            <v-icon class="mr-2" color="primary">mdi-clock</v-icon>
            系统信息
          </v-card-title>
          <v-card-text>
            <v-list density="compact">
              <v-list-item>
                <template v-slot:prepend>
                  <v-icon size="small">mdi-update</v-icon>
                </template>
                <v-list-item-title>最后更新</v-list-item-title>
                <v-list-item-subtitle>{{ formatTime(status?.timestamp) }}</v-list-item-subtitle>
              </v-list-item>
              <v-list-item>
                <template v-slot:prepend>
                  <v-icon size="small">mdi-check-circle</v-icon>
                </template>
                <v-list-item-title>初始化状态</v-list-item-title>
                <v-list-item-subtitle>
                  <v-chip
                    :color="status?.initialized ? 'success' : 'warning'"
                    size="x-small"
                  >
                    {{ status?.initialized ? '已完成' : '进行中' }}
                  </v-chip>
                </v-list-item-subtitle>
              </v-list-item>
            </v-list>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>

    <v-alert
      v-if="status?.initialized === false"
      type="warning"
      variant="tonal"
      class="mt-6"
    >
      系统正在初始化中，部分功能可能不可用。请稍候...
    </v-alert>

    <v-alert
      v-if="status?.initialized === true"
      type="success"
      variant="tonal"
      class="mt-6"
    >
      系统已完全初始化并正常运行
    </v-alert>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useScriptorApi } from '@/composables/useScriptorApi'
import type { StatusResponse } from '@/types'
import StatCard from '@/components/common/StatCard.vue'

const api = useScriptorApi()
const status = ref<StatusResponse | null>(null)
const loading = ref(true)

onMounted(async () => {
  try {
    status.value = await api.getStatus()
  } catch (e) {
    console.error('Failed to load status:', e)
  } finally {
    loading.value = false
  }
})

function formatTime(timestamp?: string): string {
  if (!timestamp) return '-'
  try {
    return new Date(timestamp).toLocaleString('zh-CN')
  } catch {
    return timestamp
  }
}
</script>
