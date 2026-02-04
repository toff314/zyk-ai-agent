import { describe, it, expect } from 'vitest'
import { replaceTriggerText } from './triggerInsert'

describe('replaceTriggerText', () => {
  it('replaces text between trigger and cursor with replacement', () => {
    const result = replaceTriggerText('hello #tem', 6, 10, 'TEMPLATE')
    expect(result).toBe('hello TEMPLATE')
  })

  it('keeps suffix after cursor', () => {
    const result = replaceTriggerText('hi #tem world', 3, 7, 'TEMPLATE')
    expect(result).toBe('hi TEMPLATE world')
  })
})
