<template>
  <div>
    <h1 class="page-title">配置中心</h1>
    <p class="page-subtitle">管理系统配置参数</p>

    <v-card>
      <v-tabs v-model="activeTab" color="primary" class="border-b">
        <v-tab value="basic">基础设置</v-tab>
        <v-tab value="memory">记忆管理</v-tab>
        <v-tab value="embedding">嵌入与搜索</v-tab>
        <v-tab value="priority">提示词优先级</v-tab>
        <v-tab value="features">功能开关</v-tab>
        <v-tab value="websearch">网页搜索</v-tab>
        <v-tab value="smartsplit">智能分段</v-tab>
        <v-tab value="activereply">主动回复</v-tab>
        <v-tab value="media">媒体文件</v-tab>
      </v-tabs>

      <v-card-text class="pa-6">
        <v-window v-model="activeTab">
          <v-window-item value="basic">
            <ConfigSection title="基础设置">
              <v-row>
                <v-col cols="12" md="6">
                  <v-switch v-model="config.web_ui_enabled" label="启用 Web UI" hide-details />
                  <v-switch v-model="config.debug_mode" label="调试模式" hide-details class="mt-2" />
                </v-col>
                <v-col cols="12" md="6">
                  <v-text-field v-model.number="config.web_api_port" label="Web 服务端口" type="number" hint="前端和 API 共用此端口" />
                </v-col>
              </v-row>
            </ConfigSection>

            <ConfigSection title="登录密码">
              <v-row>
                <v-col cols="12" md="4">
                  <v-text-field v-model="currentPassword" label="当前密码" type="password" hint="请输入当前密码进行验证" />
                </v-col>
                <v-col cols="12" md="4">
                  <v-text-field v-model="newPassword" label="新密码" type="password" />
                </v-col>
                <v-col cols="12" md="4">
                  <v-text-field v-model="confirmPassword" label="确认密码" type="password" />
                </v-col>
              </v-row>
              <v-btn color="primary" @click="updatePassword" :loading="updatingPassword">
                修改密码
              </v-btn>
            </ConfigSection>
          </v-window-item>

          <v-window-item value="memory">
            <ConfigSection title="记忆管理">
              <v-row>
                <v-col cols="12" md="6">
                  <v-text-field
                    v-model.number="config.memory_compact_threshold"
                    label="记忆压缩阈值"
                    type="number"
                    hint="当记忆内容超过此字符数时触发压缩"
                  />
                  <v-switch v-model="config.daily_note_enabled" label="启用日记" hide-details class="mt-2" />
                  <v-switch v-model="config.cross_group_enabled" label="启用跨群功能" hide-details class="mt-2" />
                  <v-switch v-model="config.memory_encryption_enabled" label="启用记忆内容加密存储" hide-details class="mt-2" />
                </v-col>
                <v-col cols="12" md="6">
                  <v-text-field
                    v-model.number="config.memory_archive_score_cap"
                    label="记忆归档分数上限"
                    type="number"
                    step="0.5"
                    hint="控制记忆归档的严格程度"
                  />
                  <v-text-field
                    v-model.number="config.llm_extraction_threshold"
                    label="LLM记忆提取阈值"
                    type="number"
                    hint="累积多少条消息后触发LLM提取记忆"
                  />
                  <v-text-field
                    v-model.number="config.backup_retention_days"
                    label="备份文件保留天数"
                    type="number"
                  />
                </v-col>
              </v-row>
            </ConfigSection>

            <ConfigSection title="记忆反思">
              <v-row>
                <v-col cols="12" md="6">
                  <v-text-field
                    v-model.number="config.reflection_message_threshold"
                    label="反思消息阈值"
                    type="number"
                  />
                  <v-text-field
                    v-model.number="config.reflection_time_threshold"
                    label="反思时间阈值（秒）"
                    type="number"
                  />
                </v-col>
                <v-col cols="12" md="6">
                  <v-text-field
                    v-model.number="config.reflection_topic_threshold"
                    label="话题识别阈值"
                    type="number"
                    step="0.05"
                    min="0"
                    max="1"
                  />
                  <v-text-field
                    v-model.number="config.reflection_recent_messages_limit"
                    label="反思时考虑的最新消息数量"
                    type="number"
                  />
                </v-col>
              </v-row>
            </ConfigSection>
          </v-window-item>

          <v-window-item value="embedding">
            <ConfigSection title="嵌入设置">
              <v-row>
                <v-col cols="12" md="6">
                  <v-switch v-model="config.embedding_enabled" label="启用嵌入" hide-details />
                  <v-select
                    v-model="config.embedding_provider"
                    :items="['local', 'api']"
                    label="嵌入提供者"
                    class="mt-2"
                  />
                  <v-text-field v-model="config.embedding_model" label="嵌入模型" />
                </v-col>
                <v-col cols="12" md="6">
                  <v-text-field v-model="config.embedding_api_base" label="嵌入 API 地址" />
                  <v-text-field v-model="config.embedding_api_key" label="嵌入 API 密钥" type="password" />
                </v-col>
              </v-row>
            </ConfigSection>

            <ConfigSection title="搜索设置">
              <v-row>
                <v-col cols="12" md="6">
                  <v-text-field v-model.number="config.search_top_k" label="搜索返回结果数" type="number" />
                </v-col>
              </v-row>
            </ConfigSection>

            <ConfigSection title="重排设置">
              <v-row>
                <v-col cols="12" md="6">
                  <v-switch v-model="config.rerank_enabled" label="启用重排" hide-details />
                  <v-select
                    v-model="config.rerank_provider"
                    :items="['api', 'local']"
                    label="重排提供者"
                    class="mt-2"
                  />
                  <v-text-field v-model="config.rerank_model" label="重排模型" />
                </v-col>
                <v-col cols="12" md="6">
                  <v-text-field v-model="config.rerank_api_base" label="重排 API 地址" />
                  <v-text-field v-model="config.rerank_api_key" label="重排 API 密钥" type="password" />
                  <v-text-field v-model.number="config.rerank_top_k" label="重排返回结果数" type="number" />
                </v-col>
              </v-row>
            </ConfigSection>
          </v-window-item>

          <v-window-item value="priority">
            <ConfigSection title="Token 控制">
              <v-row>
                <v-col cols="12" md="6">
                  <v-switch v-model="config.enable_token_control" label="启用 Token 控制" hide-details />
                </v-col>
                <v-col cols="12" md="6">
                  <v-text-field
                    v-model.number="config.max_system_prompt_tokens"
                    label="最大系统提示词 Token"
                    type="number"
                  />
                </v-col>
              </v-row>
            </ConfigSection>

            <ConfigSection title="提示词优先级（1-20，数值越高优先级越高）">
              <v-row>
                <v-col cols="12" md="6">
                  <v-slider v-model="config.soul_priority" label="人设优先级" :min="1" :max="20" :step="1" thumb-label />
                  <v-slider v-model="config.agents_priority" label="代理/工具优先级" :min="1" :max="20" :step="1" thumb-label />
                  <v-slider v-model="config.profile_priority" label="用户档案优先级" :min="1" :max="20" :step="1" thumb-label />
                  <v-slider v-model="config.group_rules_priority" label="群规则优先级" :min="1" :max="20" :step="1" thumb-label />
                  <v-slider v-model="config.group_members_priority" label="群成员优先级" :min="1" :max="20" :step="1" thumb-label />
                </v-col>
                <v-col cols="12" md="6">
                  <v-slider v-model="config.cross_group_tasks_priority" label="跨群任务优先级" :min="1" :max="20" :step="1" thumb-label />
                  <v-slider v-model="config.recent_notes_priority" label="近期笔记优先级" :min="1" :max="20" :step="1" thumb-label />
                  <v-slider v-model="config.sop_priority" label="SOP 优先级" :min="1" :max="20" :step="1" thumb-label />
                  <v-slider v-model="config.retrieval_guidance_priority" label="检索指导优先级" :min="1" :max="20" :step="1" thumb-label />
                  <v-slider v-model="config.graph_recall_priority" label="知识图谱召回优先级" :min="1" :max="20" :step="1" thumb-label />
                </v-col>
              </v-row>
            </ConfigSection>

            <ConfigSection title="知识图谱">
              <v-row>
                <v-col cols="12" md="6">
                  <v-text-field v-model.number="config.graph_recall_limit" label="单次召回最大关系条数" type="number" />
                </v-col>
                <v-col cols="12" md="6">
                  <v-text-field v-model.number="config.graph_keyword_search_limit" label="每个关键词召回实体数量限制" type="number" />
                </v-col>
              </v-row>
            </ConfigSection>
          </v-window-item>

          <v-window-item value="features">
            <ConfigSection title="功能开关">
              <v-row>
                <v-col cols="12" md="4">
                  <v-switch v-model="config.message_sanitizer_enabled" label="消息清洗器" hide-details />
                  <v-switch v-model="config.message_buffer_enabled" label="消息缓冲器" hide-details class="mt-2" />
                  <v-switch v-model="config.tool_decoration_enabled" label="工具装饰器" hide-details class="mt-2" />
                </v-col>
                <v-col cols="12" md="4">
                  <v-switch v-model="config.session_locks_enabled" label="会话锁" hide-details />
                  <v-switch v-model="config.nightly_maintenance_enabled" label="夜间维护" hide-details class="mt-2" />
                </v-col>
                <v-col cols="12" md="4">
                  <v-text-field
                    v-model.number="config.nightly_maintenance_inactivity_minutes"
                    label="夜间维护无活动阈值（分钟）"
                    type="number"
                  />
                </v-col>
              </v-row>
            </ConfigSection>
          </v-window-item>

          <v-window-item value="websearch">
            <ConfigSection title="网页搜索">
              <v-row>
                <v-col cols="12" md="6">
                  <v-switch v-model="config.web_search_enabled" label="启用网页搜索工具" hide-details />
                  <v-text-field v-model="config.searxng_base_url" label="SearXNG 搜索引擎地址" class="mt-2" />
                  <v-text-field v-model="config.searxng_secret" label="SearXNG 密钥" type="password" />
                  <v-text-field v-model="config.searxng_default_engines" label="默认启用的搜索引擎" />
                </v-col>
                <v-col cols="12" md="6">
                  <v-text-field v-model.number="config.searxng_max_results" label="最大搜索结果数" type="number" />
                  <v-text-field v-model.number="config.searxng_timeout" label="请求超时时间（秒）" type="number" />
                  <v-switch v-model="config.search_archive_enabled" label="启用搜索结果归档" hide-details />
                  <v-text-field
                    v-model.number="config.search_archive_threshold"
                    label="归档判定阈值"
                    type="number"
                    step="0.05"
                    min="0.5"
                    max="0.95"
                  />
                </v-col>
              </v-row>
            </ConfigSection>
          </v-window-item>

          <v-window-item value="smartsplit">
            <ConfigSection title="智能分段发送">
              <v-row>
                <v-col cols="12" md="6">
                  <v-switch v-model="config.smart_split_enabled" label="启用智能分段发送" hide-details />
                  <v-switch v-model="config.smart_split_only_llm" label="仅对 LLM 结果进行分段" hide-details class="mt-2" />
                  <v-text-field v-model="config.smart_split_regex" label="智能分段正则表达式" />
                  <v-text-field v-model="config.smart_split_cleanup_regex" label="清理正则表达式" />
                  <v-text-field
                    v-model.number="config.smart_split_typing_speed"
                    label="模拟打字速度（秒/字符）"
                    type="number"
                    step="0.01"
                  />
                </v-col>
                <v-col cols="12" md="6">
                  <v-text-field v-model.number="config.smart_split_min_delay" label="分段最小延迟（秒）" type="number" step="0.1" />
                  <v-text-field v-model.number="config.smart_split_max_delay" label="分段最大延迟（秒）" type="number" step="0.1" />
                  <v-text-field v-model.number="config.smart_split_random_factor" label="延迟随机波动因子" type="number" step="0.05" />
                  <v-text-field v-model.number="config.smart_split_long_text_threshold" label="长文本判定阈值" type="number" />
                  <v-text-field v-model="config.smart_split_long_text_pattern" label="长文本分段正则" />
                  <v-switch v-model="config.smart_split_group_reply" label="群聊引用功能" hide-details />
                </v-col>
              </v-row>
            </ConfigSection>
          </v-window-item>

          <v-window-item value="activereply">
            <ConfigSection title="群聊主动回复">
              <v-row>
                <v-col cols="12" md="6">
                  <v-switch v-model="config.active_reply_enabled" label="启用群聊主动回复" hide-details />
                  <v-switch v-model="config.ar_name_wakeup" label="启用群内称呼唤醒" hide-details class="mt-2" />
                  <v-switch v-model="config.ar_task_sniffing" label="启用活跃任务嗅探" hide-details class="mt-2" />
                  <v-switch v-model="config.ar_continuous_dialogue" label="启用连续对话智能判定" hide-details class="mt-2" />
                  <v-text-field v-model.number="config.ar_debounce_seconds" label="防抖窗口时间（秒）" type="number" />
                  <v-text-field v-model.number="config.ar_max_queue_size" label="打包队列最大消息数" type="number" />
                </v-col>
                <v-col cols="12" md="6">
                  <v-text-field v-model.number="config.ar_attention_window_minutes" label="注意力窗口时间（分钟）" type="number" />
                  <v-text-field v-model.number="config.ar_attention_window_messages" label="注意力窗口消息条数上限" type="number" />
                  <v-text-field v-model="config.ar_intent_model_provider" label="意图判定小模型提供商ID" />
                  <v-text-field v-model.number="config.ar_context_messages" label="意图判定上下文消息数" type="number" />
                  <v-text-field v-model="config.ar_hard_stop_words" label="硬打断词列表" />
                </v-col>
              </v-row>
            </ConfigSection>
          </v-window-item>

          <v-window-item value="media">
            <ConfigSection title="媒体文件">
              <v-row>
                <v-col cols="12" md="6">
                  <v-switch v-model="config.media_auto_save_enabled" label="自动保存收到的图片和文件" hide-details />
                  <v-switch v-model="config.media_save_to_memory" label="保存媒体时自动生成图片描述" hide-details class="mt-2" />
                  <v-text-field v-model.number="config.media_max_image_size_mb" label="单张图片最大大小（MB）" type="number" />
                  <v-text-field v-model.number="config.media_max_file_size_mb" label="单个文件最大大小（MB）" type="number" />
                </v-col>
                <v-col cols="12" md="6">
                  <v-text-field v-model="config.media_allowed_file_types" label="允许保存的文件类型" />
                  <v-text-field v-model.number="config.media_retention_days" label="媒体文件保留天数（0=永久）" type="number" />
                </v-col>
              </v-row>
            </ConfigSection>

            <ConfigSection title="系统设置">
              <v-row>
                <v-col cols="12" md="6">
                  <v-text-field v-model="adminUidsInput" label="管理员UID列表" hint="逗号分隔" />
                </v-col>
                <v-col cols="12" md="6">
                  <v-text-field v-model.number="config.max_file_locks" label="文件锁缓存最大数量" type="number" />
                  <v-text-field v-model.number="config.index_cache_timeout" label="索引缓存超时时间（秒）" type="number" />
                </v-col>
              </v-row>
            </ConfigSection>
          </v-window-item>
        </v-window>

        <v-divider class="my-6" />

        <div class="d-flex justify-end ga-4">
          <v-btn variant="outlined" @click="discardChanges">
            撤销更改
          </v-btn>
          <v-btn variant="outlined" color="warning" @click="resetToDefault">
            恢复默认
          </v-btn>
          <v-btn color="primary" @click="saveConfig" :loading="saving">
            保存配置
          </v-btn>
        </div>
      </v-card-text>
    </v-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useScriptorApi } from '@/composables/useScriptorApi'
