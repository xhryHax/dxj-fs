import http from './request'

// ===== file-io-service 文件上下载 =====

// 获取已有的上传进度
export function getUploadInfos(groupId) {
  return http.get(`/file-io-service/groups/${groupId}/files/upload-info`)
}

// 删除上传记录
export function deleteUploadInfo(groupId, uploadInfoId) {
  return http.delete(`/file-io-service/groups/${groupId}/files/upload-info/${uploadInfoId}`)
}

// 就绪文件上传环境（创建上传记录）
export function prepareUpload(groupId, { size, fileName, label }) {
  return http.post(`/file-io-service/groups/${groupId}/files/upload-info`, {
    size,
    fileName,
    label,
  })
}

// 上传文件分片数据
// 须携带 Content-Range 标头声明当前分片位置，格式如: bytes=0-5242879/10485760
export function uploadChunk(groupId, uploadInfoId, chunk, start, end, total) {
  return http.put(
    `/file-io-service/groups/${groupId}/files/upload-info/${uploadInfoId}/data`,
    chunk,
    {
      headers: {
        'Content-Type': 'application/octet-stream',
        'Content-Range': `bytes=${start}-${end}/${total}`,
      },
    },
  )
}

// 完成文件上传
export function completeUpload(groupId, uploadInfoId) {
  return http.post(`/file-io-service/groups/${groupId}/files/upload-info/${uploadInfoId}/complete`)
}

// 获取下载文件链接（返回 { fileURL, fileName }，由客户端自行下载）
export function getDownloadLink(groupId, fileId) {
  return http.get(`/file-io-service/groups/${groupId}/files/${fileId}`)
}
