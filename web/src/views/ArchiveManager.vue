<template>
  <div>
    <h1 class="page-title">档案馆</h1>
    <p class="page-subtitle">导入和管理大规模结构化数据， AI 将能够通过 SQL 实时查询这些数据</p>

    <v-tabs v-model="activeTab" class="mb-6">
      <v-tab value="list">馆藏管理</v-tab>
      <v-tab value="import">导入新档案</v-tab>
    </v-tabs>

    <v-window v-model="activeTab">
      <v-window-item value="list">
        <v-card>
          <v-card-title class="d-flex align-center">
            <v-icon class="mr-2" color="primary">mdi-database</v-icon>
            当前馆藏列表
            <v-spacer />
            <v-chip v-if="authStore.isSudo" color="error" size="small" class="mr-2">
              <v-icon start>mdi-shield-check</v-icon>
              管理模式
            </v-chip>
            <v-btn color="primary" variant="text" @click="loadArchives">
              <v-icon class="mr-1">mdi-refresh</v-icon>
              刷新
            </v-btn>
          </v-card-title>
          <v-card-text>
            <v-alert v-if="!authStore.isSudo" type="info" variant="tonal" class="mb-4">
              点击右上角 Sudo 按钮进入管理模式后，可进行删除、重命名、移动等管理操作。
            </v-alert>
            <template v-if="archives.length > 0">
              <v-expansion-panels v-model="expandedScope">
                <v-expansion-panel value="global">
                  <v-expansion-panel-title>
                    <v-icon class="mr-2" color="success">mdi-earth</v-icon>
                    全局档案库
                    <v-chip size="x-small" class="ml-2" color="success">
                      {{ globalArchives.length }}
                    </v-chip>
                  </v-expansion-panel-title>
                  <v-expansion-panel-text>
                    <v-list v-if="globalArchives.length > 0">
                      <v-list-item v-for="archive in globalArchives" :key="archive.table_name">
                        <template v-slot:prepend>
                          <v-avatar color="success" size="40">
                            <v-icon>mdi-database</v-icon>
                          </v-avatar>
                        </template>
                        <v-list-item-title class="d-flex align-center">
                          {{ archive.display_name }}
                          <v-chip size="x-small" color="success" class="ml-2">全局</v-chip>
                        </v-list-item-title>
                        <v-list-item-subtitle>
                          表名: {{ archive.table_name }} · {{ archive.row_count }} 条数据 · {{ archive.import_time }}
                        </v-list-item-subtitle>
                        <template v-slot:append>
                          <div class="d-flex align-center">
                            <v-btn variant="text" color="primary" size="small" class="mr-1" @click="openPreview(archive)">
                              <v-icon>mdi-eye</v-icon>
                              <v-tooltip activator="parent" location="bottom">预览</v-tooltip>
                            </v-btn>
                            <v-btn variant="text" color="secondary" size="small" class="mr-1" @click="exportArchive(archive, 'json')">
                              <v-icon>mdi-download</v-icon>
                              <v-tooltip activator="parent" location="bottom">导出 JSON</v-tooltip>
                            </v-btn>
                            <v-btn variant="text" color="secondary" size="small" class="mr-1" @click="exportArchive(archive, 'csv')">
                              <v-icon>mdi-file-delimited</v-icon>
                              <v-tooltip activator="parent" location="bottom">导出 CSV</v-tooltip>
                            </v-btn>
                            <v-menu v-if="authStore.isSudo">
                              <template v-slot:activator="{ props }">
                                <v-btn variant="text" size="small" v-bind="props">
                                  <v-icon>mdi-dots-vertical</v-icon>
                                </v-btn>
                              </template>
                              <v-list density="compact">
                                <v-list-item @click="openRenameDialog(archive)">
                                  <template v-slot:prepend>
                                    <v-icon>mdi-rename</v-icon>
                                  </template>
                                  <v-list-item-title>重命名</v-list-item-title>
                                </v-list-item>
                                <v-list-item @click="openMoveDialog(archive)">
                                  <template v-slot:prepend>
                                    <v-icon>mdi-folder-move</v-icon>
                                  </template>
                                  <v-list-item-title>移动到...</v-list-item-title>
                                </v-list-item>
                                <v-list-item @click="openCopyDialog(archive)">
                                  <template v-slot:prepend>
                                    <v-icon>mdi-content-copy</v-icon>
                                  </template>
                                  <v-list-item-title>复制到...</v-list-item-title>
                                </v-list-item>
                                <v-divider />
                                <v-list-item @click="deleteArchive(archive)" class="text-error">
                                  <template v-slot:prepend>
                                    <v-icon>mdi-delete</v-icon>
                                  </template>
                                  <v-list-item-title>删除</v-list-item-title>
                                </v-list-item>
                              </v-list>
                            </v-menu>
                          </div>
                        </template>
                      </v-list-item>
                    </v-list>
                    <v-empty-state v-else icon="mdi-database-off" title="暂无全局档案" text="" />
                  </v-expansion-panel-text>
                </v-expansion-panel>

                <v-expansion-panel value="group">
                  <v-expansion-panel-title>
                    <v-icon class="mr-2" color="warning">mdi-account-group</v-icon>
                    群组档案库
                    <v-chip size="x-small" class="ml-2" color="warning">
                      {{ groupArchives.length }}
                    </v-chip>
                  </v-expansion-panel-title>
                  <v-expansion-panel-text>
                    <v-list v-if="groupArchives.length > 0">
                      <v-list-item v-for="archive in groupArchives" :key="archive.table_name + archive.target_id">
                        <template v-slot:prepend>
                          <v-avatar color="warning" size="40">
                            <v-icon>mdi-database</v-icon>
                          </v-avatar>
                        </template>
                        <v-list-item-title class="d-flex align-center">
                          {{ archive.display_name }}
                          <v-chip size="x-small" color="warning" class="ml-2">群组: {{ archive.target_id }}</v-chip>
                        </v-list-item-title>
                        <v-list-item-subtitle>
                          表名: {{ archive.table_name }} · {{ archive.row_count }} 条数据 · {{ archive.import_time }}
                        </v-list-item-subtitle>
                        <template v-slot:append>
                          <div class="d-flex align-center">
                            <v-btn variant="text" color="primary" size="small" class="mr-1" @click="openPreview(archive)">
                              <v-icon>mdi-eye</v-icon>
                              <v-tooltip activator="parent" location="bottom">预览</v-tooltip>
                            </v-btn>
                            <v-btn variant="text" color="secondary" size="small" class="mr-1" @click="exportArchive(archive, 'json')">
                              <v-icon>mdi-download</v-icon>
                              <v-tooltip activator="parent" location="bottom">导出 JSON</v-tooltip>
                            </v-btn>
                            <v-btn variant="text" color="secondary" size="small" class="mr-1" @click="exportArchive(archive, 'csv')">
                              <v-icon>mdi-file-delimited</v-icon>
                              <v-tooltip activator="parent" location="bottom">导出 CSV</v-tooltip>
                            </v-btn>
                            <v-menu v-if="authStore.isSudo">
                              <template v-slot:activator="{ props }">
                                <v-btn variant="text" size="small" v-bind="props">
                                  <v-icon>mdi-dots-vertical</v-icon>
                                </v-btn>
                              </template>
                              <v-list density="compact">
                                <v-list-item @click="openRenameDialog(archive)">
                                  <template v-slot:prepend>
                                    <v-icon>mdi-rename</v-icon>
                                  </template>
                                  <v-list-item-title>重命名</v-list-item-title>
                                </v-list-item>
                                <v-list-item @click="openMoveDialog(archive)">
                                  <template v-slot:prepend>
                                    <v-icon>mdi-folder-move</v-icon>
                                  </template>
                                  <v-list-item-title>移动到...</v-list-item-title>
                                </v-list-item>
                                <v-list-item @click="openCopyDialog(archive)">
                                  <template v-slot:prepend>
                                    <v-icon>mdi-content-copy</v-icon>
                                  </template>
                                  <v-list-item-title>复制到...</v-list-item-title>
                                </v-list-item>
                                <v-divider />
                                <v-list-item @click="deleteArchive(archive)" class="text-error">
                                  <template v-slot:prepend>
                                    <v-icon>mdi-delete</v-icon>
                                  </template>
                                  <v-list-item-title>删除</v-list-item-title>
                                </v-list-item>
                              </v-list>
                            </v-menu>
                          </div>
                        </template>
                      </v-list-item>
                    </v-list>
                    <v-empty-state v-else icon="mdi-database-off" title="暂无群组档案" text="" />
                  </v-expansion-panel-text>
                </v-expansion-panel>

                <v-expansion-panel value="personal">
                  <v-expansion-panel-title>
                    <v-icon class="mr-2" color="primary">mdi-account</v-icon>
                    个人档案库
                    <v-chip size="x-small" class="ml-2" color="primary">
                      {{ personalArchives.length }}
                    </v-chip>
                  </v-expansion-panel-title>
                  <v-expansion-panel-text>
                    <v-list v-if="personalArchives.length > 0">
                      <v-list-item v-for="archive in personalArchives" :key="archive.table_name + archive.target_id">
                        <template v-slot:prepend>
                          <v-avatar color="primary" size="40">
                            <v-icon>mdi-database</v-icon>
                          </v-avatar>
                        </template>
                        <v-list-item-title class="d-flex align-center">
                          {{ archive.display_name }}
                          <v-chip size="x-small" color="primary" class="ml-2">用户: {{ archive.target_id }}</v-chip>
                        </v-list-item-title>
                        <v-list-item-subtitle>
                          表名: {{ archive.table_name }} · {{ archive.row_count }} 条数据 · {{ archive.import_time }}
                        </v-list-item-subtitle>
                        <template v-slot:append>
                          <div class="d-flex align-center">
                            <v-btn variant="text" color="primary" size="small" class="mr-1" @click="openPreview(archive)">
                              <v-icon>mdi-eye</v-icon>
                              <v-tooltip activator="parent" location="bottom">预览</v-tooltip>
                            </v-btn>
                            <v-btn variant="text" color="secondary" size="small" class="mr-1" @click="exportArchive(archive, 'json')">
                              <v-icon>mdi-download</v-icon>
                              <v-tooltip activator="parent" location="bottom">导出 JSON</v-tooltip>
                            </v-btn>
                            <v-btn variant="text" color="secondary" size="small" class="mr-1" @click="exportArchive(archive, 'csv')">
                              <v-icon>mdi-file-delimited</v-icon>
                              <v-tooltip activator="parent" location="bottom">导出 CSV</v-tooltip>
                            </v-btn>
                            <v-menu v-if="authStore.isSudo">
                              <template v-slot:activator="{ props }">
                                <v-btn variant="text" size="small" v-bind="props">
                                  <v-icon>mdi-dots-vertical</v-icon>
                                </v-btn>
                              </template>
                              <v-list density="compact">
                                <v-list-item @click="openRenameDialog(archive)">
                                  <template v-slot:prepend>
                                    <v-icon>mdi-rename</v-icon>
                                  </template>
                                  <v-list-item-title>重命名</v-list-item-title>
                                </v-list-item>
                                <v-list-item @click="openMoveDialog(archive)">
                                  <template v-slot:prepend>
                                    <v-icon>mdi-folder-move</v-icon>
                                  </template>
                                  <v-list-item-title>移动到...</v-list-item-title>
                                </v-list-item>
                                <v-list-item @click="openCopyDialog(archive)">
                                  <template v-slot:prepend>
                                    <v-icon>mdi-content-copy</v-icon>
                                  </template>
                                  <v-list-item-title>复制到...</v-list-item-title>
                                </v-list-item>
                                <v-divider />
                                <v-list-item @click="deleteArchive(archive)" class="text-error">
                                  <template v-slot:prepend>
                                    <v-icon>mdi-delete</v-icon>
                                  </template>
                                  <v-list-item-title>删除</v-list-item-title>
                                </v-list-item>
                              </v-list>
                            </v-menu>
                          </div>
                        </template>
                      </v-list-item>
                    </v-list>
                    <v-empty-state v-else icon="mdi-database-off" title="暂无个人档案" text="" />
                  </v-expansion-panel-text>
                </v-expansion-panel>
              </v-expansion-panels>
            </template>
            <v-empty-state
              v-else
              icon="mdi-database-off"
              title="暂无档案"
              text="档案馆目前空空如也，快去导入一些数据吧！"
            />
          </v-card-text>
        </v-card>
      </v-window-item>

      <v-window-item value="import">
        <v-card>
          <v-card-title>
            <v-icon class="mr-2" color="primary">mdi-upload</v-icon>
            导入数据档案
          </v-card-title>
          <v-card-text>
            <v-select
              v-model="importScope"
              :items="scopeOptions"
              label="导入目标层级"
              item-title="label"
              item-value="value"
              hint="选择档案存储的位置"
              class="mb-4"
            />

            <v-select
              v-if="importScope === 'personal'"
              v-model="targetUid"
              :items="profileOptions"
              label="选择目标用户"
              item-title="title"
              item-value="value"
              :loading="loadingProfiles"
              no-data-text="暂无用户数据"
              hint="留空则导入到当前登录用户的个人档案库"
              clearable
              class="mb-4"
              @click="loadProfilesAndGroups"
            />

            <v-select
              v-if="importScope === 'group'"
              v-model="targetGroupId"
              :items="groupOptions"
              label="选择目标群组"
              item-title="title"
              item-value="value"
              :loading="loadingGroups"
              no-data-text="暂无群组数据"
              class="mb-4"
              @click="loadProfilesAndGroups"
            />

            <v-file-input
              v-model="uploadFile"
              label="选择文件"
              accept=".xlsx,.xls,.csv,.txt"
              prepend-icon="mdi-file-document"
              show-size
              class="mb-4"
            />

            <v-text-field
              v-model="displayName"
              label="档案显示名称"
              class="mb-4"
            />

            <v-textarea
              v-model="description"
              label="档案描述"
              rows="2"
              hint="简要说明这份数据的内容，帮助 AI 更好地理解何时调用它"
              class="mb-4"
            />

            <v-text-field
              v-if="fileExt && ['xlsx', 'xls'].includes(fileExt)"
              v-model="sheetName"
              label="工作表名称 (Sheet Name)"
              hint="留空则导入第一个工作表"
              class="mb-4"
            />

            <v-text-field
              v-if="fileExt && ['csv', 'txt'].includes(fileExt)"
              v-model="delimiter"
              label="分隔符"
              hint="留空自动检测（支持: 制表符、逗号、分号、竖线、空格）"
              class="mb-4"
            />

            <v-alert
              v-if="!authStore.isSudo && importScope === 'global'"
              type="warning"
              variant="tonal"
              class="mb-4"
            >
              导入到全局档案馆需要 Sudo 权限。请先点击右上角的 Sudo 按钮进行验证。
            </v-alert>

            <v-btn
              color="primary"
              size="large"
              :loading="uploading"
              :disabled="!uploadFile || (!authStore.isSudo && importScope === 'global')"
              @click="uploadArchive"
            >
              <v-icon class="mr-2">mdi-upload</v-icon>
              开始导入
            </v-btn>

            <v-progress-linear
              v-if="uploadProgress > 0"
              :model-value="uploadProgress"
              class="mt-4"
              color="primary"
            />
          </v-card-text>
        </v-card>
      </v-window-item>
    </v-window>

    <v-dialog v-model="previewDialog" fullscreen transition="dialog-bottom-transition">
      <v-card v-if="previewData || previewArchive">
        <v-toolbar dark color="primary">
          <v-btn icon dark @click="previewDialog = false">
            <v-icon>mdi-close</v-icon>
          </v-btn>
          <v-toolbar-title class="ml-4">
            <v-icon class="mr-2">mdi-table</v-icon>
            {{ previewArchive?.display_name }} - 数据预览
          </v-toolbar-title>
          <v-chip :color="getScopeColor(previewArchive?.scope)" size="small" class="ml-4">
            {{ previewArchive?.scope_label || previewArchive?.scope }}
          </v-chip>
          <v-spacer />
          <v-btn color="white" variant="text" @click="exportArchive(previewArchive!, 'json')">
            <v-icon start>mdi-download</v-icon>
            JSON
          </v-btn>
          <v-btn color="white" variant="text" @click="exportArchive(previewArchive!, 'csv')">
            <v-icon start>mdi-file-delimited</v-icon>
            CSV
          </v-btn>
        </v-toolbar>
        <v-card-text class="pa-6" v-if="previewData">
          <v-container fluid>
            <v-row class="mb-4">
              <v-col cols="12">
                <v-chip class="mr-2">表名: {{ previewData.table_name }}</v-chip>
                <v-chip class="mr-2">共 {{ previewData.total_count }} 条数据</v-chip>
                <v-chip v-if="previewData.has_more" color="warning">
                  仅显示前 {{ previewData.limit }} 条
                </v-chip>
              </v-col>
            </v-row>
            <v-row>
              <v-col cols="12">
                <v-table density="compact" fixed-header class="elevation-1">
                  <thead>
                    <tr>
                      <th v-for="col in previewData.columns" :key="col" class="text-left font-weight-bold">
                        {{ col }}
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr v-for="(row, idx) in previewData.data" :key="idx">
                      <td v-for="col in previewData.columns" :key="col">
                        {{ formatCellValue(row[col]) }}
                      </td>
                    </tr>
                  </tbody>
                </v-table>
              </v-col>
            </v-row>
          </v-container>
        </v-card-text>
        <v-card-text v-else class="pa-6 text-center">
          <v-progress-circular indeterminate color="primary" size="64" />
          <p class="mt-4">正在加载数据...</p>
        </v-card-text>
      </v-card>
    </v-dialog>

    <v-dialog v-model="renameDialog" max-width="400">
      <v-card>
        <v-card-title>
          <v-icon class="mr-2">mdi-rename</v-icon>
          重命名档案
        </v-card-title>
        <v-card-text>
          <v-text-field
            v-model="renameNewName"
            label="新的显示名称"
            variant="outlined"
            :placeholder="renameArchive?.display_name"
          />
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn variant="text" @click="renameDialog = false">取消</v-btn>
          <v-btn color="primary" :loading="renameLoading" @click="doRename">确认</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <v-dialog v-model="moveDialog" max-width="450">
      <v-card>
        <v-card-title>
          <v-icon class="mr-2">mdi-folder-move</v-icon>
          移动档案
        </v-card-title>
        <v-card-text>
          <p class="text-body-2 mb-4">
            将 <strong>{{ moveArchiveData?.display_name }}</strong> 移动到：
          </p>
          <v-select
            v-model="moveTargetScope"
            :items="moveScopeOptions"
            label="目标层级"
            item-title="label"
            item-value="value"
            class="mb-4"
          />
          <v-select
            v-if="moveTargetScope === 'group'"
            v-model="moveTargetGroupId"
            :items="groupOptions"
            label="选择目标群组"
            item-title="title"
            item-value="value"
            :loading="loadingGroups"
            no-data-text="暂无群组数据"
          />
          <v-select
            v-if="moveTargetScope === 'personal'"
            v-model="moveTargetUid"
            :items="profileOptions"
            label="选择目标用户"
            item-title="title"
            item-value="value"
            :loading="loadingProfiles"
            no-data-text="暂无用户数据"
          />
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn variant="text" @click="moveDialog = false">取消</v-btn>
          <v-btn color="primary" :loading="moveLoading" :disabled="!canMove" @click="doMove">确认移动</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- 复制对话框 -->
    <v-dialog v-model="copyDialog" max-width="450">
      <v-card>
        <v-card-title>
          <v-icon class="mr-2">mdi-content-copy</v-icon>
          复制档案
        </v-card-title>
        <v-card-text>
          <p class="text-body-2 mb-4">
            将 <strong>{{ copyArchiveData?.display_name }}</strong> 复制到：
          </p>
          <v-select
            v-model="copyTargetScope"
            :items="copyScopeOptions"
            label="目标层级"
            item-title="label"
            item-value="value"
            class="mb-4"
          />
          <v-select
            v-if="copyTargetScope === 'group'"
            v-model="copyTargetGroupId"
            :items="groupOptions"
            label="选择目标群组"
            item-title="title"
            item-value="value"
            :loading="loadingGroups"
            no-data-text="暂无群组数据"
          />
          <v-select
            v-if="copyTargetScope === 'personal'"
            v-model="copyTargetUid"
            :items="profileOptions"
            label="选择目标用户"
            item-title="title"
            item-value="value"
            :loading="loadingProfiles"
            no-data-text="暂无用户数据"
          />
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn variant="text" @click="copyDialog = false">取消</v-btn>
          <v-btn color="primary" :loading="copyLoading" :disabled="!canCopy" @click="doCopy">确认复制</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useScriptorApi } from '@/composables/useScriptorApi'
