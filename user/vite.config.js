import vue from '@vitejs/plugin-vue'
import { defineConfig, loadEnv } from 'vite'

// https://vite.dev/config/
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  return {
    plugins: [vue()],
    server: {
      host: '0.0.0.0',
      allowedHosts: true,
      proxy: {
        // RustFS 文件下载直链代理：直链为统一网关下的 /v1/io 路径，
        // 经 Vite 代理转发后可同源下载（a.download 生效），避免浏览器跨域 CORS 拦截
        // 目标地址通过环境变量 VITE_RUSTFS_GATEWAY 参数化（见 .env）
        '/v1/io': {
          target: env.VITE_RUSTFS_GATEWAY || 'http://xyhraics.top',
          changeOrigin: true,
        },
        // 后端 API 代理：解决 HttpOnly Cookie 跨域问题
        // 目标地址通过环境变量 VITE_API_PROXY_TARGET 参数化（见 .env）
        '/v1': {
          target: env.VITE_API_PROXY_TARGET || 'http://localhost:1114',
          changeOrigin: true,
        },
      },
    },
  }
})
