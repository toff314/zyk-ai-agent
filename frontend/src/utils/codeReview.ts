export function buildCodeReviewPayload({ title, diff }: { title: string; diff: string }) {
  const MAX = 20000
  const HEAD = 10000
  const TAIL = 10000

  let reviewDiff = diff
  let reviewNotice = ''

  if (diff.length > MAX) {
    reviewDiff = diff.slice(0, HEAD) + '\n\n...已截断...\n\n' + diff.slice(-TAIL)
    reviewNotice = `diff内容过长，已截断，仅展示前后各 ${HEAD} 字符。`
  }

  const message = reviewNotice ? `代码审查: ${title}（diff已截断）` : `代码审查: ${title}`

  return {
    message,
    review_diff: reviewDiff,
    review_notice: reviewNotice
  }
}
