<template>
  <div>
    <h1 class="page-title">记忆管理</h1>
    <p class="page-subtitle">管理用户、群聊和全局的记忆文件</p>

    <v-row>
      <v-col cols="12" md="4">
        <v-card>
          <v-card-title class="d-flex align-center">
            <v-icon class="mr-2" color="primary">mdi-account-multiple</v-icon>
            选择对象
          </v-card-title>
          <v-card-text>
            <v-tabs v-model="activeTab" grow class="mb-4">
              <v-tab value="global">
                <v-icon class="mr-1">mdi-earth</v-icon>
                全局
              </v-tab>
              <v-tab value="profiles">用户</v-tab>
              <v-tab value="groups">群聊</v-tab>
            </v-tabs>

            <!-- 全局记忆说明 -->
            <div v-if="activeTab === 'global'" class="pa-4 text-center">
              <v-icon size="48" color="success" class="mb-2">mdi-earth</v-icon>
              <p class="text-body-2">全局记忆对所有用户和群聊可见</p>
              <p class="text-caption text-medium-emphasis mt-2">
                编辑全局记忆需要 Sudo 权限
              </p>
            </div>

            <v-list v-else-if="activeTab === 'profiles'" density="compact" class="pa-0">
              <v-list-item
                v-for="profile in profiles"
                :key="profile.uid"
                :active="selectedId === profile.uid"
                @click="selectProfile(profile.uid)"
              >
                <template v-slot:prepend>
                  <v-avatar color="primary" size="32">
                    <v-icon>mdi-account</v-icon>
                  </v-avatar>
                </template>
                <v-list-item-title>{{ profile.name || profile.uid }}</v-list-item-title>
                <v-list-item-subtitle>{{ profile.uid }}</v-list-item-subtitle>
              </v-list-item>
              <v-list-item v-if="profiles.length === 0">
                <v-list-item-title class="text-medium-emphasis">暂无用户数据</v-list-item-title>
              </v-list-item>
            </v-list>

            <v-list v-else density="compact" class="pa-0">
              <v-list-item
                v-for="group in groups"
                :key="group.group_id"
                :active="selectedId === group.group_id"
                @click="selectGroup(group.group_id)"
              >
                <template v-slot:prepend>
                  <v-avatar color="secondary" size="32">
                    <v-icon>mdi-account-group</v-icon>
                  </v-avatar>
                </template>
                <v-list-item-title>{{ group.name || group.group_id }}</v-list-item-title>
                <v-list-item-subtitle>{{ group.group_id }}</v-list-item-subtitle>
              </v-list-item>
              <v-list-item v-if="groups.length === 0">
                <v-list-item-title class="text-medium-emphasis">暂无群聊数据</v-list-item-title>
              </v-list-item>
            </v-list>
          </v-card-text>
        </v-card>
      </v-col>

      <v-col cols="12" md="8">
        <!-- 全局记忆面板 -->
        <template v-if="activeTab === 'global'">
          <v-card class="mb-4">
            <v-card-title class="d-flex align-center">
              <v-icon class="mr-2" color="success">mdi-earth</v-icon>
              全局记忆文件
              <v-spacer />
              <v-btn
                color="primary"
                variant="text"
                size="small"
                @click="loadGlobalMemoryFiles"
              >
                <v-icon class="mr-1">mdi-refresh</v-icon>
                刷新
              </v-btn>
            </v-card-title>
            <v-card-text>
              <v-list density="compact">
                <v-list-item
                  v-for="file in globalMemoryFiles"
                  :key="file.filename"
                  :active="selectedGlobalFile === file.filename"
                  @click="selectGlobalFile(file.filename)"
                >
                  <template v-slot:prepend>
                    <v-icon :color="getGlobalFileColor(file.filename)">
                      {{ getGlobalFileIcon(file.filename) }}
                    </v-icon>
                  </template>
                  <v-list-item-title>
                    {{ file.filename }}
                    <v-chip size="x-small" class="ml-2" :color="getGlobalFileColor(file.filename)">
                      {{ getGlobalFileLabel(file.filename) }}
                    </v-chip>
                  </v-list-item-title>
                  <v-list-item-subtitle>
                    {{ formatSize(file.size) }}
                    <span v-if="file.modified"> · {{ file.modified }}</span>
                  </v-list-item-subtitle>
                </v-list-item>
              </v-list>
            </v-card-text>
          </v-card>

          <v-card v-if="selectedGlobalFile">
            <v-card-title class="d-flex align-center">
              <v-icon class="mr-2" color="success">mdi-pencil</v-icon>
              编辑: {{ selectedGlobalFile }}
              <v-chip v-if="!authStore.isSudo" color="warning" size="small" class="ml-2">
                需要 Sudo 权限
              </v-chip>
              <v-spacer />
              <v-btn
                color="primary"
                :loading="savingGlobal"
                :disabled="!authStore.isSudo"
                @click="saveGlobalFile"
              >
                <v-icon class="mr-1">mdi-content-save</v-icon>
                保存
              </v-btn>
            </v-card-title>
            <v-card-text>
              <v-alert
                v-if="!authStore.isSudo"
                type="info"
                variant="tonal"
                class="mb-4"
              >
                编辑全局记忆需要 Sudo 权限。请点击右上角的 Sudo 按钮进行验证。
              </v-alert>
              <MdEditor
                v-model="globalFileContent"
                language="zh-CN"
                :preview="true"
                :toolbars="editorToolbars"
                :disabled="!authStore.isSudo"
                class="memory-editor"
              />
            </v-card-text>
          </v-card>
        </template>

        <!-- 用户/群聊记忆面板 -->
        <template v-else>
          <v-card v-if="!selectedId">
            <v-card-text class="text-center py-12">
              <v-icon size="64" color="medium-emphasis" class="mb-4">mdi-arrow-left</v-icon>
              <p class="text-medium-emphasis">请从左侧选择用户或群聊</p>
            </v-card-text>
          </v-card>

          <template v-else>
            <v-card class="mb-4">
              <v-card-title class="d-flex align-center">
                <v-icon class="mr-2" color="primary">mdi-file-document-multiple</v-icon>
                记忆文件
                <v-spacer />
                <v-btn
                  color="primary"
                  variant="text"
                  size="small"
                  @click="loadMemoryFiles"
                >
                  <v-icon class="mr-1">mdi-refresh</v-icon>
                  刷新
                </v-btn>
              </v-card-title>
              <v-card-text>
                <v-list density="compact">
                  <v-list-item
                    v-for="file in memoryFiles"
                    :key="file.filename"
                    :active="selectedFile === file.filename"
                    @click="selectFile(file.filename)"
                  >
                    <template v-slot:prepend>
                      <v-icon>mdi-file-document</v-icon>
                    </template>
                    <v-list-item-title>{{ file.filename }}</v-list-item-title>
                    <v-list-item-subtitle>
                      {{ formatSize(file.size) }} · {{ file.modified_str }}
                    </v-list-item-subtitle>
                    <template v-slot:append>
                      <v-btn
                        icon="mdi-delete"
                        variant="text"
                        size="small"
                        color="error"
                        @click.stop="deleteFile(file.filename)"
                      />
                    </template>
                  </v-list-item>
                  <v-list-item v-if="memoryFiles.length === 0">
                    <v-list-item-title class="text-medium-emphasis">暂无记忆文件</v-list-item-title>
                  </v-list-item>
                </v-list>
              </v-card-text>
            </v-card>

            <v-card v-if="selectedFile">
              <v-card-title class="d-flex align-center">
                <v-icon class="mr-2" color="primary">mdi-pencil</v-icon>
                编辑: {{ selectedFile }}
                <v-spacer />
                <v-btn
                  color="primary"
                  :loading="saving"
                  @click="saveFile"
                >
                  <v-icon class="mr-1">mdi-content-save</v-icon>
                  保存
                </v-btn>
              </v-card-title>
              <v-card-text>
                <MdEditor
                  v-model="fileContent"
                  language="zh-CN"
                  :preview="true"
                  :toolbars="editorToolbars"
                  class="memory-editor"
                />
              </v-card-text>
            </v-card>
          </template>
        </template>
      </v-col>
    </v-row>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, watch } from 'vue'
