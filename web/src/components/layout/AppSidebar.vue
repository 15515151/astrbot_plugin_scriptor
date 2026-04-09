<template>
  <v-navigation-drawer
    v-model="appStore.sidebarOpen"
    color="surface"
    :rail="false"
    permanent
  >
    <v-list nav class="px-2 py-4">
      <v-list-item
        v-for="item in menuItems"
        :key="item.to"
        :to="item.to"
        :prepend-icon="item.icon"
        :title="item.title"
        :value="item.to"
        rounded="lg"
        class="mb-1"
      />
    </v-list>

    <template v-slot:append>
      <div class="pa-4">
        <v-divider class="mb-4" />
        <div class="text-caption text-medium-emphasis text-center">
          灵笔司书 v1.0.0
        </div>
      </div>
    </template>
  </v-navigation-drawer>
</template>

<script setup lang="ts">
import { useAppStore } from '@/stores/app'

const appStore = useAppStore()

const menuItems = [
  { to: '/', title: '系统概览', icon: 'mdi-view-dashboard' },
  { to: '/memory', title: '记忆管理', icon: 'mdi-brain' },
  { to: '/archives', title: '档案馆', icon: 'mdi-database' },
  { to: '/knowledge', title: '知识库', icon: 'mdi-book-open-variant' },
  { to: '/config', title: '配置中心', icon: 'mdi-cog' },
  { to: '/performance', title: '性能面板', icon: 'mdi-chart-line' },
  { to: '/maintenance', title: '维护工具', icon: 'mdi-tools' },
  { to: '/debug', title: '调试工具', icon: 'mdi-bug' },
]
</script>
