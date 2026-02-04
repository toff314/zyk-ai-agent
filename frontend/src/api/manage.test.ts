import { describe, it, expect, vi, beforeEach } from 'vitest'
import {
  getGitlabProjects,
  getGitlabUsers,
  getGitlabBranches,
  getGitlabCommits,
  getMysqlDatabasesManage,
  getMysqlTablesManage
} from './manage'

const { getMock, patchMock } = vi.hoisted(() => {
  return {
    getMock: vi.fn(),
    patchMock: vi.fn()
  }
})

vi.mock('@/utils/request', () => {
  return {
    default: {
      get: getMock,
      patch: patchMock
    }
  }
})

beforeEach(() => {
  getMock.mockReset()
  patchMock.mockReset()
})

const mockPageResponse = {
  items: [],
  total: 0,
  page: 1,
  page_size: 20
}


describe('manage api pagination', () => {
  it('passes pagination params for gitlab projects', async () => {
    getMock.mockResolvedValue(mockPageResponse)
    await getGitlabProjects(true, 2, 50)

    expect(getMock).toHaveBeenCalledWith('/gitlab/projects', {
      params: { include_disabled: true, page: 2, page_size: 50 }
    })
  })

  it('passes pagination params for gitlab users', async () => {
    getMock.mockResolvedValue(mockPageResponse)
    await getGitlabUsers(true, 3, 20)

    expect(getMock).toHaveBeenCalledWith('/gitlab/users', {
      params: { include_disabled: true, page: 3, page_size: 20 }
    })
  })

  it('passes pagination params for gitlab branches', async () => {
    getMock.mockResolvedValue(mockPageResponse)
    await getGitlabBranches(10, false, 2, 10)

    expect(getMock).toHaveBeenCalledWith('/gitlab/branches', {
      params: { project_id: 10, refresh: false, page: 2, page_size: 10 }
    })
  })

  it('passes pagination params for gitlab commits', async () => {
    getMock.mockResolvedValue(mockPageResponse)
    await getGitlabCommits(10, 'main', false, 50, 1, 20)

    expect(getMock).toHaveBeenCalledWith('/gitlab/commits', {
      params: { project_id: 10, branch: 'main', refresh: false, limit: 50, page: 1, page_size: 20 }
    })
  })

  it('passes pagination params for mysql databases manage', async () => {
    getMock.mockResolvedValue(mockPageResponse)
    await getMysqlDatabasesManage(false, true, 2, 10)

    expect(getMock).toHaveBeenCalledWith('/mysql/manage/databases', {
      params: { refresh: false, include_disabled: true, page: 2, page_size: 10 }
    })
  })

  it('passes pagination params for mysql tables manage', async () => {
    getMock.mockResolvedValue(mockPageResponse)
    await getMysqlTablesManage('db_01', false, true, 3, 10)

    expect(getMock).toHaveBeenCalledWith('/mysql/manage/tables', {
      params: { database: 'db_01', refresh: false, include_disabled: true, page: 3, page_size: 10 }
    })
  })
})
