import { describe, it, expect } from 'vitest'
import { buildCodeReviewPayload, buildDiffContent } from './codeReview'

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

describe('buildDiffContent', () => {
  it('formats diffs with headers and diff body', () => {
    const result = buildDiffContent([
      { new_path: 'src/app.ts', diff: '+console.log("hi")' },
      { old_path: 'src/old.ts', diff: '-console.log("bye")' }
    ])

    expect(result).toContain('# src/app.ts')
    expect(result).toContain('+console.log("hi")')
    expect(result).toContain('# src/old.ts')
    expect(result).toContain('-console.log("bye")')
  })
})
