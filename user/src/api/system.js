import http from './request'

// ===== system-service 管理员登录 =====

// 系统管理员登录（使用用户 id + 密码）
export function adminLogin({ id, password }) {
  return http.post('/system-service/sessions', { id, password })
}

// ===== system-service 系统状态类 =====

// 获取当前活跃的用户信息
export function getOnlineUsers() {
  return http.get('/system-service/system/users/online')
}

// 获取存储系统使用情况
export function getSystemStorageInfo() {
  return http.get('/system-service/system/storage/info')
}

// ===== system-service 可访问域类 =====

// 获取当前可访问域
export function getAccessibleDomains() {
  return http.get('/system-service/system/network/accessible')
}

// 添加可访问域
export function addAccessibleDomain(value) {
  return http.post('/system-service/system/network/accessible', { value })
}

// 删除可访问域
export function removeAccessibleDomain(value) {
  return http.delete('/system-service/system/network/accessible', { params: { value } })
}

// ===== system-service 组类 =====

// 获取所有的组的信息和对应的成员信息
export function getSystemGroups() {
  return http.get('/system-service/system/groups')
}

// 获取所有组的存储空间配额信息
export function getSystemStorageQuotas() {
  return http.get('/system-service/system/groups/storage-quota')
}

// 对指定组进行存储空间配额设置
export function setStorageQuota(groupId, size) {
  return http.patch(`/system-service/system/groups/${groupId}/storage-quota`, { groupId, size })
}

// 获取组中的成员信息
export function getSystemGroupMembers(groupId) {
  return http.get(`/system-service/system/groups/${groupId}/members`)
}

// 将指定成员任命为组管理员
export function appointAdministrator(groupId, userId) {
  return http.put(`/system-service/system/groups/${groupId}/administrator`, null, {
    params: { userId },
  })
}

// 将指定成员免除组管理员
export function dismissAdministrator(groupId, userId) {
  return http.delete(`/system-service/system/groups/${groupId}/administrator`, {
    params: { userId },
  })
}

// 创建组
export function createGroup(groupName) {
  return http.post('/system-service/system/groups', { groupName })
}

// 删除组
export function deleteGroup(groupId) {
  return http.delete(`/system-service/system/groups/${groupId}`)
}

// 修改组名
export function renameGroup(groupId, groupName) {
  return http.patch(`/system-service/system/groups/${groupId}`, { groupName })
}

// 获取加入组请求
export function getSystemJoinRequests(groupId) {
  return http.get(`/system-service/system/groups/${groupId}/join-requests`)
}

// 审批加入组请求
export function reviewSystemJoinRequest(groupId, userId, status) {
  return http.patch(`/system-service/system/groups/${groupId}/join-requests/${userId}`, { status })
}
