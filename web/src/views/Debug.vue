<template>
  <div>
    <h1 class="page-title">调试工具</h1>
    <p class="page-subtitle">系统调试和诊断工具</p>

    <v-row>
      <v-col cols="12" md="6">
        <v-card>
          <v-card-title>
            <v-icon class="mr-2" color="primary">mdi-api</v-icon>
            API 测试
          </v-card-title>
          <v-card-text>
            <v-text-field
              v-model="apiEndpoint"
              label="API 端点"
              hint="例如: status, profiles, config"
            />
            <v-btn color="primary" @click="testApi" :loading="testingApi">
              <v-icon class="mr-2">mdi-send</v-icon>
              发送请求
            </v-btn>

            <v-card v-if="apiResult" variant="outlined" class="mt-4">
              <v-card-title class="text-subtitle-2">响应结果</v-card-title>
              <v-card-text>
                <pre class="code-block">{{ JSON.stringify(apiResult, null, 2) }}</pre>
              </v-card-text>
            </v-card>
          </v-card-text>
        </v-card>
      </v-col>

      <v-col cols="12" md="6">
        <v-card>
          <v-card-title>
            <v-icon class="mr-2" color="primary">mdi-file-document</v-icon>
            系统日志
          </v-card-title>
          <v-card-text>
            <v-row class="mb-4">
              <v-col cols="6">
                <v-select
                  v-model="logSource"
                  :items="logSources"
                  label="日志来源"
                />
              </v-col>
              <v-col cols="6">
                <v-text-field
                  v-model.number="logLines"
                  label="显示行数"
                  type="number"
                  min="50"
                  max="500"
                />
              </v-col>
            </v-row>
            <v-btn color="primary" @click="loadLogs" :loading="loadingLogs">
              <v-icon class="mr-2">mdi-refresh</v-icon>
              刷新日志
            </v-btn>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>

    <v-card v-if="logs" class="mt-6">
      <v-card-title>
        <v-icon class="mr-2" color="primary">mdi-text-box</v-icon>
        日志内容
      </v-card-title>
      <v-card-text>
        <div v-for="(sourceData, sourceName) in logs.results" :key="sourceName" class="mb-4">
          <h3 class="text-subtitle-1 font-weight-medium mb-2">{{ getLogSourceName(sourceName as string) }}</h3>
          <v-alert v-if="'error' in sourceData" type="error" variant="tonal" class="mb-2">
            {{ sourceData.error }}
          </v-alert>
          <v-alert v-else-if="'hint' in sourceData" type="info" variant="tonal" class="mb-2">
            {{ sourceData.content }}
            <div v-if="sourceData.hint" class="mt-2">💡 {{ sourceData.hint }}</div>
          </v-alert>
          <pre v-else class="log-block">{{ sourceData.content }}</pre>
        </div>
      </v-card-text>
    </v-card>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useScriptorApi } from '@/composables/useScriptorApi'
import { useAppStore } from '@/stores/app'
import type { LogsResponse } from '@/types'

const api = useScriptorApi()
const appStore = useAppStore()

const apiEndpoint = ref('status')
const apiResult = ref<unknown>(null)
const testingApi = ref(false)

const logSource = ref('all')
const logSources = [
  { title: '全部', value: 'all' },
  { title: 'API 服务', value: 'api' },
  { title: '前端服务', value: 'frontend' },
  { title: 'AstrBot 主日志', value: 'astrbot' },
]
const logLines = ref(100)
const logs = ref<LogsResponse | null>(null)
const loadingLogs = ref(false)

async function testApi() {
  testingApi.value = true
  try {
    const response = await fetch(`/api/${apiEndpoint.value}`, {
      headers: {
        'X-API-Key': api.getApiKey() || '',
      },
    })
    apiResult.value = await response.json()
  } catch (e) {
    apiResult.value = { error: e instanceof Error ? e.message : '请求失败' }
  } finally {
    testingApi.value = false
  }
}

async function loadLogs() {
  loadingLogs.value = true
  try {
    logs.value = await api.getLogs(logLines.value, logSource.value)
  } catch (e) {
    console.error('Failed to load logs:', e)
    appStore.showSnackbar('获取日志失败', 'error')
  } finally {
    loadingLogs.value = false
  }
}

function getLogSourceName(source: string): string {
  const map: Record<string, string> = {
    api: 'API 服务',
    frontend: '前端服务',
    astrbot: 'AstrBot 主日志',
  }
  return map[source] || source
}
</script>

<style scoped>
.code-block, .log-block {
  background: rgba(0, 0, 0, 0.3);
  padding: 16px;
  border-radius: 8px;
  font-family: monospace;
  font-size: 12px;
  overflow-x: auto;
  white-space: pre-wrap;
  word-break: break-all;
}

.log-block {
  max-height: 400px;
  overflow-y: auto;
}
</style>
