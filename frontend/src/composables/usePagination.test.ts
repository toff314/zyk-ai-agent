import { describe, it, expect } from 'vitest'
import { usePagination, DEFAULT_PAGE_SIZE } from './usePagination'

describe('usePagination', () => {
  it('defaults to page 1 and default page size', () => {
    const pagination = usePagination()

    expect(pagination.page.value).toBe(1)
    expect(pagination.pageSize.value).toBe(DEFAULT_PAGE_SIZE)
    expect(pagination.total.value).toBe(0)
  })

  it('clamps current page when total shrinks', () => {
    const pagination = usePagination(3, 10)
    pagination.setTotal(25)
    expect(pagination.maxPage.value).toBe(3)

    pagination.setTotal(15)
    expect(pagination.maxPage.value).toBe(2)
    expect(pagination.page.value).toBe(2)
  })

  it('resetPage sets page back to 1', () => {
    const pagination = usePagination(4, 20)
    pagination.resetPage()
    expect(pagination.page.value).toBe(1)
  })

  it('prevPage does not go below 1', () => {
    const pagination = usePagination(1, 20)
    pagination.prevPage()
    expect(pagination.page.value).toBe(1)
  })

  it('nextPage increments but not beyond maxPage', () => {
    const pagination = usePagination(1, 10)
    pagination.setTotal(25)

    pagination.nextPage()
    expect(pagination.page.value).toBe(2)

    pagination.nextPage()
    expect(pagination.page.value).toBe(3)

    pagination.nextPage()
    expect(pagination.page.value).toBe(3)
  })
})