import { useAppStore } from '@/stores/app'
import { useAuthStore } from '@/stores/auth'
import type { Archive } from '@/types'

const api = useScriptorApi()
const appStore = useAppStore()
const authStore = useAuthStore()

const activeTab = ref('list')
const archives = ref<Archive[]>([])
const uploadFile = ref<File | null>(null)
const displayName = ref('')
const description = ref('')
const sheetName = ref('')
const delimiter = ref('')
const uploading = ref(false)
const uploadProgress = ref(0)
const expandedScope = ref<string[]>(['global', 'group', 'personal'])

const importScope = ref('personal')
const targetUid = ref('')
const targetGroupId = ref('')

const previewDialog = ref(false)
const previewData = ref<{
  table_name: string
  columns: string[]
  data: Record<string, unknown>[]
  total_count: number
  limit: number
  offset: number
  has_more: boolean
} | null>(null)
const previewArchive = ref<Archive | null>(null)

const renameDialog = ref(false)
const renameArchive = ref<Archive | null>(null)
const renameNewName = ref('')
const renameLoading = ref(false)

const moveDialog = ref(false)
const moveArchiveData = ref<Archive | null>(null)
const moveTargetScope = ref('global')
const moveTargetGroupId = ref('')
const moveTargetUid = ref('')
const moveLoading = ref(false)

