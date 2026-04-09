<template>
  <div>
    <h1 class="page-title">知识库</h1>
    <p class="page-subtitle">管理灵笔司书的知识库文档</p>

    <v-row>
      <v-col cols="12" md="6">
        <v-card>
          <v-card-title class="d-flex align-center">
            <v-icon class="mr-2" color="primary">mdi-book-open-variant</v-icon>
            知识库列表
            <v-spacer />
            <v-btn color="primary" variant="text" @click="loadKnowledge">
              <v-icon class="mr-1">mdi-refresh</v-icon>
              刷新
            </v-btn>
          </v-card-title>
          <v-card-text>
            <v-list v-if="knowledgeItems.length > 0" density="compact">
              <v-list-item
                v-for="item in knowledgeItems"
                :key="item.id"
                @click="openDetail(item)"
                class="cursor-pointer"
              >
                <template v-slot:prepend>
                  <v-avatar color="secondary" size="40">
                    <v-icon>mdi-lightbulb</v-icon>
                  </v-avatar>
                </template>
                <v-list-item-title>{{ item.title || item.content.substring(0, 50) }}</v-list-item-title>
                <v-list-item-subtitle>
                  类型: {{ item.knowledge_type }} · {{ item.tags?.join(', ') || '无标签' }}
                </v-list-item-subtitle>
                <template v-slot:append>
                  <div class="d-flex align-center gap-1">
                    <v-btn
                      icon="mdi-pencil"
                      variant="text"
                      size="x-small"
                      color="primary"
                      density="comfortable"
                      @click.stop="openEdit(item)"
                    />
                    <v-btn
                      v-show="authStore.isSudo"
                      icon="mdi-delete"
                      variant="text"
                      size="x-small"
                      color="error"
                      density="comfortable"
                      @click.stop="deleteItem(item.id)"
                    />
                  </div>
                </template>
              </v-list-item>
            </v-list>
            <v-empty-state
              v-else
              icon="mdi-book-off"
              title="暂无知识"
              text="知识库暂无文档，点击右侧添加"
            />
          </v-card-text>
        </v-card>
      </v-col>

      <v-col cols="12" md="6">
        <v-card>
          <v-card-title>
            <v-icon class="mr-2" color="primary">mdi-plus</v-icon>
            添加知识
          </v-card-title>
          <v-card-text>
            <v-text-field v-model="newItem.title" label="标题" class="mb-4" />
            <v-textarea v-model="newItem.content" label="内容" rows="4" class="mb-4" />
            <v-select
              v-model="newItem.knowledge_type"
              :items="['fact', 'rule', 'preference', 'reference']"
              label="类型"
              class="mb-4"
            />
            <v-text-field
              v-model="tagsInput"
              label="标签（逗号分隔）"
              hint="例如: 重要, 技术, 备注"
              class="mb-4"
            />
            <v-text-field v-model="newItem.category" label="分类" class="mb-4" />
            <v-btn color="primary" :loading="adding" @click="addItem">
              <v-icon class="mr-2">mdi-plus</v-icon>
              添加知识
            </v-btn>
            <v-alert
              v-if="!authStore.isSudo"
              type="info"
              variant="tonal"
              class="mt-4"
              density="compact"
            >
              需要 Sudo 权限才能添加/编辑/删除知识，请点击右上角 Sudo 按钮
            </v-alert>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>

    <!-- 详情对话框 -->
    <v-dialog v-model="detailDialog" fullscreen transition="dialog-bottom-transition">
      <v-card v-if="selectedItem">
        <v-toolbar dark color="primary">
          <v-btn icon dark @click="detailDialog = false">
            <v-icon>mdi-close</v-icon>
          </v-btn>
          <v-toolbar-title class="ml-4">
            <v-icon class="mr-2">mdi-lightbulb</v-icon>
            知识详情
          </v-toolbar-title>
          <v-spacer />
          <v-btn color="white" variant="text" @click="openEdit(selectedItem); detailDialog = false">
            <v-icon class="mr-1">mdi-pencil</v-icon>
            编辑
          </v-btn>
        </v-toolbar>
        <v-card-text class="pa-6">
          <v-container fluid>
            <v-row>
              <v-col cols="12">
                <v-text-field
                  v-model="selectedItem.title"
                  label="标题"
                  readonly
                  variant="filled"
                  class="mb-2"
                />
              </v-col>
            </v-row>
            <v-row>
              <v-col cols="12">
                <v-textarea
                  v-model="selectedItem.content"
                  label="内容"
                  rows="10"
                  readonly
                  variant="filled"
                  class="mb-2"
                  auto-grow
                />
              </v-col>
            </v-row>
            <v-row>
              <v-col cols="12" md="4">
                <v-text-field
                  v-model="selectedItem.knowledge_type"
                  label="类型"
                  readonly
                  variant="filled"
                />
              </v-col>
              <v-col cols="12" md="4">
                <v-text-field
                  v-model="selectedItem.category"
                  label="分类"
                  readonly
                  variant="filled"
                />
              </v-col>
              <v-col cols="12" md="4">
                <v-text-field
                  v-model="selectedItem.source"
                  label="来源"
                  readonly
                  variant="filled"
                />
              </v-col>
            </v-row>
            <v-row>
              <v-col cols="12">
                <v-text-field
                  v-model="tagsDisplay"
                  label="标签"
                  readonly
                  variant="filled"
                />
              </v-col>
            </v-row>
            <v-row>
              <v-col cols="12" md="4">
                <v-text-field
                  v-model="selectedItem.useful_count"
                  label="使用次数"
                  readonly
                  variant="filled"
                />
              </v-col>
              <v-col cols="12" md="4">
                <v-text-field
                  v-model="selectedItem.useful_score"
                  label="有用性评分"
                  readonly
                  variant="filled"
                />
              </v-col>
              <v-col cols="12" md="4">
                <v-switch
                  :model-value="selectedItem.is_active"
                  label="启用状态"
                  disabled
                  inset
                  color="success"
                />
              </v-col>
            </v-row>
            <v-row>
              <v-col cols="12" md="6">
                <v-text-field
                  v-model="selectedItem.created_at"
                  label="创建时间"
                  readonly
                  variant="filled"
                />
              </v-col>
              <v-col cols="12" md="6">
                <v-text-field
                  v-model="selectedItem.updated_at"
                  label="更新时间"
                  readonly
                  variant="filled"
                />
              </v-col>
            </v-row>
          </v-container>
        </v-card-text>
      </v-card>
    </v-dialog>

    <!-- 编辑对话框 -->
    <v-dialog v-model="editDialog" fullscreen transition="dialog-bottom-transition">
      <v-card v-if="editItem">
        <v-toolbar dark color="primary">
          <v-btn icon dark @click="editDialog = false">
            <v-icon>mdi-close</v-icon>
          </v-btn>
          <v-toolbar-title class="ml-4">
            <v-icon class="mr-2">mdi-pencil</v-icon>
            编辑知识
          </v-toolbar-title>
          <v-spacer />
          <v-btn color="white" variant="text" :loading="saving" @click="saveEdit">
            <v-icon class="mr-1">mdi-content-save</v-icon>
            保存
          </v-btn>
        </v-toolbar>
        <v-card-text class="pa-6">
          <v-container fluid>
            <v-row>
              <v-col cols="12">
                <v-text-field v-model="editItem.title" label="标题" />
              </v-col>
            </v-row>
            <v-row>
              <v-col cols="12">
                <v-textarea v-model="editItem.content" label="内容" rows="12" auto-grow />
              </v-col>
            </v-row>
            <v-row>
              <v-col cols="12" md="4">
                <v-select
                  v-model="editItem.knowledge_type"
                  :items="['fact', 'skill', 'preference', 'rule', 'experience', 'reference']"
                  label="类型"
                />
              </v-col>
              <v-col cols="12" md="4">
                <v-text-field
                  v-model="editTagsInput"
                  label="标签（逗号分隔）"
                  hint="例如: 重要, 技术, 备注"
                />
              </v-col>
              <v-col cols="12" md="4">
                <v-text-field v-model="editItem.category" label="分类" />
              </v-col>
            </v-row>
            <v-row>
              <v-col cols="12" md="6">
                <v-switch
                  v-model="editItem.is_active"
                  label="启用此条知识"
                  color="primary"
                  inset
                />
              </v-col>
              <v-col cols="12" md="6" class="d-flex align-center justify-end">
                <v-btn color="error" variant="outlined" @click="editDialog = false">
                  取消
                </v-btn>
              </v-col>
            </v-row>
          </v-container>
        </v-card-text>
      </v-card>
    </v-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useScriptorApi } from '@/composables/useScriptorApi'
