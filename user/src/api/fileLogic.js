import http from './request'
import { DEFAULT_FILE_PAGE_SIZE } from '../constants'

// ===== file-logic-service 获取信息类 =====

// 获取当前组下的文件信息（窗口分页）
export function getGroupFiles(groupId, page = 0, size = DEFAULT_FILE_PAGE_SIZE) {
  return http.get(`/file-logic-service/groups/${groupId}/files`, { params: { page, size } })
}

// 获取公开页文件信息
export function getPublicPageFiles(groupId, page = 0, size = DEFAULT_FILE_PAGE_SIZE) {
  return http.get(`/file-logic-service/groups/${groupId}/public-pages/files`, {
    params: { page, size },
  })
}

// 获取指定页文件信息
export function getSpecificPageFiles(groupId, specificPagesId, page = 0, size = DEFAULT_FILE_PAGE_SIZE) {
  return http.get(`/file-logic-service/groups/${groupId}/specific-pages/${specificPagesId}/files`, {
    params: { page, size },
  })
}

// 获取已软删除的文件信息
export function getDeletedFiles(groupId, page = 0, size = DEFAULT_FILE_PAGE_SIZE) {
  return http.get(`/file-logic-service/groups/${groupId}/deleted/files`, { params: { page, size } })
}

// 获取当前组的存储使用情况（size=-1 表示未限制）
export function getStorageQuota(groupId) {
  return http.get(`/file-logic-service/groups/${groupId}/storage-quota`)
}

// ===== file-logic-service 文件操作类 =====

// 文件更名
export function renameFile(groupId, fileId, fileName) {
  return http.patch(`/file-logic-service/groups/${groupId}/files/${fileId}/name`, { fileName })
}

// 文件标签修改
export function changeFileLabel(groupId, fileId, label) {
  return http.patch(`/file-logic-service/groups/${groupId}/files/${fileId}/label`, { label })
}

// 软删除文件
export function softDeleteFile(groupId, fileId) {
  return http.delete(`/file-logic-service/groups/${groupId}/files/${fileId}`)
}

// 恢复已软删除文件
export function restoreFile(groupId, fileId) {
  return http.post(`/file-logic-service/groups/${groupId}/files/${fileId}/restore`)
}

// 实删除文件
export function hardDeleteFile(groupId, fileId) {
  return http.delete(`/file-logic-service/groups/${groupId}/deleted/files/${fileId}`)
}

// ===== file-logic-service 页类 =====

// 获取全局的公开页
export function getPublicPages() {
  return http.get('/file-logic-service/arbitrary-groups/public-pages')
}

// 获取当前用户可见的指定页
export function getVisibleSpecificPages() {
  return http.get('/file-logic-service/accounts/me/visible-pages')
}

// 获取当前组的所有指定页信息
export function getGroupSpecificPages(groupId) {
  return http.get(`/file-logic-service/groups/${groupId}/specific-pages`)
}

// 创建指定页
export function createSpecificPage(groupId, { announcement, visibleGroups }) {
  return http.post(`/file-logic-service/groups/${groupId}/specific-pages`, {
    announcement,
    visibleGroups,
  })
}

// 修改公开页的公告
export function updatePublicPageAnnouncement(groupId, publicPageId, announcement) {
  return http.patch(`/file-logic-service/groups/${groupId}/public-pages/${publicPageId}`, {
    announcement,
  })
}

// 修改指定页的公告或可见组
export function updateSpecificPage(groupId, specificPageId, payload) {
  return http.patch(`/file-logic-service/groups/${groupId}/specific-pages/${specificPageId}`, payload)
}

// 删除指定页
export function deleteSpecificPage(groupId, specificPageId) {
  return http.delete(`/file-logic-service/groups/${groupId}/specific-pages/${specificPageId}`)
}

// ===== file-logic-service 页文件操作 =====

// 将文件添加到公开页
export function addFileToPublicPage(groupId, fileId) {
  return http.post(`/file-logic-service/groups/${groupId}/public-pages/files`, { fileId })
}

// 将文件从公开页移除
export function removeFileFromPublicPage(groupId, fileId) {
  return http.delete(`/file-logic-service/groups/${groupId}/public-pages/files/${fileId}`)
}

// 将文件添加到指定页
export function addFileToSpecificPage(groupId, specificPagesId, fileId) {
  return http.post(
    `/file-logic-service/groups/${groupId}/specific-pages/${specificPagesId}/files`,
    { fileId },
  )
}

// 将文件从指定页移除
export function removeFileFromSpecificPage(groupId, specificPagesId, fileId) {
  return http.delete(
    `/file-logic-service/groups/${groupId}/specific-pages/${specificPagesId}/files/${fileId}`,
  )
}