const copyDialog = ref(false)
const copyArchiveData = ref<Archive | null>(null)
const copyTargetScope = ref('global')
const copyTargetGroupId = ref('')
const copyTargetUid = ref('')
const copyLoading = ref(false)

const profiles = ref<{uid: string, name?: string}[]>([])
const groups = ref<{group_id: string, name?: string}[]>([])
const loadingProfiles = ref(false)
const loadingGroups = ref(false)

const scopeOptions = [
  { label: '👤 个人档案库', value: 'personal' },
  { label: '👥 群组档案库', value: 'group' },
  { label: '🌐 全局档案库 (需要 Sudo)', value: 'global' },
]

const copyScopeOptions = [
  { label: '🌐 全局档案库', value: 'global' },
  { label: '👥 群组档案库', value: 'group' },
  { label: '👤 个人档案库', value: 'personal' },
]

const moveScopeOptions = [
  { label: '🌐 全局档案库', value: 'global' },
  { label: '👥 群组档案库', value: 'group' },
  { label: '👤 个人档案库', value: 'personal' },
]

const fileExt = computed(() => {
  if (!uploadFile.value) return null
  return uploadFile.value.name.split('.').pop()?.toLowerCase()
})

const globalArchives = computed(() => archives.value.filter(a => a.scope === 'global'))
const groupArchives = computed(() => archives.value.filter(a => a.scope === 'group'))
const personalArchives = computed(() => archives.value.filter(a => a.scope === 'personal' || !a.scope))

