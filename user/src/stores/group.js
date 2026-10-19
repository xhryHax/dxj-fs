import { defineStore } from 'pinia'
import { ref } from 'vue'
import * as accountApi from '../api/account'
import * as fileLogicApi from '../api/fileLogic'
import * as authModule from './auth'

export const useGroupStore = defineStore('group', () => {
  const groupId = ref(null)
  const groupName = ref('')
  const members = ref([]) // [{userId, userName, email}]
  const isGroupAdmin = ref(false)
  const storageQuota = ref(null) // {groupId, groupName, size, occupied}

  async function fetchGroupInfo() {
    const auth = authModule.useAuthStore()
    const gid = groupId.value ?? auth.user?.groupId
    if (!gid) return
    groupId.value = gid
    const groups = await accountApi.getAllGroups()
    const current = groups.find((g) => g.groupId === gid)
    groupName.value = current?.groupName ?? ''
  }

  async function fetchMembers() {
    if (!groupId.value) return
    members.value = await accountApi.getGroupMembers(groupId.value)
  }

  async function fetchIsGroupAdmin() {
    if (!groupId.value) return
    isGroupAdmin.value = await accountApi.getIsGroupAdmin()
  }

  async function fetchStorageQuota() {
    if (!groupId.value) return
    storageQuota.value = await fileLogicApi.getStorageQuota(groupId.value)
  }

  // 一次拉取组空间所需全部基础信息
  async function initGroup() {
    await fetchGroupInfo()
    await Promise.all([fetchMembers(), fetchIsGroupAdmin(), fetchStorageQuota()])
  }

  function setGroupId(gid) {
    groupId.value = gid
  }

  function clear() {
    groupId.value = null
    groupName.value = ''
    members.value = []
    isGroupAdmin.value = false
    storageQuota.value = null
  }

  return {
    groupId,
    groupName,
    members,
    isGroupAdmin,
    storageQuota,
    fetchGroupInfo,
    fetchMembers,
    fetchIsGroupAdmin,
    fetchStorageQuota,
    initGroup,
    setGroupId,
    clear,
  }
})
