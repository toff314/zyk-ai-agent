import { describe, it, expect } from 'vitest'
import { normalizeNameFilter } from './nameFilter'

describe('normalizeNameFilter', () => {
  it('returns trimmed value when non-empty', () => {
    expect(normalizeNameFilter('  foo  ')).toBe('foo')
  })

  it('returns undefined when empty or whitespace', () => {
    expect(normalizeNameFilter('   ')).toBeUndefined()
    expect(normalizeNameFilter(undefined)).toBeUndefined()
  })
})
