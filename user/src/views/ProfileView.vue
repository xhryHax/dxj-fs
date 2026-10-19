<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { useGroupStore } from '../stores/group'
import * as accountApi from '../api/account'
import { toast } from '../stores/toast'
import Card from '../components/ui/Card.vue'
import Button from '../components/ui/Button.vue'
import Input from '../components/ui/Input.vue'
import Modal from '../components/ui/Modal.vue'
import Spinner from '../components/ui/Spinner.vue'
import Tag from '../components/ui/Tag.vue'
import logoSmall from '../assets/logo-small.svg'

const router = useRouter()
const auth = useAuthStore()
const group = useGroupStore()

const groups = ref([])
const selectedGroupId = ref('')
const joinLoading = ref(false)
const loading = ref(true)
const pendingKey = computed(() => (auth.user ? `pending_join_${auth.user.userId}` : ''))

const pending = ref(false)
function loadPending() {
  pending.value = localStorage.getItem(pendingKey.value) === '1'
}

const nameModal = reactive({ open: false, name: '', loading: false })
const pwdModal = reactive({ open: false, old: '', next: '', confirm: '', loading: false })

onMounted(async () => {
  loadPending()
  try {
    if (auth.user?.groupId) {
      await group.initGroup()
    } else {
      groups.value = await accountApi.getAllGroups()
    }
  } catch {
    /* 错误提示已由请求层统一处理 */
  } finally {
    loading.value = false
  }
})

function openNameModal() {
  nameModal.name = auth.user?.userName || ''
  nameModal.open = true
}

async function submitName() {
  if (!nameModal.name.trim()) {
    toast('用户名不能为空', 'warning')
    return
  }
  nameModal.loading = true
  try {
    await auth.changeUserName(nameModal.name.trim())
    nameModal.open = false
    toast('用户名已更新', 'success')
  } catch {
    /* 错误提示已由请求层统一处理 */
  } finally {
    nameModal.loading = false
  }
}

function openPwdModal() {
  Object.assign(pwdModal, { open: true, old: '', next: '', confirm: '' })
}

async function submitPwd() {
  if (!pwdModal.old || !pwdModal.next || !pwdModal.confirm) {
    toast('请填写完整的密码信息', 'warning')
    return
  }
  if (pwdModal.next !== pwdModal.confirm) {
    toast('两次输入的新密码不一致', 'warning')
    return
  }
  if (pwdModal.next.length < 6) {
    toast('新密码长度至少为 6 位', 'warning')
    return
  }
  pwdModal.loading = true
  try {
    await auth.changePassword(pwdModal.old, pwdModal.next)
    pwdModal.open = false
    toast('密码已修改，请牢记新密码', 'success')
  } catch {
    /* 错误提示已由请求层统一处理 */
  } finally {
    pwdModal.loading = false
  }
}

async function requestJoin() {
  if (!selectedGroupId.value) {
    toast('请先选择一个组', 'warning')
    return
  }
  joinLoading.value = true
  try {
    await accountApi.requestJoinGroup(selectedGroupId.value)
    pending.value = true
    localStorage.setItem(pendingKey.value, '1')
    toast('已发起加入请求，等待审批', 'success')
  } catch {
    /* 错误提示已由请求层统一处理 */
  } finally {
    joinLoading.value = false
  }
}

async function handleLogout() {
  auth.logout()
  toast('已退出登录', 'info')
  router.push('/')
}
</script>

