<template>
  <div class="mb-6">
    <h3 class="text-subtitle-1 font-weight-medium mb-4 d-flex align-center">
      <v-icon v-if="icon" :icon="icon" class="mr-2" color="primary" />
      {{ title }}
    </h3>
    <slot />
  </div>
</template>

<script setup lang="ts">
defineProps<{
  title: string
  icon?: string
}>()
</script>
