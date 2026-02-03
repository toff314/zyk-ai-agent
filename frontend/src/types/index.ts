/**
 * 用户信息
 */
export interface User {
  id: number
  username: string
  role: 'admin' | 'user'
  created_at: string
  updated_at: string
}

/**
 * 对话信息
 */
export interface Conversation {
  id: number
  user_id: number
  title: string
  mode: 'normal' | 'data_analysis' | 'code_review'
  created_at: string
  updated_at: string
  message_count?: number
}

/**
 * 消息信息
 */
export interface Message {
  id: number
  conversation_id: number | null
  role: 'user' | 'assistant'
  content: string
  created_at: string
}

/**
 * API响应
 */
export interface ApiResponse<T = any> {
  code: number
  message?: string
  data?: T
}

/**
 * 登录请求
 */
export interface LoginRequest {
  username: string
  password: string
}

/**
 * 登录响应
 */
export interface LoginResponse {
  token: string
  user: User
}

/**
 * 用户创建请求
 */
export interface CreateUserRequest {
  username: string
  password: string
  role: 'admin' | 'user'
}

/**
 * @选择项
 */
export interface MentionItem {
  id: string | number
  name: string
  type: 'user' | 'database' | 'table'
  avatar_url?: string
  description?: string
}

// GitLab用户类型
export interface GitLabUser {
  id: number
  username: string
  name: string
  avatar_url: string
  commits_week: number
  commits_month: number
}

export interface MysqlDatabase {
  name: string
}

export interface MysqlTable {
  database: string
  name: string
  type?: string
  comment?: string
}

// 对话请求类型
export interface ChatRequest {
  message: string
  mode: 'normal' | 'data_analysis' | 'code_review'
  conversation_id?: number | null
}

// 流式响应类型
export interface StreamResponse {
  type: 'chunk' | 'done' | 'conversation_id' | 'error'
  content?: string
  id?: number
  error?: string
}
