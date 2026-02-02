/**
 * 认证和用户管理相关API
 */
import request from '@/utils/request'
import type { LoginRequest, LoginResponse, User, CreateUserRequest } from '@/types'

/**
 * 用户登录
 */
export async function login(data: LoginRequest): Promise<LoginResponse> {
  return request.post<LoginResponse>('/auth/login', data)
}

/**
 * 用户登出
 */
export async function logout(): Promise<void> {
  return request.post('/auth/logout')
}

/**
 * 获取所有用户（管理员）
 */
export async function getUsers(): Promise<User[]> {
  return request.get<User[]>('/users')
}

/**
 * 创建用户（管理员）
 */
export async function createUser(data: CreateUserRequest): Promise<User> {
  return request.post<User>('/users', data)
}

/**
 * 删除用户（管理员）
 */
export async function deleteUser(userId: number): Promise<void> {
  return request.delete(`/users/${userId}`)
}

/**
 * 重置用户密码（管理员）
 */
export async function resetUserPassword(userId: number, data: { new_password: string }): Promise<void> {
  return request.post(`/users/${userId}/reset-password`, data)
}
