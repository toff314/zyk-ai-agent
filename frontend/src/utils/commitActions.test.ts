import { describe, it, expect } from 'vitest'
import { commitActionButtonStyle } from './commitActions'

describe('commitActionButtonStyle', () => {
  it('sets a fixed min width for consistent button size', () => {
    expect(commitActionButtonStyle).toMatchObject({
      minWidth: '96px'
    })
  })
})
