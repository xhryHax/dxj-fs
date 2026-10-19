// 依据接口返回的 fileURL 与 fileName 触发浏览器下载，保证文件名与 fileName 一致。
// 直链为统一网关下的路径（如 /v1/io/...），将 origin 改写为页面所在源后同源下载：
// 开发环境经 Vite 代理（/v1/io -> VITE_RUSTFS_GATEWAY）转发，
// 生产环境页面与网关同源（统一域名 xyhraics.top）原样即可。
// 同源 URL 下 a.download 属性生效，下载文件名与 fileName 严格一致，无需 blob 中转。
function toPageOriginUrl(url) {
  try {
    const u = new URL(url, window.location.href)
    u.protocol = window.location.protocol
    u.host = window.location.host
    return u.href
  } catch {
    return url
  }
}

export function downloadByUrl(fileURL, fileName) {
  if (!fileURL) return
  const sameOriginUrl = toPageOriginUrl(fileURL)
  console.info('[download]', { fileURL, fileName, downloadUrl: sameOriginUrl })
  const link = document.createElement('a')
  link.href = sameOriginUrl
  if (fileName) link.download = fileName
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
}
