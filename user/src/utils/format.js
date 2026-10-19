// 字节数格式化：1048576 -> "1.0 MB"
export function formatBytes(bytes) {
  if (bytes === null || bytes === undefined || Number.isNaN(Number(bytes))) return '-'
  const n = Number(bytes)
  if (n === 0) return '0 B'
  if (n === -1) return '不限'
  const units = ['B', 'KB', 'MB', 'GB', 'TB']
  let i = 0
  let v = n
  while (v >= 1024 && i < units.length - 1) {
    v /= 1024
    i += 1
  }
  return `${v.toFixed(v >= 100 ? 0 : 1)} ${units[i]}`
}

// UTC ISO8601 时间转本地时间显示（如 2026-08-25 14:30）
export function formatDateTime(utcIso) {
  if (!utcIso) return '-'
  const d = new Date(utcIso)
  if (Number.isNaN(d.getTime())) return String(utcIso)
  const pad = (x) => String(x).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`
}

// 百分比占位计算
export function percent(part, total) {
  if (!total || total <= 0) return 0
  return Math.min(100, Math.round((part / total) * 100))
}
