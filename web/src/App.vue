<template>
  <v-app>
    <router-view v-slot="{ Component }">
      <transition name="fade" mode="out-in">
        <component :is="Component" />
      </transition>
    </router-view>

    <v-snackbar
      v-model="appStore.snackbar"
      :color="appStore.snackbarColor"
      :timeout="3000"
      location="top right"
    >
      {{ appStore.snackbarText }}
      <template v-slot:actions>
        <v-btn
          variant="text"
          @click="appStore.hideSnackbar"
        >
          关闭
        </v-btn>
      </template>
    </v-snackbar>

    <v-overlay
      :model-value="appStore.loading"
      class="align-center justify-center"
      persistent
    >
      <v-progress-circular
        indeterminate
        color="primary"
        size="64"
      />
      <div v-if="appStore.loadingText" class="mt-4 text-center">
        {{ appStore.loadingText }}
      </div>
    </v-overlay>
  </v-app>
</template>

<script setup lang="ts">
import { useAppStore } from '@/stores/app'

const appStore = useAppStore()
</script>

<style>
.v-overlay__content {
  display: flex;
  flex-direction: column;
  align-items: center;
}
</style>