import { useScriptorApi } from '@/composables/useScriptorApi'
import { useAppStore } from '@/stores/app'
import { useAuthStore } from '@/stores/auth'
import type { Profile, Group, MemoryFile, GlobalMemoryFile } from '@/types'
import { MdEditor, type ToolbarNames } from 'md-editor-v3'
import 'md-editor-v3/lib/style.css'

const api = useScriptorApi()
const appStore = useAppStore()
const authStore = useAuthStore()

const activeTab = ref<'global' | 'profiles' | 'groups'>('global')
const profiles = ref<Profile[]>([])
const groups = ref<Group[]>([])
const selectedId = ref<string | null>(null)
const memoryFiles = ref<MemoryFile[]>([])
const selectedFile = ref<string | null>(null)
const fileContent = ref('')
const saving = ref(false)

// 全局记忆
const globalMemoryFiles = ref<GlobalMemoryFile[]>([])
const selectedGlobalFile = ref<string | null>(null)
const globalFileContent = ref('')
const savingGlobal = ref(false)

const editorToolbars: ToolbarNames[] = [
  'bold', 'underline', 'italic', '-',
  'title', 'strikeThrough', 'sub', 'sup', 'quote', '-',
  'unorderedList', 'orderedList', 'task', '-',
  'codeRow', 'code', 'link', 'image', 'table', '-',
  'revoke', 'next', 'save', '=', 'preview', 'fullscreen'
]

onMounted(async () => {
  await Promise.all([loadProfiles(), loadGroups(), loadGlobalMemoryFiles()])
})

watch(activeTab, () => {
  selectedId.value = null
  selectedFile.value = null
  memoryFiles.value = []
})

async function loadProfiles() {
  try {
    profiles.value = await api.getProfiles()
  } catch (e) {
    console.error('Failed to load profiles:', e)
  }
}