import { useAppStore } from '@/stores/app'
import type { Config } from '@/types'
import ConfigSection from '@/components/scriptor/ConfigSection.vue'

const api = useScriptorApi()
const appStore = useAppStore()

const activeTab = ref('basic')
const config = ref<Config>(getDefaultConfig())
const originalConfig = ref<Config>(getDefaultConfig())
const saving = ref(false)
const currentPassword = ref('')
const newPassword = ref('')
const confirmPassword = ref('')
const updatingPassword = ref(false)

const adminUidsInput = computed({
  get: () => (config.value.admin_uids || []).join(', '),
  set: (val: string) => {
    config.value.admin_uids = val.split(',').map(s => s.trim()).filter(Boolean)
  }
})

function getDefaultConfig(): Config {
  return {
    web_ui_enabled: true,
    web_api_port: 18111,
    debug_mode: true,
    memory_compact_threshold: 50000,
    daily_note_enabled: true,
    cross_group_enabled: true,
    memory_encryption_enabled: false,
    memory_archive_score_cap: 15.0,
    llm_extraction_threshold: 10,
    backup_retention_days: 7,
    reflection_message_threshold: 15,
    reflection_time_threshold: 1800,
    reflection_topic_threshold: 0.7,
    reflection_recent_messages_limit: 20,
    embedding_enabled: true,
    search_top_k: 5,
    embedding_provider: 'local',
    embedding_model: 'AI-ModelScope/bge-small-zh-v1.5',
    embedding_api_base: 'http://localhost:11434/v1',
    embedding_api_key: '',
    rerank_enabled: false,
    rerank_provider: 'api',
    rerank_model: 'bge-reranker-v2-m3',
    rerank_api_base: 'http://localhost:11434/v1',
    rerank_api_key: '',
    rerank_top_k: 5,
    enable_token_control: true,
    max_system_prompt_tokens: 100000,
    soul_priority: 10,
    agents_priority: 9,
    profile_priority: 8,
    group_rules_priority: 7,
    group_members_priority: 6,
    cross_group_tasks_priority: 5,
    recent_notes_priority: 4,
    sop_priority: 3,
    retrieval_guidance_priority: 2,
    graph_recall_priority: 10,
    graph_recall_limit: 15,
    graph_keyword_search_limit: 3,
    message_sanitizer_enabled: true,
    message_buffer_enabled: true,
    tool_decoration_enabled: true,
    session_locks_enabled: true,
    nightly_maintenance_enabled: true,
    nightly_maintenance_inactivity_minutes: 60,
    web_search_enabled: true,
    searxng_base_url: 'http://10.31.0.100:38080',
    searxng_secret: '',
    searxng_default_engines: 'google,bing,duckduckgo',
    searxng_max_results: 10,
    searxng_timeout: 10,
    search_archive_enabled: true,
    search_archive_threshold: 0.8,
    smart_split_enabled: true,
    smart_split_only_llm: true,
    smart_split_regex: '.*?(?:\\n+|[。？！~…]{2,})|.+$',
    smart_split_cleanup_regex: '^\\s+|\\s+$',
    smart_split_typing_speed: 0.08,
    smart_split_min_delay: 1.5,
    smart_split_max_delay: 3.5,
    smart_split_random_factor: 0.2,
    smart_split_long_text_threshold: 150,
    smart_split_long_text_pattern: '\\n{2,}',
    smart_split_group_reply: true,
    active_reply_enabled: false,
    ar_name_wakeup: true,
    ar_task_sniffing: false,
    ar_continuous_dialogue: true,
    ar_debounce_seconds: 3,
    ar_max_queue_size: 10,
    ar_attention_window_minutes: 2,
    ar_attention_window_messages: 10,
    ar_intent_model_provider: '',
    ar_context_messages: 10,
    ar_hard_stop_words: '退下，闭嘴，滚，消失，别说话，不用了，算了，没事了',
    media_auto_save_enabled: true,
    media_save_to_memory: false,
    media_max_image_size_mb: 20,
    media_max_file_size_mb: 20,
    media_allowed_file_types: 'txt,md,doc,docx,wps,xls,xlsx,et,csv,ppt,pptx,pdf,jpg,jpeg,png,gif,webp,bmp',
    media_retention_days: 30,
    admin_uids: [],
    max_file_locks: 100,
    index_cache_timeout: 300,
  }
}

