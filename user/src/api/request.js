import axios from 'axios'
import { toast } from '../stores/toast'

// 统一 axios 实例：HttpOnly Cookie 认证，必须携带凭据
// baseURL 通过环境变量 VITE_API_BASE_URL 参数化（见 .env），未配置时默认 /v1
const http = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '/v1',
  withCredentials: true,
  timeout: 30000,
})

http.interceptors.response.use(
  (response) => {
    // 响应数据体统一为 { code, msg, content }
    const { code, msg, content } = response.data
    if (code === 0) return content
    // 未登录：清除登录态并跳转登录页（延迟处理，避免在 store 初始化前触发）
    if (code === 2001) {
      Promise.all([import('../stores/auth'), import('../router')]).then(
        ([authModule, routerModule]) => {
          authModule.useAuthStore().clear()
          const router = routerModule.default
          if (router.currentRoute.value.path !== '/login') {
            router.push('/login')
          }
        },
      )
    }
    toast(msg || '请求失败')
    return Promise.reject(new Error(msg || '请求失败'))
  },
  (error) => {
    const status = error.response?.status
    if (status === 401 || status === 403) {
      import('../stores/auth').then(({ useAuthStore }) => {
        useAuthStore().clear()
      })
    }
    toast(error.response?.data?.msg || error.message || '网络错误')
    return Promise.reject(error)
  },
)

export default http
