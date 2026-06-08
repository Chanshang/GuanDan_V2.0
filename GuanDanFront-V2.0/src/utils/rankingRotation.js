export function getRotatingPage(totalCount, pageSize, intervalMs, nowMs = Date.now()) {
  if (!Number.isFinite(totalCount) || totalCount <= 0) {
    return 0
  }
  if (!Number.isFinite(pageSize) || pageSize <= 0) {
    return 0
  }
  if (!Number.isFinite(intervalMs) || intervalMs <= 0) {
    return 0
  }

  const pageCount = Math.ceil(totalCount / pageSize)
  return Math.floor(nowMs / intervalMs) % pageCount
}

export function sliceRotatingPage(rows, pageSize, intervalMs, nowMs = Date.now()) {
  if (!Array.isArray(rows) || rows.length === 0) {
    return []
  }

  const currentPage = getRotatingPage(rows.length, pageSize, intervalMs, nowMs)
  const start = currentPage * pageSize
  return rows.slice(start, start + pageSize)
}
