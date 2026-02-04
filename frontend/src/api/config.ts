/**
 * 配置管理API
 */
import request from '@/utils/request'

export interface ModelConfig {
  api_key: string
  base_url: string
  model: string
}

export interface GitLabConfig {
  url: string
  token: string
  groups: string
}

export interface MySQLConfig {
  host: string
  port: number
  user: string
  password: string
  database: string
}

export interface SyncResult {
  success: boolean
  message: string
}

export interface AppConfig {
  model_config?: ModelConfig
  gitlab_config?: GitLabConfig
  mcp_config?: any
}

/**
 * 获取所有配置
 */
export async function getConfig(): Promise<AppConfig> {
  const response = await request.get<{ code: number; data: AppConfig }>('/config')
  return response.data
}

/**
 * 更新模型配置
 */
export async function updateModelConfig(config: ModelConfig): Promise<void> {
  return request.put('/config/model', config)
}

/**
 * 更新GitLab配置
 */
export async function updateGitLabConfigWithSync(
  config: GitLabConfig
): Promise<{ code: number; message: string; sync?: SyncResult }> {
  return request.put('/config/gitlab', config)
}

/**
 * 测试模型配置
 */
export async function testModelConfig(config: ModelConfig): Promise<{ code: number; message: string; data?: { response: string } }> {
  return request.post('/config/test/model', config)
}

/**
 * 测试MySQL配置
 */
export async function testMySQLConfig(config: MySQLConfig): Promise<{ code: number; message: string; data?: { database_count: number } }> {
  return request.post('/config/test/mysql', config)
}

/**
 * 测试GitLab配置
 */
export async function testGitLabConfig(
  config: GitLabConfig
): Promise<{ code: number; message: string; data?: { user: { id?: number; username?: string; name?: string } } }> {
  return request.post('/config/test/gitlab', config)
}
/**
 * 更新MySQL配置（带返回类型）
 */
export async function updateMySQLConfigWithSync(config: MySQLConfig): Promise<{ code: number; message: string; sync?: SyncResult }> {
  return request.put('/config/mysql', config)
}

/**
 * 同步GitLab数据
 */
export async function syncGitLabData(): Promise<{ code: number; message: string; sync?: SyncResult }> {
  return request.post('/config/sync/gitlab')
}

/**
 * 同步MySQL数据
 */
export async function syncMySQLData(): Promise<{ code: number; message: string; sync?: SyncResult }> {
  return request.post('/config/sync/mysql')
}
