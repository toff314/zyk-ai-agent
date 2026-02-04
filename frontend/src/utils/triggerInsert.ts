export function replaceTriggerText(
  value: string,
  triggerIndex: number,
  cursorIndex: number,
  replacement: string
): string {
  const before = value.slice(0, triggerIndex)
  let after = value.slice(cursorIndex)
  const normalized = replacement.endsWith(' ') ? replacement : `${replacement} `
  if (normalized.endsWith(' ') && after.startsWith(' ')) {
    after = after.slice(1)
  }
  return `${before}${normalized}${after}`.trimEnd()
}