const profileOptions = computed(() => 
  profiles.value.map(p => ({
    title: p.name ? `${p.name} (${p.uid})` : p.uid,
    value: p.uid
  }))
)

const groupOptions = computed(() => 
  groups.value.map(g => ({
    title: g.name ? `${g.name} (${g.group_id})` : g.group_id,
    value: g.group_id
  }))
)

const canMove = computed(() => {
  if (moveTargetScope.value === 'global') return true
  if (moveTargetScope.value === 'group') return !!moveTargetGroupId.value
  if (moveTargetScope.value === 'personal') return !!moveTargetUid.value
  return false
})

const canCopy = computed(() => {
  if (copyTargetScope.value === 'global') return true
  if (copyTargetScope.value === 'group') return !!copyTargetGroupId.value
  if (copyTargetScope.value === 'personal') return !!copyTargetUid.value
  return false
})

onMounted(() => {
  loadArchives()
})

async function loadArchives() {
  try {
    archives.value = await api.getArchives()
  } catch (e) {
    console.error('Failed to load archives:', e)
    appStore.showSnackbar('加载档案列表失败', 'error')
  }
}

async function uploadArchive() {
  if (!uploadFile.value) return

  if (importScope.value === 'global' && !authStore.isSudo) {
    appStore.showSnackbar('导入到全局档案馆需要 Sudo 权限', 'error')
    return
  }

  if (importScope.value === 'group' && !targetGroupId.value) {
    appStore.showSnackbar('请选择目标群组', 'error')
    return
  }

  uploading.value = true
  uploadProgress.value = 0

  try {
    const targetId = importScope.value === 'personal' 
      ? targetUid.value || undefined 
      : importScope.value === 'group' 
        ? targetGroupId.value 
        : undefined

    const result = await api.uploadArchive(
      uploadFile.value,
      displayName.value || uploadFile.value.name.replace(/\.[^.]+$/, ''),
      description.value,
      importScope.value,
      targetId,
      sheetName.value || undefined,
      delimiter.value || undefined,
      (percent) => { uploadProgress.value = percent }
    )
    appStore.showSnackbar(`导入成功！共导入 ${result.row_count} 条数据。`, 'success')
    activeTab.value = 'list'
    await loadArchives()
    resetForm()
  } catch (e: unknown) {
    console.error('Failed to upload archive:', e)
    const errorDetail = e instanceof Error ? e.message : 
      (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail || '导入失败'
    appStore.showSnackbar(`导入失败: ${errorDetail}`, 'error')
  } finally {
    uploading.value = false
  }
}

async function deleteArchive(archive: Archive) {
  if (!authStore.isSudo) {
    appStore.showSnackbar('删除档案需要 Sudo 权限', 'error')
    return
  }

  if (!confirm(`确定要删除档案 "${archive.display_name}" 吗？此操作不可恢复。`)) return

  try {
    // 传递 scope 和 target_id
    await api.deleteArchive(archive.table_name, archive.scope || 'global', archive.target_id)
    appStore.showSnackbar('删除成功', 'success')
    await loadArchives()
  } catch (e: unknown) {
    console.error('Failed to delete archive:', e)
    const errorDetail = e instanceof Error ? e.message : 
      (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail || '删除失败'
    appStore.showSnackbar(`删除失败：${errorDetail}`, 'error')
  }
}

async function openPreview(archive: Archive) {
  previewArchive.value = archive
  previewDialog.value = true
  previewData.value = null

  try {
    previewData.value = await api.previewArchive(
      archive.table_name,
      archive.scope || 'global',
      archive.target_id
    )
  } catch (e) {
    console.error('Failed to preview archive:', e)
    appStore.showSnackbar('预览失败', 'error')
    previewDialog.value = false
  }
}

function openRenameDialog(archive: Archive) {
  renameArchive.value = archive
  renameNewName.value = archive.display_name
  renameDialog.value = true
}

async function doRename() {
  if (!renameArchive.value || !renameNewName.value.trim()) return

  renameLoading.value = true
  try {
    await api.renameArchive(
      renameArchive.value.table_name,
      renameNewName.value.trim(),
      renameArchive.value.scope || 'global',
      renameArchive.value.target_id
    )
    appStore.showSnackbar('重命名成功', 'success')
    renameDialog.value = false
    await loadArchives()
  } catch (e) {
    console.error('Failed to rename archive:', e)
    appStore.showSnackbar('重命名失败', 'error')
  } finally {
    renameLoading.value = false
  }
}

function openMoveDialog(archive: Archive) {
  moveArchiveData.value = archive
  moveTargetScope.value = 'global'
  moveTargetGroupId.value = ''
  moveTargetUid.value = ''
  moveDialog.value = true
  loadProfilesAndGroups()
}

async function loadProfilesAndGroups() {
  loadingProfiles.value = true
  loadingGroups.value = true
  try {
    const [profilesData, groupsData] = await Promise.all([
      api.getProfiles(),
      api.getGroups()
    ])
    profiles.value = profilesData
    groups.value = groupsData
  } catch (e) {
    console.error('Failed to load profiles/groups:', e)
  } finally {
    loadingProfiles.value = false
    loadingGroups.value = false
  }
}

async function doMove() {
  if (!moveArchiveData.value || !canMove.value) return

  moveLoading.value = true
  try {
    const targetId = moveTargetScope.value === 'group' 
      ? moveTargetGroupId.value 
      : moveTargetScope.value === 'personal' 
        ? moveTargetUid.value 
        : undefined

    await api.moveArchive(
      moveArchiveData.value.table_name,
      moveTargetScope.value,
      targetId,
      moveArchiveData.value.scope || 'global',
      moveArchiveData.value.target_id
    )
    appStore.showSnackbar('移动成功', 'success')
    moveDialog.value = false
    await loadArchives()
  } catch (e: unknown) {
    console.error('Failed to move archive:', e)
    const errorDetail = e instanceof Error ? e.message : 
      (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail || '移动失败'
    appStore.showSnackbar(`移动失败: ${errorDetail}`, 'error')
  } finally {
    moveLoading.value = false
  }
}

function openCopyDialog(archive: Archive) {
  copyArchiveData.value = archive
  copyTargetScope.value = 'global'
  copyTargetGroupId.value = ''
  copyTargetUid.value = ''
  copyDialog.value = true
  loadProfilesAndGroups()
}

async function doCopy() {
  if (!copyArchiveData.value || !canCopy.value) return

  copyLoading.value = true
  try {
    const targetId = copyTargetScope.value === 'group' 
      ? copyTargetGroupId.value 
      : copyTargetScope.value === 'personal' 
        ? copyTargetUid.value 
        : undefined

    await api.copyArchive(
      copyArchiveData.value.table_name,
      copyTargetScope.value,
      targetId,
      copyArchiveData.value.scope || 'global',
      copyArchiveData.value.target_id
    )
    appStore.showSnackbar('复制成功', 'success')
    copyDialog.value = false
    await loadArchives()
  } catch (e: unknown) {
    console.error('Failed to copy archive:', e)
    const errorDetail = e instanceof Error ? e.message : 
      (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail || '复制失败'
    appStore.showSnackbar(`复制失败: ${errorDetail}`, 'error')
  } finally {
    copyLoading.value = false
  }
}

async function exportArchive(archive: Archive, format: 'json' | 'csv') {
  try {
    appStore.showSnackbar(`正在导出 ${format.toUpperCase()} 文件...`, 'info')
    const result = await api.exportArchive(
      archive.table_name,
      archive.scope || 'global',
      archive.target_id,
      format
    )
    const url = window.URL.createObjectURL(result.data)
    const link = document.createElement('a')
    link.href = url
    link.download = result.filename
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    window.URL.revokeObjectURL(url)
    appStore.showSnackbar(`导出成功`, 'success')
  } catch (e) {
    console.error('Failed to export archive:', e)
    appStore.showSnackbar('导出失败', 'error')
  }
}

function resetForm() {
  uploadFile.value = null
  displayName.value = ''
  description.value = ''
  sheetName.value = ''
  delimiter.value = ''
  uploadProgress.value = 0
  importScope.value = 'personal'
  targetUid.value = ''
  targetGroupId.value = ''
}

function getScopeColor(scope?: string): string {
  switch (scope) {
    case 'global':
      return 'success'
    case 'group':
      return 'warning'
    case 'personal':
    default:
      return 'primary'
  }
}

function formatCellValue(value: unknown): string {
  if (value === null || value === undefined) return ''
  if (typeof value === 'object') return JSON.stringify(value)
  return String(value)
}
</script>
