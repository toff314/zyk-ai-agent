import { describe, it, expect, vi, beforeEach } from 'vitest'
import { syncGitLabData, syncMySQLData } from './config'

const { postMock } = vi.hoisted(() => ({ postMock: vi.fn() }))

vi.mock('@/utils/request', () => {
  return {
    default: {
      get: vi.fn(),
      put: vi.fn(),
      post: postMock
    }
  }
})

beforeEach(() => {
  postMock.mockReset()
})

describe('config sync api', () => {
  it('calls gitlab sync endpoint', async () => {
    postMock.mockResolvedValue({ code: 0 })
    await syncGitLabData()
    expect(postMock).toHaveBeenCalledWith('/config/sync/gitlab')
  })

  it('calls mysql sync endpoint', async () => {
    postMock.mockResolvedValue({ code: 0 })
    await syncMySQLData()
    expect(postMock).toHaveBeenCalledWith('/config/sync/mysql')
  })
})
