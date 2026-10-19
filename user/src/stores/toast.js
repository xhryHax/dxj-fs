import { reactive } from 'vue'

// 轻量级全局 Toast 状态（供组件与 api 层共用）
export const toastState = reactive({ list: [] })

let seed = 0

export function toast(message, type = 'error', duration = 3200) {
  const id = ++seed
  toastState.list.push({ id, message, type })
  setTimeout(() => removeToast(id), duration)
}

export function removeToast(id) {
  const index = toastState.list.findIndex((t) => t.id === id)
  if (index !== -1) toastState.list.splice(index, 1)
}
