export function replaceTriggerText(
  value: string,
  triggerIndex: number,
  cursorIndex: number,
  replacement: string
): string {
  const before = value.slice(0, triggerIndex)
  const after = value.slice(cursorIndex)
  const normalized = replacement.endsWith(' ') ? replacement : `${replacement} `
  return `${before}${normalized}${after}`.trimEnd()
}
