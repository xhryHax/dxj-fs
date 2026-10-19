<script setup>
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import * as systemApi from '../api/system'
import { formatBytes } from '../utils/format'
import { toast } from '../stores/toast'
import Card from '../components/ui/Card.vue'
import Spinner from '../components/ui/Spinner.vue'
import EmptyState from '../components/ui/EmptyState.vue'

const router = useRouter()
const auth = useAuthStore()

const online = ref([])
const storage = ref(null)
const groupCount = ref(0)
const loading = ref(true)

onMounted(() => load().catch(() => {}))

// 兼容后端返回的字段变体（userName/username/name 等），并过滤无效记录
function normalizeOnlineUser(u) {
  if (!u || typeof u !== 'object') return null
  const userId = u.userId ?? u.id
  if (userId === undefined || userId === null) return null
  return {
    userId,
    userName: u.userName ?? u.username ?? u.name ?? '未知用户',
    email: u.email ?? '',
    groupId: u.groupId ?? u.group,
    groupName: u.groupName ?? '',
  }
}

async function load() {
  loading.value = true
  try {
    // 请求相互独立：任一失败（如后端接口未实现）不应影响其他数据的渲染
    const [users, info, groups] = await Promise.all([
      systemApi.getOnlineUsers().catch(() => null),
      systemApi.getSystemStorageInfo().catch(() => null),
      systemApi.getSystemGroups().catch(() => null),
    ])
    // content 可能为 null（后端约定），防御处理避免渲染异常
    online.value = Array.isArray(users) ? users.map(normalizeOnlineUser).filter(Boolean) : []
    storage.value = info
    // 组数取自组列表接口（storage/info 接口可能未实现），避免依赖不可用数据源
    groupCount.value = Array.isArray(groups) ? groups.length : 0
  } finally {
    loading.value = false
  }
}

function logout() {
  auth.logout()
  toast('已退出管理员登录', 'info')
  router.push('/')
}
</script>

<template>
  <div class="page">
    <header class="head">
      <div class="head-row">
        <h2>系统管理员界面</h2>
        <button class="logout-btn" @click="logout">退出管理员</button>
      </div>
      <p class="muted">管理在线用户、系统存储、可访问域与组类。</p>
    </header>

    <Spinner v-if="loading" class="loading" :size="36" />

    <template v-else>
      <!-- 系统存储 -->
      <Card class="storage-card">
        <h3>系统存储使用情况</h3>
        <div class="storage-stat">
          <div class="stat-item">
            <span class="stat-label">系统存储总量</span>
            <span class="stat-value">{{ formatBytes(storage?.size) }}</span>
          </div>
          <div class="stat-item">
            <span class="stat-label">已使用</span>
            <span class="stat-value">{{ formatBytes(storage?.occupied) }}</span>
          </div>
          <div class="stat-item">
            <span class="stat-label">组数</span>
            <span class="stat-value">{{ groupCount }}</span>
          </div>
        </div>
      </Card>

      <!-- 在线用户 -->
      <Card class="users-card">
        <h3>当前在线用户（{{ online.length }}）</h3>
        <div class="table-scroll">
          <table class="users-table">
            <thead>
              <tr>
                <th>用户名</th>
                <th>邮箱</th>
                <th>组名</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="u in online" :key="u.userId">
                <td class="col-strong">{{ u.userName }}</td>
                <td>{{ u.email }}</td>
                <td>{{ u.groupName || '—' }}</td>
              </tr>
            </tbody>
          </table>
        </div>
        <EmptyState v-if="!online.length" message="当前无在线用户" />
      </Card>

      <!-- 入口 -->
      <div class="entry-grid">
        <button class="entry-card" @click="router.push('/admin/domains')">
          <img src="/img/domain.png" alt="可访问域" class="entry-icon" />
          <h3>可访问域</h3>
          <p class="muted">管理系统允许访问的网络域</p>
        </button>
        <button class="entry-card" @click="router.push('/admin/groups')">
          <img src="/img/group.png" alt="组类" class="entry-icon" />
          <h3>组类</h3>
          <p class="muted">管理所有组、成员与存储配额</p>
        </button>
      </div>
    </template>
  </div>
</template>

<style scoped>
.head {
  margin-bottom: 24px;
}
.head-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}
.logout-btn {
  background: none;
  border: 1px solid var(--border-interactive);
  border-radius: var(--radius-sm);
  padding: 6px 12px;
  cursor: pointer;
  font-size: 19px;
  font-weight: 600;
}
.logout-btn:hover {
  box-shadow: var(--shadow-focus);
}
.loading {
  display: block;
  margin: 80px auto;
}
.storage-card {
  margin-bottom: 20px;
}
.storage-stat {
  display: flex;
  gap: 40px;
  flex-wrap: wrap;
}
.stat-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.stat-label {
  font-size: 19px;
  color: var(--text-secondary);
}
.stat-value {
  font-size: 24px;
  font-weight: 600;
}
.users-card {
  margin-bottom: 20px;
}
.users-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 19px;
  min-width: 480px;
}
.users-table th,
.users-table td {
  text-align: left;
  padding: 10px 12px;
  border-bottom: 1px solid var(--border-passive);
}
.users-table th {
  font-size: 19px;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--text-secondary);
}
.users-table tbody tr:hover {
  background: rgba(28, 28, 28, 0.03);
}
.users-table tbody tr:last-child td {
  border-bottom: none;
}
.col-strong {
  font-weight: 600;
}
.entry-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 16px;
}
.entry-card {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 6px;
  padding: 20px;
  background: var(--bg-cream);
  border: 1px solid var(--border-passive);
  border-radius: var(--radius-md);
  cursor: pointer;
  text-align: left;
  transition: box-shadow 0.2s ease, transform 0.2s ease;
}
.entry-card:hover {
  box-shadow: var(--shadow-focus);
  transform: translateY(-2px);
}
.entry-card h3 {
  margin: 0;
}
.entry-card p {
  margin: 0;
  font-size: 19px;
}
.entry-icon {
  width: 26px;
  height: 26px;
  object-fit: contain;
}
</style>
