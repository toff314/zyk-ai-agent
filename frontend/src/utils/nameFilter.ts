export function normalizeNameFilter(value?: string) {
  const trimmed = (value || '').trim()
  return trimmed ? trimmed : undefined
}