async function loadGroups() {
  try {
    groups.value = await api.getGroups()
  } catch (e) {
    console.error('Failed to load groups:', e)
  }
}

async function loadGlobalMemoryFiles() {
  try {
    globalMemoryFiles.value = await api.getGlobalMemoryFiles()
  } catch (e) {
    console.error('Failed to load global memory files:', e)
  }
}

async function selectProfile(uid: string) {
  selectedId.value = uid
  selectedFile.value = null
  await loadMemoryFiles()
}

async function selectGroup(gid: string) {
  selectedId.value = gid
  selectedFile.value = null
  await loadMemoryFiles()
}

async function loadMemoryFiles() {
  if (!selectedId.value) return

  try {
    if (activeTab.value === 'profiles') {
      memoryFiles.value = await api.getProfileMemory(selectedId.value)
    } else {
      memoryFiles.value = await api.getGroupMemory(selectedId.value)
    }
  } catch (e) {
    console.error('Failed to load memory files:', e)
    appStore.showSnackbar('加载记忆文件失败', 'error')
  }
}

async function selectFile(filename: string) {
  if (!selectedId.value) return

  selectedFile.value = filename
  try {
    let result
    if (activeTab.value === 'profiles') {
      result = await api.getMemoryFile(selectedId.value, filename)
    } else {
      result = await api.getGroupMemoryFile(selectedId.value, filename)
    }
    fileContent.value = result.content
  } catch (e) {
    console.error('Failed to load file:', e)
    appStore.showSnackbar('加载文件失败', 'error')
  }
}

async function saveFile() {
  if (!selectedId.value || !selectedFile.value) return

  saving.value = true
  try {
    if (activeTab.value === 'profiles') {
      await api.updateMemoryFile(selectedId.value, selectedFile.value, fileContent.value)
    } else {
      await api.updateGroupMemoryFile(selectedId.value, selectedFile.value, fileContent.value)
    }
    appStore.showSnackbar('保存成功', 'success')
  } catch (e) {
    console.error('Failed to save file:', e)
    appStore.showSnackbar('保存失败', 'error')
  } finally {
    saving.value = false
  }
}

async function deleteFile(filename: string) {
  if (!selectedId.value) return
  if (!confirm(`确定要删除文件 ${filename} 吗？`)) return

  try {
    if (activeTab.value === 'profiles') {
      await api.deleteMemoryFile(selectedId.value, filename)
    } else {
      await api.deleteGroupMemoryFile(selectedId.value, filename)
    }
    appStore.showSnackbar('删除成功', 'success')
    await loadMemoryFiles()
    if (selectedFile.value === filename) {
      selectedFile.value = null
    }
  } catch (e) {
    console.error('Failed to delete file:', e)
    appStore.showSnackbar('删除失败', 'error')
  }
}

// 全局记忆方法
async function selectGlobalFile(filename: string) {
  selectedGlobalFile.value = filename
  try {
    const result = await api.getGlobalMemoryContent(filename)
    globalFileContent.value = result.content
  } catch (e) {
    console.error('Failed to load global file:', e)
    appStore.showSnackbar('加载文件失败', 'error')
  }
}

async function saveGlobalFile() {
  if (!selectedGlobalFile.value) return
  
  if (!authStore.isSudo) {
    appStore.showSnackbar('需要 Sudo 权限才能编辑全局记忆', 'error')
    return
  }

  savingGlobal.value = true
  try {
    await api.updateGlobalMemory(selectedGlobalFile.value, globalFileContent.value)
    appStore.showSnackbar('保存成功', 'success')
    await loadGlobalMemoryFiles()
  } catch (e) {
    console.error('Failed to save global file:', e)
    appStore.showSnackbar('保存失败', 'error')
  } finally {
    savingGlobal.value = false
  }
}

function getGlobalFileColor(filename: string): string {
  const baseName = filename.replace('Global_', '').replace('.md', '')
  switch (baseName) {
    case 'SOUL':
      return 'purple'
    case 'MEMORY':
      return 'success'
    case 'HEARTBEAT':
      return 'warning'
    default:
      return 'primary'
  }
}

function getGlobalFileIcon(filename: string): string {
  const baseName = filename.replace('Global_', '').replace('.md', '')
  switch (baseName) {
    case 'SOUL':
      return 'mdi-heart'
    case 'MEMORY':
      return 'mdi-brain'
    case 'HEARTBEAT':
      return 'mdi-pulse'
    default:
      return 'mdi-file-document'
  }
}

function getGlobalFileLabel(filename: string): string {
  const baseName = filename.replace('Global_', '').replace('.md', '')
  switch (baseName) {
    case 'SOUL':
      return '核心人格'
    case 'MEMORY':
      return '共享记忆'
    case 'HEARTBEAT':
      return '临时指令'
    default:
      return ''
  }
}

function formatSize(bytes: number): string {
  if (bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
}
</script>

<style scoped>
.memory-editor {
  height: 500px;
}
</style>
