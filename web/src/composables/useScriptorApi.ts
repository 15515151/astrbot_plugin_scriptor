import axios, { type AxiosInstance } from 'axios'
import type {
  StatusResponse,
  Profile,
  Group,
  MemoryFile,
  Archive,
  KnowledgeItem,
  Config,
  PerformanceStats,
  LogsResponse,
  SudoStatus,
  GlobalMemoryFile,
  GlobalMemoryContent,
} from '@/types'

const API_BASE = '/api'

class ScriptorApi {
  private client: AxiosInstance
  private apiKey: string | null = null
  private csrfToken: string | null = null
  private sessionId: string = ''

  constructor() {
    this.client = axios.create({
      baseURL: API_BASE,
      timeout: 30000,
      headers: {
        'Content-Type': 'application/json',
      },
    })

    this.sessionId = this.generateSessionId()

    this.client.interceptors.request.use(async (config) => {
      if (this.apiKey) {
        config.headers['X-API-Key'] = this.apiKey
      }
      
      config.headers['X-Session-ID'] = this.sessionId
      
      if (['post', 'put', 'patch', 'delete'].includes(config.method?.toLowerCase() || '')) {
        if (!this.csrfToken) {
          await this.fetchCsrfToken()
        }
        if (this.csrfToken) {
          config.headers['X-CSRF-Token'] = this.csrfToken
        }
      }
      
      return config
    })

    this.client.interceptors.response.use(
      (response) => response,
      async (error) => {
        if (error.response?.status === 401) {
          this.clearApiKey()
        }
        if (error.response?.status === 403 && error.response?.data?.detail?.includes('CSRF')) {
          this.csrfToken = null
        }
        return Promise.reject(error)
      }
    )
  }

  private generateSessionId(): string {
    let sessionId = localStorage.getItem('scriptor_session_id')
    if (!sessionId) {
      sessionId = 'session_' + Math.random().toString(36).substring(2, 15) + Date.now().toString(36)
      localStorage.setItem('scriptor_session_id', sessionId)
    }
    return sessionId
  }

  private async fetchCsrfToken(): Promise<void> {
    try {
      const response = await this.client.get('/csrf/token')
      this.csrfToken = response.data.csrf_token
    } catch (e) {
      console.warn('Failed to fetch CSRF token:', e)
    }
  }

  setApiKey(key: string) {
    this.apiKey = key
    localStorage.setItem('scriptor_api_key', key)
  }

  getApiKey(): string | null {
    if (!this.apiKey) {
      this.apiKey = localStorage.getItem('scriptor_api_key')
    }
    return this.apiKey
  }

  clearApiKey() {
    this.apiKey = null
    localStorage.removeItem('scriptor_api_key')
  }

  isAuthenticated(): boolean {
    return !!this.getApiKey()
  }

  async verifyApiKey(): Promise<boolean> {
    try {
      await this.client.get('/status')
      return true
    } catch {
      return false
    }
  }

  async getSetupStatus(): Promise<{ needs_setup: boolean; has_password: boolean; has_temp_key: boolean }> {
    const response = await this.client.get('/setup/status')
    return response.data
  }

  async setupFirstPassword(password: string): Promise<void> {
    await this.client.post('/setup/password', { password })
  }

  async getStatus(): Promise<StatusResponse> {
    const response = await this.client.get('/status')
    return response.data
  }

  async getProfiles(): Promise<Profile[]> {
    const response = await this.client.get('/profiles')
    return response.data
  }

  async getProfileDetail(uid: string): Promise<{ uid: string; files: Record<string, string> }> {
    const response = await this.client.get(`/profiles/${uid}`)
    return response.data
  }

  async getProfileMemory(uid: string): Promise<MemoryFile[]> {
    const response = await this.client.get(`/profiles/${uid}/memory`)
    return response.data
  }

  async getMemoryFile(uid: string, filename: string): Promise<{ content: string }> {
    const response = await this.client.get(`/profiles/${uid}/memory/${filename}`)
    return response.data
  }