<template>
  <div class="page">
    <header class="profile-nav">
      <img :src="logoSmall" alt="logo" class="nav-logo" />
      <span class="nav-brand">个人中心</span>
    </header>

    <Spinner v-if="loading" class="page-loading" :size="32" />
    <template v-else-if="auth.user">
      <!-- 用户信息 -->
      <Card class="user-card">
        <div class="user-avatar">{{ (auth.user.userName || auth.user.email || '?').charAt(0).toUpperCase() }}</div>
        <div class="user-meta">
          <h2 class="user-name">{{ auth.user.userName || '未设置用户名' }}</h2>
          <p class="user-email">{{ auth.user.email }}</p>
        </div>
        <div class="user-actions">
          <Button variant="ghost" size="sm" @click="openNameModal">修改用户名</Button>
          <Button variant="ghost" size="sm" @click="openPwdModal">修改密码</Button>
        </div>
      </Card>

      <!-- 未加入组：加入组界面 -->
      <Card v-if="!auth.user.groupId" class="join-card">
        <h3>加入一个组</h3>
        <p class="muted join-desc">
          {{ pending ? '你已发起加入请求，请耐心等待组管理员审批。' : '选择你所属的组并发起加入请求，通过审批后即可进入组空间。' }}
        </p>
        <div v-if="!pending" class="join-row">
          <select v-model="selectedGroupId" class="join-select">
            <option value="" disabled>请选择组</option>
            <option v-for="g in groups" :key="g.groupId" :value="g.groupId">{{ g.groupName }}</option>
          </select>
          <Button :loading="joinLoading" @click="requestJoin">申请加入</Button>
        </div>
        <Tag v-else tone="warning">等待审批中</Tag>
        <p v-if="!groups.length" class="muted join-empty">当前暂无可加入的组</p>
      </Card>

      <!-- 已加入组：组信息 -->
      <Card v-else class="join-card">
        <h3>你所在的组</h3>
        <div class="group-info">
          <Tag tone="success">已加入</Tag>
          <span class="group-name">{{ group.groupName || `组 #${auth.user.groupId}` }}</span>
          <span class="muted">{{ group.members.length }} 位成员</span>
        </div>
        <div class="join-row">
          <Button @click="router.push('/group-space')">进入组空间</Button>
        </div>
      </Card>

      <!-- 快捷入口 -->
      <h3 class="section-title">快捷入口</h3>
      <div class="quick-grid">
        <button class="quick-card" @click="router.push('/public-pages')">
          <img src="/img/unlock.png" alt="访问公开页" class="quick-icon" />
          <span>访问公开页</span>
        </button>
        <button class="quick-card" @click="router.push('/specific-pages')">
          <img src="/img/lock.png" alt="访问指定页" class="quick-icon" />
          <span>访问指定页</span>
        </button>
        <button class="quick-card quick-card--danger" @click="handleLogout">
          <img src="/img/exit.png" alt="退出登录" class="quick-icon" />
          <span>退出登录</span>
        </button>
      </div>
    </template>

    <!-- 修改用户名 -->
    <Modal :open="nameModal.open" title="修改用户名" @close="nameModal.open = false">
      <Input v-model="nameModal.name" label="新用户名" placeholder="请输入新的用户名" required />
      <template #footer>
        <Button variant="ghost" @click="nameModal.open = false">取消</Button>
        <Button :loading="nameModal.loading" @click="submitName">保存</Button>
      </template>
    </Modal>

    <!-- 修改密码 -->
    <Modal :open="pwdModal.open" title="修改密码" @close="pwdModal.open = false">
      <div class="pwd-fields">
        <Input v-model="pwdModal.old" label="当前密码" type="password" required autocomplete="current-password" />
        <Input v-model="pwdModal.next" label="新密码" type="password" required autocomplete="new-password" />
        <Input v-model="pwdModal.confirm" label="确认新密码" type="password" required autocomplete="new-password" />
      </div>
      <template #footer>
        <Button variant="ghost" @click="pwdModal.open = false">取消</Button>
        <Button :loading="pwdModal.loading" @click="submitPwd">确认修改</Button>
      </template>
    </Modal>
  </div>
</template>

<style scoped>
.profile-nav {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 24px;
}
.nav-logo {
  height: 26px;
}
.nav-brand {
  font-weight: 600;
}
.page-loading {
  display: block;
  margin: 80px auto;
}
.user-card {
  display: flex;
  align-items: center;
  gap: 20px;
  padding: 28px;
  margin-bottom: 20px;
  flex-wrap: wrap;
}
.user-avatar {
  width: 56px;
  height: 56px;
  border-radius: var(--radius-full);
  background: var(--text-primary);
  color: var(--text-on-dark);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 24px;
  font-weight: 600;
  flex-shrink: 0;
}
.user-meta {
  flex: 1;
  min-width: 160px;
}
.user-name {
  margin: 0 0 2px;
}
.user-email {
  margin: 0;
  color: var(--text-secondary);
  font-size: 19px;
}
.user-actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}
.join-card {
  margin-bottom: 32px;
}
.join-desc {
  font-size: 19px;
}
.join-row {
  display: flex;
  gap: 12px;
  align-items: center;
  flex-wrap: wrap;
  margin-top: 12px;
}
.join-select {
  padding: 9px 12px;
  background: var(--bg-cream);
  border: 1px solid var(--border-passive);
  border-radius: var(--radius-sm);
  min-width: 220px;
  cursor: pointer;
}
.join-empty {
  font-size: 19px;
  margin-top: 8px;
}
.group-info {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}
.group-name {
  font-weight: 600;
}
.section-title {
  margin-top: 8px;
}
.quick-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 16px;
}
.quick-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
  padding: 24px 16px;
  background: var(--bg-cream);
  border: 1px solid var(--border-passive);
  border-radius: var(--radius-md);
  cursor: pointer;
  font-weight: 600;
  transition: box-shadow 0.2s ease, transform 0.2s ease;
}
.quick-card:hover {
  box-shadow: var(--shadow-focus);
  transform: translateY(-2px);
}
.quick-icon {
  width: 24px;
  height: 24px;
  object-fit: contain;
}
.quick-card--danger {
  color: var(--color-danger);
}
.pwd-fields {
  display: flex;
  flex-direction: column;
  gap: 14px;
}
</style>
