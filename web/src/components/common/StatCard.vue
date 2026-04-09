<template>
  <v-card class="stat-card h-100">
    <v-card-text class="d-flex flex-column">
      <div class="d-flex align-center mb-3">
        <v-avatar :color="iconColor" size="48" class="mr-3">
          <v-icon :icon="icon" color="white" />
        </v-avatar>
        <div>
          <div class="text-caption text-medium-emphasis">{{ title }}</div>
          <div class="text-h5 font-weight-bold" :class="`text-${iconColor}`">
            <template v-if="loading">
              <v-skeleton-loader type="text" width="60" />
            </template>
            <template v-else>
              {{ value }}
            </template>
          </div>
        </div>
      </div>
    </v-card-text>
  </v-card>
</template>

<script setup lang="ts">
defineProps<{
  title: string
  value: string | number
  icon: string
  iconColor?: 'primary' | 'secondary' | 'success' | 'warning' | 'error' | 'info'
  loading?: boolean
}>()
</script>
