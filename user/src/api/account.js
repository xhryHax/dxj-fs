import http from './request'

// ===== account-service 用户板块 =====

// 注册并登录账户
export function register({ email, password, userName }) {
  return http.post('/account-service/accounts', { email, password, userName })
}

// 登录账户（用户登录）
export function login({ email, password }) {
  return http.post('/account-service/sessions', { email, password })
}

// 修改账户名
export function updateUserName(userName) {
  return http.patch('/account-service/accounts/me/name', { userName })
}

// 修改账户密码（会设置新的 Cookie）
export function updatePassword(oldPassword, newPassword) {
  return http.patch('/account-service/accounts/me/password', { oldPassword, newPassword })
}

// 获取当前用户是否为组管理员
export function getIsGroupAdmin() {
  return http.get('/account-service/accounts/me/admin')
}

// ===== account-service 组板块 =====

// 获取本组中所有成员的信息
export function getGroupMembers(groupId) {
  return http.get(`/account-service/groups/${groupId}/members`)
}

// 获取所有的组信息
export function getAllGroups() {
  return http.get('/account-service/groups')
}

// 发起加入组的请求
export function requestJoinGroup(groupId) {
  return http.post(`/account-service/groups/${groupId}/join-requests`)
}

// 获取组加入请求
export function getGroupJoinRequests(groupId) {
  return http.get(`/account-service/groups/${groupId}/join-requests`)
}

// 审批加入组请求
export function reviewJoinRequest(groupId, userId, status) {
  return http.patch(`/account-service/groups/${groupId}/join-requests/${userId}`, { status })
}

// 退出所在的组
export function leaveGroup(groupId) {
  return http.delete(`/account-service/groups/${groupId}/members/me`)
}