onMounted(async () => {
  await loadConfig()
})

async function loadConfig() {
  try {
    const data = await api.getConfig()
    config.value = { ...getDefaultConfig(), ...data }
    originalConfig.value = { ...config.value }
  } catch (e) {
    console.error('Failed to load config:', e)
    appStore.showSnackbar('加载配置失败', 'error')
  }
}

async function saveConfig() {
  saving.value = true
  try {
    await api.updateConfig(config.value)
    originalConfig.value = { ...config.value }
    appStore.showSnackbar('配置已保存！请重启 AstrBot 使配置生效。', 'success')
  } catch (e) {
    console.error('Failed to save config:', e)
    appStore.showSnackbar('保存失败', 'error')
  } finally {
    saving.value = false
  }
}

function discardChanges() {
  config.value = { ...originalConfig.value }
  appStore.showSnackbar('已撤销未保存的更改', 'info')
}

function resetToDefault() {
  if (confirm('确定要恢复所有配置到默认值吗？此操作不可撤销。')) {
    config.value = { ...getDefaultConfig() }
    appStore.showSnackbar('已恢复默认配置，请点击保存生效', 'info')
  }
}

async function updatePassword() {
  if (!currentPassword.value) {
    appStore.showSnackbar('请输入当前密码', 'error')
    return
  }
  if (!newPassword.value) {
    appStore.showSnackbar('新密码不能为空', 'error')
    return
  }
  if (newPassword.value.length < 6) {
    appStore.showSnackbar('密码长度至少 6 位', 'error')
    return
  }
  if (newPassword.value !== confirmPassword.value) {
    appStore.showSnackbar('两次输入的密码不一致', 'error')
    return
  }

  updatingPassword.value = true
  try {
    await api.updatePassword(currentPassword.value, newPassword.value)
    api.setApiKey(newPassword.value)
    appStore.showSnackbar('密码已修改，立即生效！', 'success')
    currentPassword.value = ''
    newPassword.value = ''
    confirmPassword.value = ''
  } catch (e: unknown) {
    console.error('Failed to update password:', e)
    const errorDetail = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail
    appStore.showSnackbar(errorDetail || '修改失败', 'error')
  } finally {
    updatingPassword.value = false
  }
}
</script>
