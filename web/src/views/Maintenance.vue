<template>
  <div>
    <h1 class="page-title">维护工具</h1>
    <p class="page-subtitle">系统维护和配置管理</p>

    <v-row>
      <v-col cols="12" md="6">
        <v-card>
          <v-card-title>
            <v-icon class="mr-2" color="primary">mdi-backup-restore</v-icon>
            数据备份
          </v-card-title>
          <v-card-text>
            <p class="text-body-2 text-medium-emphasis mb-4">
              创建系统数据备份，包括配置、记忆文件和数据库。
            </p>
            <v-btn
              color="primary"
              :loading="backingUp"
              @click="createBackup"
            >
              <v-icon class="mr-2">mdi-backup-restore</v-icon>
              创建备份
            </v-btn>
          </v-card-text>
        </v-card>
      </v-col>

      <v-col cols="12" md="6">
        <v-card>
          <v-card-title>
            <v-icon class="mr-2" color="warning">mdi-broom</v-icon>
            系统清理
          </v-card-title>
          <v-card-text>
            <p class="text-body-2 text-medium-emphasis mb-4">
              清理临时文件、过期缓存和无效数据。
            </p>
            <v-btn
              color="warning"
              :loading="cleaning"
              @click="cleanup"
            >
              <v-icon class="mr-2">mdi-broom</v-icon>
              清理临时文件
            </v-btn>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>

    <v-card class="mt-6">
      <v-card-title>
        <v-icon class="mr-2" color="primary">mdi-information</v-icon>
        关于灵笔司书
      </v-card-title>
      <v-card-text>
        <v-list density="compact">
          <v-list-item>
            <v-list-item-title><strong>名称</strong></v-list-item-title>
            <v-list-item-subtitle>灵笔司书 (Scriptor)</v-list-item-subtitle>
          </v-list-item>
          <v-list-item>
            <v-list-item-title><strong>版本</strong></v-list-item-title>
            <v-list-item-subtitle>1.0.0</v-list-item-subtitle>
          </v-list-item>
          <v-list-item>
            <v-list-item-title><strong>作者</strong></v-list-item-title>
            <v-list-item-subtitle>ysf7762-dev</v-list-item-subtitle>
          </v-list-item>
          <v-list-item>
            <v-list-item-title><strong>许可证</strong></v-list-item-title>
            <v-list-item-subtitle>GNU Affero General Public License v3.0</v-list-item-subtitle>
          </v-list-item>
        </v-list>

        <v-divider class="my-4" />

        <h3 class="text-subtitle-1 font-weight-medium mb-2">主要功能</h3>
        <v-chip-group>
          <v-chip>用户身份识别与管理</v-chip>
          <v-chip>长期记忆存储与检索</v-chip>
          <v-chip>知识图谱构建</v-chip>
          <v-chip>跨群组记忆共享</v-chip>
          <v-chip>智能记忆压缩与归档</v-chip>
        </v-chip-group>
      </v-card-text>
    </v-card>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useScriptorApi } from '@/composables/useScriptorApi'
import { useAppStore } from '@/stores/app'

const api = useScriptorApi()
const appStore = useAppStore()

const backingUp = ref(false)
const cleaning = ref(false)

async function createBackup() {
  backingUp.value = true
  try {
    await api.createBackup()
    appStore.showSnackbar('备份创建成功', 'success')
  } catch (e) {
    console.error('Failed to create backup:', e)
    appStore.showSnackbar('备份失败', 'error')
  } finally {
    backingUp.value = false
  }
}

async function cleanup() {
  cleaning.value = true
  try {
    await api.cleanup()
    appStore.showSnackbar('清理完成', 'success')
  } catch (e) {
    console.error('Failed to cleanup:', e)
    appStore.showSnackbar('清理失败', 'error')
  } finally {
    cleaning.value = false
  }
}
</script>
