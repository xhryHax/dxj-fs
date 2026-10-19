import { defineStore } from 'pinia'
import { ref } from 'vue'
import * as accountApi from '../api/account'
import * as systemApi from '../api/system'
import { useGroupStore } from './group'

const USER_KEY = 'achievement_user'
const ADMIN_KEY = 'achievement_system_admin'

function readStoredUser() {
  try {
    return JSON.parse(localStorage.getItem(USER_KEY)) || null
  } catch {
    return null
  }
}

export const useAuthStore = defineStore('auth', () => {
  const user = ref(readStoredUser()) // {userId, userName, email, groupId}
  const isSystemAdmin = ref(localStorage.getItem(ADMIN_KEY) === '1')

  function persistUser() {
    if (user.value) localStorage.setItem(USER_KEY, JSON.stringify(user.value))
    else localStorage.removeItem(USER_KEY)
  }

  function setUser(data) {
    if (!data) return
    user.value = {
      userId: data.userId,
      userName: data.userName,
      email: data.email,
      groupId: data.groupId,
    }
    persistUser()
  }

  function setSystemAdmin(value) {
    isSystemAdmin.value = value
    if (value) localStorage.setItem(ADMIN_KEY, '1')
    else localStorage.removeItem(ADMIN_KEY)
  }

  function clear() {
    user.value = null
    isSystemAdmin.value = false
    persistUser()
    localStorage.removeItem(ADMIN_KEY)
    useGroupStore().clear()
  }

  async function login(email, password) {
    const data = await accountApi.login({ email, password })
    setUser(data)
    return data
  }

  async function register({ email, userName, password }) {
    const data = await accountApi.register({ email, password, userName })
    setUser(data)
    return data
  }

  async function adminLogin(id, password) {
    const data = await systemApi.adminLogin({ id, password })
    setUser(data)
    setSystemAdmin(true)
    return data
  }

  async function changeUserName(newName) {
    await accountApi.updateUserName(newName)
    if (user.value) user.value.userName = newName
    persistUser()
  }

  async function changePassword(oldPassword, newPassword) {
    await accountApi.updatePassword(oldPassword, newPassword)
  }

  function logout() {
    clear()
  }

  return {
    user,
    isSystemAdmin,
    setUser,
    setSystemAdmin,
    clear,
    login,
    register,
    adminLogin,
    changeUserName,
    changePassword,
    logout,
  }
})