  async updateMemoryFile(uid: string, filename: string, content: string): Promise<void> {
    await this.client.put(`/profiles/${uid}/memory/${filename}`, { content })
  }

  async deleteMemoryFile(uid: string, filename: string): Promise<void> {
    await this.client.delete(`/profiles/${uid}/memory/${filename}`)
  }

  async getGroups(): Promise<Group[]> {
    const response = await this.client.get('/groups')
    return response.data
  }

  async getGroupMemory(gid: string): Promise<MemoryFile[]> {
    const response = await this.client.get(`/groups/${gid}/memory`)
    return response.data
  }

  async getGroupMemoryFile(gid: string, filename: string): Promise<{ content: string }> {
    const response = await this.client.get(`/groups/${gid}/memory/${filename}`)
    return response.data
  }

  async updateGroupMemoryFile(gid: string, filename: string, content: string): Promise<void> {
    await this.client.put(`/groups/${gid}/memory/${filename}`, { content })
  }

  async deleteGroupMemoryFile(gid: string, filename: string): Promise<void> {
    await this.client.delete(`/groups/${gid}/memory/${filename}`)
  }

  async getConfig(): Promise<Config> {
    const response = await this.client.get('/config')
    return response.data
  }

  async updateConfig(config: Partial<Config>): Promise<void> {
    await this.client.put('/config', { config })
  }

  async getArchives(): Promise<Archive[]> {
    const response = await this.client.get('/archives')
    return response.data
  }

