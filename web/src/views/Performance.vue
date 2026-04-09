<template>
  <div>
    <h1 class="page-title">性能面板</h1>
    <p class="page-subtitle">监控系统性能指标</p>

    <v-row class="mb-6">
      <v-col cols="12" sm="4">
        <StatCard
          title="CPU 使用率"
          :value="stats ? `${stats.cpu_percent}%` : '-'"
          icon="mdi-memory"
          icon-color="primary"
          :loading="loading"
        />
      </v-col>
      <v-col cols="12" sm="4">
        <StatCard
          title="内存使用"
          :value="stats ? `${stats.memory_usage_mb} MB` : '-'"
          icon="mdi-chip"
          icon-color="success"
          :loading="loading"
        />
      </v-col>
      <v-col cols="12" sm="4">
        <StatCard
          title="数据库大小"
          :value="stats ? `${stats.db_size_mb} MB` : '-'"
          icon="mdi-database"
          icon-color="warning"
          :loading="loading"
        />
      </v-col>
    </v-row>

    <v-card>
      <v-card-title>
        <v-icon class="mr-2" color="primary">mdi-chart-line</v-icon>
        性能图表
      </v-card-title>
      <v-card-text>
        <v-empty-state
          v-if="!stats?.history?.length"
          icon="mdi-chart-areaspline"
          title="暂无性能数据"
          text="性能历史数据将在系统运行后显示"
        />
        <div v-else class="text-center py-8">
          <v-icon size="64" color="primary" class="mb-4">mdi-chart-line</v-icon>
          <p class="text-medium-emphasis">性能图表功能开发中...</p>
        </div>
      </v-card-text>
    </v-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useScriptorApi } from '@/composables/useScriptorApi'
import type { PerformanceStats } from '@/types'
import StatCard from '@/components/common/StatCard.vue'

const api = useScriptorApi()

const stats = ref<PerformanceStats | null>(null)
const loading = ref(true)

onMounted(async () => {
  try {
    stats.value = await api.getPerformanceStats()
  } catch (e) {
    console.error('Failed to load performance stats:', e)
  } finally {
    loading.value = false
  }
})
</script>
