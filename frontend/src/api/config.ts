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
}

export interface MySQLConfig {
  host: string
  port: number
  user: string
  password: string
  database: string
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
export async function updateGitLabConfig(config: GitLabConfig): Promise<void> {
  return request.put('/config/gitlab', config)
}

/**
 * 更新MySQL配置
 */
export async function updateMySQLConfig(config: MySQLConfig): Promise<void> {
  return request.put('/config/mysql', config)
}

/**
 * 测试模型配置
 */
export async function testModelConfig(config: ModelConfig): Promise<{ code: number; message: string; data?: { response: string } }> {
  return request.post('/config/test/model', config)
}