  async uploadArchive(
    file: File,
    displayName: string,
    description: string,
    scope: string = 'personal',
    targetId?: string,
    sheetName?: string,
    delimiter?: string,
    onProgress?: (percent: number) => void
  ): Promise<{ row_count: number }> {
    const formData = new FormData()
    formData.append('file', file)
    formData.append('display_name', displayName)
    formData.append('description', description)
    formData.append('scope', scope)
    if (targetId) formData.append('target_id', targetId)
    if (sheetName) formData.append('sheet_name', sheetName)
    if (delimiter) formData.append('delimiter', delimiter)

    const response = await this.client.post('/archives/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
      onUploadProgress: (progressEvent) => {
        if (progressEvent.total && onProgress) {
          onProgress(Math.round((progressEvent.loaded * 100) / progressEvent.total))
        }
      },
    })
    return response.data
  }

  async deleteArchive(
    tableName: string,
    scope: string = 'global',
    targetId?: string
  ): Promise<void> {
    const params: Record<string, string> = { scope }
    if (targetId) params.target_id = targetId
    await this.client.delete(`/archives/${tableName}`, { params })
  }

  async previewArchive(
    tableName: string,
    scope: string = 'global',
    targetId?: string,
    limit: number = 50,
    offset: number = 0
  ): Promise<{
    table_name: string
    columns: string[]
    data: Record<string, unknown>[]
    total_count: number
    limit: number
    offset: number
    has_more: boolean
  }> {
    const params: Record<string, string | number> = { scope, limit, offset }
    if (targetId) params.target_id = targetId
    const response = await this.client.get(`/archives/${tableName}/preview`, { params })
    return response.data
  }

  async renameArchive(
    tableName: string,
    newDisplayName: string,
    scope: string = 'global',
    targetId?: string
  ): Promise<{ status: string; message: string }> {
    const params: Record<string, string> = { scope }
    if (targetId) params.target_id = targetId
    const response = await this.client.put(`/archives/${tableName}/rename`, { new_display_name: newDisplayName }, { params })
    return response.data
  }

  async moveArchive(
    tableName: string,
    targetScope: string,
    targetId?: string,
    sourceScope: string = 'global',
    sourceTargetId?: string
  ): Promise<{ status: string; message: string }> {
    const params: Record<string, string> = { scope: sourceScope }
    if (sourceTargetId) params.target_id = sourceTargetId
    const body: { target_scope: string; target_id?: string } = { target_scope: targetScope }
    if (targetId) body.target_id = targetId
    const response = await this.client.post(`/archives/${tableName}/move`, body, { params })
    return response.data
  }

  async copyArchive(
    tableName: string,
    targetScope: string,
    targetId?: string,
    sourceScope: string = 'global',
    sourceTargetId?: string
  ): Promise<{ status: string; message: string }> {
    const params: Record<string, string> = { scope: sourceScope }
    if (sourceTargetId) params.target_id = sourceTargetId
    const body: { target_scope: string; target_id?: string } = { target_scope: targetScope }
    if (targetId) body.target_id = targetId
    const response = await this.client.post(`/archives/${tableName}/copy`, body, { params })
    return response.data
  }

  async exportArchive(
    tableName: string,
    scope: string = 'global',
    targetId?: string,
    format: string = 'json'
  ): Promise<{ data: Blob; filename: string }> {
    const params: Record<string, string> = { scope, format }
    if (targetId) params.target_id = targetId
    const response = await this.client.get(`/archives/${tableName}/export`, {
      params,
      responseType: 'blob'
    })
    const contentDisposition = response.headers['content-disposition']
    let filename = `${tableName}.${format}`
    if (contentDisposition) {
      const match = contentDisposition.match(/filename="?(.+?)"?$/)
      if (match) filename = match[1]
    }
    return { data: response.data, filename }
  }

  async getKnowledge(): Promise<KnowledgeItem[]> {
    const response = await this.client.get('/knowledge')
    return response.data
  }

  async getKnowledgeItem(id: string): Promise<KnowledgeItem> {
    const response = await this.client.get(`/knowledge/${id}`)
    return response.data
  }

  async addKnowledge(item: { title: string; content: string; knowledge_type: string; tags?: string[]; category?: string }): Promise<{ id: string }> {
    const response = await this.client.post('/knowledge', item)
    return response.data
  }

  async updateKnowledge(id: string, item: { title: string; content: string; knowledge_type: string; tags?: string[]; category?: string; is_active?: boolean }): Promise<{ id: string }> {
    const response = await this.client.put(`/knowledge/${id}`, item)
    return response.data
  }

  async deleteKnowledge(id: string): Promise<void> {
    await this.client.delete(`/knowledge/${id}`)
  }

  async getPerformanceStats(): Promise<PerformanceStats> {
    const response = await this.client.get('/performance/stats')
    return response.data
  }

  async getLogs(lines: number = 100, source: string = 'all'): Promise<LogsResponse> {
    const response = await this.client.get('/logs', { params: { lines, source } })
    return response.data
  }

  async createBackup(): Promise<void> {
    await this.client.post('/maintenance/backup')
  }

  async cleanup(): Promise<void> {
    await this.client.post('/maintenance/cleanup')
  }

  async updatePassword(currentPassword: string, newPassword: string): Promise<void> {
    await this.client.put('/password', { current_password: currentPassword, password: newPassword })
  }

  // Sudo 相关 API
  async getSudoStatus(): Promise<SudoStatus> {
    const response = await this.client.get('/sudo/status')
    return response.data
  }

  async verifySudo(password: string): Promise<{ status: string; message: string; timeout_minutes: number }> {
    const response = await this.client.post('/sudo/verify', { password })
    return response.data
  }

  async exitSudo(): Promise<{ status: string; message: string }> {
    const response = await this.client.post('/sudo/exit')
    return response.data
  }

  // 全局记忆管理 API
  async getGlobalMemoryFiles(): Promise<GlobalMemoryFile[]> {
    const response = await this.client.get('/global/memory')
    return response.data
  }

  async getGlobalMemoryContent(filename: string): Promise<GlobalMemoryContent> {
    const response = await this.client.get(`/global/memory/${filename}`)
    return response.data
  }

  async updateGlobalMemory(filename: string, content: string): Promise<{ status: string; message: string }> {
    const response = await this.client.put(`/global/memory/${filename}`, { content })
    return response.data
  }
}

export const scriptorApi = new ScriptorApi()

export function useScriptorApi() {
  return scriptorApi
}
