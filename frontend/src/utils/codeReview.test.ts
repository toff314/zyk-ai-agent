import { describe, it, expect } from 'vitest'
import { buildCodeReviewPayload } from './codeReview'

describe('buildCodeReviewPayload', () => {
  it('truncates large diff and sets notice', () => {
    const diff = 'a'.repeat(30000)
    const payload = buildCodeReviewPayload({
      title: 'commit-123',
      diff
    })

    expect(payload.review_diff.length).toBeLessThan(diff.length)
    expect(payload.review_notice).toContain('已截断')
    expect(payload.message).toContain('代码审查')
  })
})