import { useAppStore } from '@/stores/app'
import { useAuthStore } from '@/stores/auth'
import type { KnowledgeItem } from '@/types'

const api = useScriptorApi()
const appStore = useAppStore()
const authStore = useAuthStore()

const knowledgeItems = ref<KnowledgeItem[]>([])
const adding = ref(false)
const saving = ref(false)
const newItem = ref({
  title: '',
  content: '',
  knowledge_type: 'fact',
  category: ''
})
const tagsInput = ref('')

// 详情对话框
const detailDialog = ref(false)
const selectedItem = ref<KnowledgeItem | null>(null)

// 编辑对话框
const editDialog = ref(false)
const editItem = ref<KnowledgeItem | null>(null)
const editTagsInput = ref('')

const tagsDisplay = computed(() => {
  return selectedItem.value?.tags?.join(', ') || '无标签'
})

onMounted(() => {
  loadKnowledge()
})

async function loadKnowledge() {
  try {
    knowledgeItems.value = await api.getKnowledge()
  } catch (e) {
    console.error('Failed to load knowledge:', e)
    appStore.showSnackbar('加载知识库失败', 'error')
  }
}

function openDetail(item: KnowledgeItem) {
  selectedItem.value = { ...item }
  detailDialog.value = true
}

function openEdit(item: KnowledgeItem) {
  if (!authStore.isSudo) {
    appStore.showSnackbar('需要 Sudo 权限才能编辑', 'error')
    return
  }
  editItem.value = { ...item }
  editTagsInput.value = item.tags?.join(', ') || ''
  editDialog.value = true
}

