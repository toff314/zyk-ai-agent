/**
 * 对话相关API
 */
import request from '@/utils/request'
import type { Conversation, Message } from '@/types'

export interface ChatRequest {
  message: string
  mode: 'normal' | 'data_analysis' | 'code_review'
  conversation_id?: number
}

export interface ChatResponse {
  type: 'chunk' | 'done' | 'error' | 'conversation_id'
  content?: string
  id?: number
  error?: string
}

export interface ChatStats {
  total_conversations: number
  total_messages: number
  conversations_by_mode: {
    normal: number
    data_analysis: number
    code_review: number
  }
}

export interface GitLabUser {
  id: number
  username: string
  name: string
  avatar_url: string
  commits_week: number
  commits_month: number
}

/**
 * 流式对话
 */
export async function chatStream(
  data: ChatRequest,
  onMessage: (response: ChatResponse) => void,
  onError?: (error: Error) => void
): Promise<void> {
  const token = localStorage.getItem('token')
  
  try {
    const response = await fetch('http://localhost:8000/api/v1/chat/stream', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
      },
      body: JSON.stringify(data)
    })

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`)
    }

    const reader = response.body?.getReader()
    const decoder = new TextDecoder()

    if (!reader) {
      throw new Error('无法读取响应流')
    }

    while (true) {
      const { done, value } = await reader.read()
      
      if (done) break
      
      const chunk = decoder.decode(value)
      const lines = chunk.split('\n')
      
      for (const line of lines) {
        if (line.startsWith('data: ')) {
          const dataStr = line.slice(6)
          if (dataStr.trim()) {
            try {
              const jsonData = JSON.parse(dataStr)
              onMessage(jsonData)
            } catch (e) {
              console.error('解析响应失败:', e)
            }
          }
        }
      }
    }
  } catch (error) {
    console.error('流式对话出错:', error)
    if (onError) {
      onError(error as Error)
    } else {
      throw error
    }
  }
}

/**
 * 获取对话列表
 */
export async function getConversations(): Promise<Conversation[]> {
  return request.get<Conversation[]>('/conversations')
}

/**
 * 获取对话中的消息列表
 */
export async function getMessages(conversationId: number): Promise<Message[]> {
  return request.get<Message[]>(`/conversations/${conversationId}/messages`)
}

/**
 * 删除对话
 */
export async function deleteConversation(conversationId: number): Promise<void> {
  return request.delete(`/conversations/${conversationId}`)
}

/**
 * 获取GitLab用户列表
 */
export async function getGitLabUsers(): Promise<GitLabUser[]> {
  return request.get<GitLabUser[]>('/chat/gitlab/users')
}

/**
 * 获取聊天统计
 */
export async function getChatStats(): Promise<ChatStats> {
  return request.get<ChatStats>('/chat/stats')
}
