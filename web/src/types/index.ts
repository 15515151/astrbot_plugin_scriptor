export interface StatusResponse {
  status: string
  initialized: boolean
  data_dir: string
  profiles_count: number
  groups_count: number
  total_memory_files: number
  timestamp: string
  debug?: {
    api_key_loaded: boolean
    api_key_fingerprint: string
    key_dir: string
    password_file_exists: boolean
    key_file_exists: boolean
    env_key_set: boolean
  }
}

export interface SudoStatus {
  is_sudo: boolean
  timeout_minutes: number
  remaining_seconds: number
}

export interface GlobalMemoryFile {
  filename: string
  size: number
  modified: string | null
  exists: boolean
}

export interface GlobalMemoryContent {
  content: string
  exists: boolean
}

export interface Profile {
  uid: string
  name?: string
}

export interface Group {
  group_id: string
  name?: string
}

export interface MemoryFile {
  filename: string
  size: number
  modified: number
  modified_str: string
}

export interface Archive {
  table_name: string
  display_name: string
  description?: string
  row_count: number
  import_time: string
  columns_json: string
  scope?: string
  scope_label?: string
  target_id?: string
  db_path?: string
}

export interface KnowledgeItem {
  id: string
  title?: string
  content: string
  knowledge_type: string
  tags?: string[]
  category?: string
  is_active?: boolean
  source?: string
  useful_count?: number
  useful_score?: number
  created_at?: string
  updated_at?: string
}

export interface Config {
  web_ui_enabled: boolean
  web_api_port: number
  debug_mode: boolean
  memory_compact_threshold: number
  daily_note_enabled: boolean
  cross_group_enabled: boolean
  memory_encryption_enabled: boolean
  memory_archive_score_cap: number
  llm_extraction_threshold: number
  backup_retention_days: number
  reflection_message_threshold: number
  reflection_time_threshold: number
  reflection_topic_threshold: number
  reflection_recent_messages_limit: number
  embedding_enabled: boolean
  search_top_k: number
  embedding_provider: string
  embedding_model: string
  embedding_api_base: string
  embedding_api_key: string
  rerank_enabled: boolean
  rerank_provider: string
  rerank_model: string
  rerank_api_base: string
  rerank_api_key: string
  rerank_top_k: number
  enable_token_control: boolean
  max_system_prompt_tokens: number
  soul_priority: number
  agents_priority: number
  profile_priority: number
  group_rules_priority: number
  group_members_priority: number
  cross_group_tasks_priority: number
  recent_notes_priority: number
  sop_priority: number
  retrieval_guidance_priority: number
  graph_recall_priority: number
  graph_recall_limit: number
  graph_keyword_search_limit: number
  message_sanitizer_enabled: boolean
  message_buffer_enabled: boolean
  tool_decoration_enabled: boolean
  session_locks_enabled: boolean
  nightly_maintenance_enabled: boolean
  nightly_maintenance_inactivity_minutes: number
  web_search_enabled: boolean
  searxng_base_url: string
  searxng_secret: string
  searxng_default_engines: string
  searxng_max_results: number
  searxng_timeout: number
  search_archive_enabled: boolean
  search_archive_threshold: number
  smart_split_enabled: boolean
  smart_split_only_llm: boolean
  smart_split_regex: string
  smart_split_cleanup_regex: string
  smart_split_typing_speed: number
  smart_split_min_delay: number
  smart_split_max_delay: number
  smart_split_random_factor: number
  smart_split_long_text_threshold: number
  smart_split_long_text_pattern: string
  smart_split_group_reply: boolean
  active_reply_enabled: boolean
  ar_name_wakeup: boolean
  ar_task_sniffing: boolean
  ar_continuous_dialogue: boolean
  ar_debounce_seconds: number
  ar_max_queue_size: number
  ar_attention_window_minutes: number
  ar_attention_window_messages: number
  ar_intent_model_provider: string
  ar_context_messages: number
  ar_hard_stop_words: string
  media_auto_save_enabled: boolean
  media_save_to_memory: boolean
  media_max_image_size_mb: number
  media_max_file_size_mb: number
  media_allowed_file_types: string
  media_retention_days: number
  admin_uids: string[]
  max_file_locks: number
  index_cache_timeout: number
  [key: string]: unknown
}

export interface PerformanceStats {
  cpu_percent: number
  memory_usage_mb: number
  db_size_mb: number
  history?: number[]
}

export interface LogResult {
  content: string
  total_lines: number
  returned_lines: number
}

export interface LogsResponse {
  results: Record<string, LogResult | { error: string } | { hint: string; content?: string }>
}