async function saveEdit() {
  if (!editItem.value) return

  if (!editItem.value.content) {
    appStore.showSnackbar('内容不能为空', 'error')
    return
  }

  saving.value = true
  try {
    const tags = editTagsInput.value.split(',').map(s => s.trim()).filter(Boolean)
    await api.updateKnowledge(editItem.value.id, {
      title: editItem.value.title || '',
      content: editItem.value.content,
      knowledge_type: editItem.value.knowledge_type || 'fact',
      category: editItem.value.category || '',
      is_active: editItem.value.is_active ?? true,
      tags
    })
    appStore.showSnackbar('更新成功', 'success')
    editDialog.value = false
    await loadKnowledge()
  } catch (e: unknown) {
    console.error('Failed to update knowledge:', e)
    const errorDetail = e instanceof Error ? e.message :
      (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail || '更新失败'
    appStore.showSnackbar(`更新失败: ${errorDetail}`, 'error')
  } finally {
    saving.value = false
  }
}

async function addItem() {
  if (!authStore.isSudo) {
    appStore.showSnackbar('需要 Sudo 权限才能添加', 'error')
    return
  }

  if (!newItem.value.content) {
    appStore.showSnackbar('内容不能为空', 'error')
    return
  }

  adding.value = true
  try {
    const tags = tagsInput.value.split(',').map(s => s.trim()).filter(Boolean)
    await api.addKnowledge({
      ...newItem.value,
      tags
    })
    appStore.showSnackbar('添加成功', 'success')
    newItem.value = { title: '', content: '', knowledge_type: 'fact', category: '' }
    tagsInput.value = ''
    await loadKnowledge()
  } catch (e: unknown) {
    console.error('Failed to add knowledge:', e)
    const errorDetail = e instanceof Error ? e.message :
      (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail || '添加失败'
    appStore.showSnackbar(`添加失败: ${errorDetail}`, 'error')
  } finally {
    adding.value = false
  }
}

async function deleteItem(id: string) {
  if (!confirm('确定要删除这条知识吗？')) return

  try {
    await api.deleteKnowledge(id)
    appStore.showSnackbar('删除成功', 'success')
    await loadKnowledge()
  } catch (e: unknown) {
    console.error('Failed to delete knowledge:', e)
    const errorDetail = e instanceof Error ? e.message :
      (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail || '删除失败'
    appStore.showSnackbar(`删除失败: ${errorDetail}`, 'error')
  }
}
</script>

<style scoped>
.cursor-pointer {
  cursor: pointer;
}
</style>
