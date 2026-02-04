import request from '@/utils/request'

export interface PageResult<T> {
  items: T[]
  total: number
  page: number
  page_size: number
}

export interface MysqlDatabaseManage {
  id: number
  name: string
  remark?: string | null
  enabled: boolean
  table_count?: number
}

export interface MysqlTableManage {
  id: number
  database: string
  name: string
  type?: string
  comment?: string
  remark?: string | null
  enabled: boolean
}

export interface GitlabProjectManage {
  id: number
  name?: string
  path_with_namespace?: string
  web_url?: string
  last_activity_at?: string
  remark?: string | null
  enabled: boolean
  branch_count?: number
}

export interface GitlabUserManage {
  id: number
  username: string
  name?: string
  avatar_url?: string
  remark?: string | null
  enabled: boolean
  commits_week?: number
  commits_month?: number
}

export interface GitlabBranch {
  name: string
  commit_sha?: string
  committed_date?: string
}

export interface GitlabCommit {
  commit_sha: string
  title?: string
  author_name?: string
  created_at?: string
  web_url?: string
}

export interface GitlabCommitDiff {
  old_path?: string
  new_path?: string
  diff?: string
}

export async function getMysqlDatabasesManage(
  refresh = false,
  includeDisabled = true,
  page = 1,
  pageSize = 20
) {
  return request.get<PageResult<MysqlDatabaseManage>>('/mysql/manage/databases', {
    params: { refresh, include_disabled: includeDisabled, page, page_size: pageSize }
  })
}

export async function getMysqlTablesManage(
  database: string,
  refresh = false,
  includeDisabled = true,
  page = 1,
  pageSize = 20
) {
  return request.get<PageResult<MysqlTableManage>>('/mysql/manage/tables', {
    params: { database, refresh, include_disabled: includeDisabled, page, page_size: pageSize }
  })
}

export async function updateMysqlDatabaseManage(id: number, payload: { enabled?: boolean; remark?: string | null }) {
  return request.patch(`/mysql/manage/databases/${id}`, payload)
}

export async function updateMysqlTableManage(id: number, payload: { enabled?: boolean; remark?: string | null }) {
  return request.patch(`/mysql/manage/tables/${id}`, payload)
}

export async function getMysqlTableDetail(database: string, table: string) {
  return request.get<{ columns: any[] }>('/mysql/manage/table-detail', {
    params: { database, table }
  })
}

export async function getGitlabProjects(
  includeDisabled = true,
  page = 1,
  pageSize = 20
) {
  return request.get<PageResult<GitlabProjectManage>>('/gitlab/projects', {
    params: { include_disabled: includeDisabled, page, page_size: pageSize }
  })
}

export async function updateGitlabProject(id: number, payload: { enabled?: boolean; remark?: string | null }) {
  return request.patch(`/gitlab/projects/${id}`, payload)
}

export async function getGitlabUsers(
  includeDisabled = true,
  page = 1,
  pageSize = 20
) {
  return request.get<PageResult<GitlabUserManage>>('/gitlab/users', {
    params: { include_disabled: includeDisabled, page, page_size: pageSize }
  })
}

export async function updateGitlabUser(id: number, payload: { enabled?: boolean; remark?: string | null }) {
  return request.patch(`/gitlab/users/${id}`, payload)
}

export async function getGitlabBranches(
  projectId: number,
  refresh = false,
  page = 1,
  pageSize = 20
) {
  return request.get<PageResult<GitlabBranch>>('/gitlab/branches', {
    params: { project_id: projectId, refresh, page, page_size: pageSize }
  })
}

export async function getGitlabCommits(
  projectId: number,
  branch: string,
  refresh = false,
  limit = 50,
  page = 1,
  pageSize = 20
) {
  return request.get<PageResult<GitlabCommit>>('/gitlab/commits', {
    params: { project_id: projectId, branch, refresh, limit, page, page_size: pageSize }
  })
}

export async function getGitlabCommitDiffs(projectId: number, commit: string, refresh = false) {
  const response = await request.get<{ total: number; items: GitlabCommitDiff[] }>('/gitlab/commit-diffs', {
    params: { project_id: projectId, commit, refresh }
  })
  return response.items || []
}
