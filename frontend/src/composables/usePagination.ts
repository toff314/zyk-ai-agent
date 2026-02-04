import { computed, ref } from 'vue'

export const DEFAULT_PAGE_SIZE = 20
export const PAGE_SIZE_OPTIONS = [10, 20, 50, 100]

export function usePagination(initialPage = 1, initialPageSize = DEFAULT_PAGE_SIZE) {
  const page = ref(initialPage)
  const pageSize = ref(initialPageSize)
  const total = ref(0)

  const maxPage = computed(() => {
    return Math.max(1, Math.ceil(total.value / pageSize.value))
  })

  const setTotal = (value: number) => {
    total.value = value
    if (page.value > maxPage.value) {
      page.value = maxPage.value
    }
  }

  const resetPage = () => {
    page.value = 1
  }

  return {
    page,
    pageSize,
    total,
    maxPage,
    setTotal,
    resetPage
  }
}
