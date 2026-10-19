<script setup>
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import * as systemApi from '../api/system'
import { formatBytes, percent } from '../utils/format'
import { toast } from '../stores/toast'
import Button from '../components/ui/Button.vue'
import Input from '../components/ui/Input.vue'
import Modal from '../components/ui/Modal.vue'
import Spinner from '../components/ui/Spinner.vue'
import EmptyState from '../components/ui/EmptyState.vue'
import Tag from '../components/ui/Tag.vue'
import ConfirmDialog from '../components/ui/ConfirmDialog.vue'

const router = useRouter()

const groups = ref([])
const quotas = ref([])
const loading = ref(true)
const expandedId = ref(null)

// 操作状态
const createOpen = ref(false)
const createName = ref('')
const creating = ref(false)

const renameTarget = ref(null)
const renameName = ref('')
const renaming = ref(false)

const quotaTarget = ref(null)
const quotaSize = ref('')
const quotaSetting = ref(false)

const deleteTarget = ref(null)
const deleting = ref(false)

const reqTarget = ref(null)
const reqList = ref([])
const reqLoading = ref(false)
const reqBusy = ref(null)

onMounted(() => loadAll().catch(() => {}))

async function loadAll() {
  loading.value = true
  try {
    const [g, q] = await Promise.all([systemApi.getSystemGroups(), systemApi.getSystemStorageQuotas()])
    groups.value = g
    quotas.value = q
    // 展开状态保持：若当前展开的组已不存在，则默认展开第一个组
    if (!g.some((x) => x.groupId === expandedId.value)) {
      expandedId.value = g.length ? g[0].groupId : null
    }
  } finally {
    loading.value = false
  }
}

function toggleExpand(groupId) {
  expandedId.value = expandedId.value === groupId ? null : groupId
}

function quotaOf(groupId) {
  return quotas.value.find((q) => q.groupId === groupId)
}

// isAdmin 由后端返回（true 为组管理员）；任命/免除成功后就地更新本地状态
async function toggleAdmin(member, group) {
  try {
    if (member.isAdmin) {
      await systemApi.dismissAdministrator(group.groupId, member.userId)
      member.isAdmin = false
      toast('已免除组管理员', 'success')
    } else {
      await systemApi.appointAdministrator(group.groupId, member.userId)
      member.isAdmin = true
      toast('已任命为组管理员', 'success')
    }
  } catch {
    /* 错误提示已由请求层统一处理 */
  }
}

async function createGroup() {
  if (!createName.value.trim()) {
    toast('请输入组名', 'warning')
    return
  }
  creating.value = true
  try {
    await systemApi.createGroup(createName.value.trim())
    toast('组已创建', 'success')
    createOpen.value = false
    createName.value = ''
    await loadAll()
  } catch {
    /* 错误提示已由请求层统一处理 */
  } finally {
    creating.value = false
  }
}

function openRename(group) {
  renameTarget.value = group
  renameName.value = group.groupName
}

async function submitRename() {
  if (!renameName.value.trim()) {
    toast('组名不能为空', 'warning')
    return
  }
  renaming.value = true
  try {
    await systemApi.renameGroup(renameTarget.value.groupId, renameName.value.trim())
    toast('组名已修改', 'success')
    renameTarget.value = null
    await loadAll()
  } catch {
    /* 错误提示已由请求层统一处理 */
  } finally {
    renaming.value = false
  }
}

function openQuota(group) {
  quotaTarget.value = group
  const q = quotaOf(group.groupId)
  quotaSize.value = q ? String(q.size) : ''
}

async function submitQuota() {
  const size = Number(quotaSize.value)
  if (Number.isNaN(size) || size < -1) {
    toast('配额必须是 -1（不限）或非负字节数', 'warning')
    return
  }
  quotaSetting.value = true
  try {
    await systemApi.setStorageQuota(quotaTarget.value.groupId, size)
    toast('配额已设置', 'success')
    quotaTarget.value = null
    await loadAll()
  } catch {
    /* 错误提示已由请求层统一处理 */
  } finally {
    quotaSetting.value = false
  }
}

async function confirmDelete() {
  deleting.value = true
  try {
    await systemApi.deleteGroup(deleteTarget.value.groupId)
    toast('组已删除', 'success')
    deleteTarget.value = null
    await loadAll()
  } catch {
    /* 错误提示已由请求层统一处理 */
  } finally {
    deleting.value = false
  }
}

async function openRequests(group) {
  reqTarget.value = group
  reqLoading.value = true
  try {
    reqList.value = await systemApi.getSystemJoinRequests(group.groupId)
  } catch {
    /* 错误提示已由请求层统一处理 */
  } finally {
    reqLoading.value = false
  }
}

async function reviewRequest(userId, status) {
  reqBusy.value = userId
  try {
    await systemApi.reviewSystemJoinRequest(reqTarget.value.groupId, userId, status)
    toast(status === 'APPROVED' ? '已通过请求' : '已拒绝请求', 'success')
    reqList.value = reqList.value.filter((r) => r.userId !== userId)
  } catch {
    /* 错误提示已由请求层统一处理 */
  } finally {
    reqBusy.value = null
  }
}
</script>

<template>
  <div class="page">
    <header class="head">
      <div class="head-row">
        <div>
          <button class="back-link" @click="router.push('/admin')">← 系统管理员界面</button>
          <h2>组类</h2>
          <p class="muted">管理所有组、组内成员与存储配额。</p>
        </div>
        <Button @click="createOpen = true">创建组</Button>
      </div>
    </header>

    <Spinner v-if="loading" class="loading" :size="36" />
    <EmptyState v-else-if="!groups.length" message="暂无任何组" hint="点击「创建组」开始" />

    <div v-else class="group-list">
      <div v-for="g in groups" :key="g.groupId" class="group-item">
        <button class="group-row" :class="{ active: expandedId === g.groupId }" @click="toggleExpand(g.groupId)">
          <span class="chevron">{{ expandedId === g.groupId ? '▾' : '▸' }}</span>
          <span class="row-name">{{ g.groupName }}</span>
          <Tag tone="neutral">{{ g.members?.length ?? 0 }} 人</Tag>
          <span class="row-spacer" />
          <span v-if="quotaOf(g.groupId)" class="row-quota">
            {{ formatBytes(quotaOf(g.groupId).occupied) }} / {{ formatBytes(quotaOf(g.groupId).size) }}
          </span>
        </button>

        <div v-if="expandedId === g.groupId" class="group-detail">
          <div v-if="quotaOf(g.groupId)" class="quota-block">
            <div class="quota-bar">
              <div
                class="quota-fill"
                :style="{ width: `${percent(quotaOf(g.groupId).occupied, quotaOf(g.groupId).size)}%` }"
              />
            </div>
            <p class="quota-text">
              {{ formatBytes(quotaOf(g.groupId).occupied) }} /
              {{ formatBytes(quotaOf(g.groupId).size) }}
            </p>
          </div>

          <div class="member-title">组成员</div>
          <ul class="member-list">
            <li v-for="m in g.members || []" :key="m.userId" class="member-item">
              <div class="member-info">
                <span class="member-name">{{ m.userName }}</span>
                <span class="member-email">{{ m.email }}</span>
              </div>
              <div class="member-actions">
                <Tag v-if="m.isAdmin" tone="warning">组管理员</Tag>
                <button class="tiny-btn" @click="toggleAdmin(m, g)">
                  {{ m.isAdmin ? '免除组管理员' : '任命为管理员' }}
                </button>
              </div>
            </li>
          </ul>

          <div class="group-actions">
            <Button variant="ghost" size="sm" @click="openRename(g)">修改组名</Button>
            <Button variant="ghost" size="sm" @click="openQuota(g)">设置配额</Button>
            <Button variant="ghost" size="sm" @click="openRequests(g)">加入请求</Button>
            <Button variant="ghost" size="sm" class="btn-danger" @click="deleteTarget = g">删除组</Button>
          </div>
        </div>
      </div>
    </div>

    <!-- 创建组 -->
    <Modal :open="createOpen" title="创建组" width="440px" @close="createOpen = false">
      <Input v-model="createName" label="组名" placeholder="请输入新组名称" required />
      <template #footer>
        <Button variant="ghost" @click="createOpen = false">取消</Button>
        <Button :loading="creating" @click="createGroup">创建</Button>
      </template>
    </Modal>

    <!-- 修改组名 -->
    <Modal :open="!!renameTarget" title="修改组名" width="440px" @close="renameTarget = null">
      <Input v-model="renameName" label="新组名" placeholder="请输入新的组名" required />
      <template #footer>
        <Button variant="ghost" @click="renameTarget = null">取消</Button>
        <Button :loading="renaming" @click="submitRename">保存</Button>
      </template>
    </Modal>

    <!-- 设置配额 -->
    <Modal :open="!!quotaTarget" title="设置存储配额" width="440px" @close="quotaTarget = null">
      <Input
        v-model="quotaSize"
        label="配额（字节，0 表示不限）"
        placeholder="例如：1073741824 表示 1GB"
        type="number"
        required
      />
      <template #footer>
        <Button variant="ghost" @click="quotaTarget = null">取消</Button>
        <Button :loading="quotaSetting" @click="submitQuota">保存</Button>
      </template>
    </Modal>

    <!-- 加入请求 -->
    <Modal
      :open="!!reqTarget"
      :title="`加入请求 · ${reqTarget?.groupName || ''}`"
      width="560px"
      @close="reqTarget = null"
    >
      <Spinner v-if="reqLoading" class="req-loading" :size="24" />
      <EmptyState v-else-if="!reqList.length" message="暂无加入请求" />
      <ul v-else class="req-list">
        <li v-for="r in reqList" :key="r.userId" class="req-item">
          <div class="req-info">
            <span class="req-name">{{ r.userName }}</span>
            <span class="req-email">{{ r.email }}</span>
          </div>
          <div class="req-actions">
            <Button variant="ghost" size="sm" :loading="reqBusy === r.userId" @click="reviewRequest(r.userId, 'APPROVED')">通过</Button>
            <Button variant="ghost" size="sm" class="btn-danger" :disabled="reqBusy === r.userId" @click="reviewRequest(r.userId, 'REJECTED')">拒绝</Button>
          </div>
        </li>
      </ul>
    </Modal>

    <!-- 删除确认 -->
    <ConfirmDialog
      :open="!!deleteTarget"
      title="删除组"
      :message="`确定删除组「${deleteTarget?.groupName || ''}」吗？此操作不可恢复。`"
      confirm-text="删除"
      danger
      :loading="deleting"
      @cancel="deleteTarget = null"
      @confirm="confirmDelete"
    />
  </div>
</template>

<style scoped>
.head {
  margin-bottom: 24px;
}
.head-row {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
}
.back-link {
  background: none;
  border: none;
  padding: 0;
  cursor: pointer;
  color: var(--text-secondary);
  font-size: 19px;
}
.back-link:hover {
  color: var(--text-primary);
}
.loading {
  display: block;
  margin: 80px auto;
}

.group-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.group-item {
  border: 1px solid var(--border-passive);
  border-radius: var(--radius-md);
  background: var(--surface);
  overflow: hidden;
}
.group-row {
  display: flex;
  align-items: center;
  gap: 12px;
  width: 100%;
  padding: 14px 16px;
  background: none;
  border: none;
  cursor: pointer;
  text-align: left;
  font-size: 19px;
}
.group-row:hover {
  background: rgba(28, 28, 28, 0.03);
}
.group-row.active {
  border-bottom: 1px solid var(--border-passive);
}
.chevron {
  color: var(--text-secondary);
  width: 14px;
  flex-shrink: 0;
}
.row-name {
  font-weight: 600;
  font-size: 19px;
}
.row-spacer {
  flex: 1;
}
.row-quota {
  font-size: 19px;
  color: var(--text-secondary);
}

.group-detail {
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 14px;
}
.quota-block {
  margin-bottom: 2px;
}
.quota-bar {
  height: 6px;
  background: rgba(28, 28, 28, 0.08);
  border-radius: var(--radius-full);
  overflow: hidden;
}
.quota-fill {
  height: 100%;
  background: var(--text-primary);
  border-radius: var(--radius-full);
}
.quota-text {
  margin: 6px 0 0;
  font-size: 19px;
  color: var(--text-secondary);
}
.member-title {
  font-size: 19px;
  font-weight: 600;
  color: var(--text-secondary);
}
.member-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.member-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  padding: 8px 10px;
  border: 1px solid var(--border-passive);
  border-radius: var(--radius-sm);
}
.member-info {
  display: flex;
  flex-direction: column;
  min-width: 0;
}
.member-name {
  font-size: 19px;
  font-weight: 600;
}
.member-email {
  font-size: 19px;
  color: var(--text-secondary);
}
.member-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
}
.tiny-btn {
  background: none;
  border: 1px solid var(--border-interactive);
  border-radius: var(--radius-sm);
  padding: 3px 8px;
  font-size: 19px;
  cursor: pointer;
}
.tiny-btn:hover {
  box-shadow: var(--shadow-focus);
}
.group-actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  border-top: 1px solid var(--border-passive);
  padding-top: 14px;
}
.btn-danger {
  color: var(--color-danger);
}
.req-loading {
  display: block;
  margin: 24px auto;
}
.req-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.req-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 10px 12px;
  border: 1px solid var(--border-passive);
  border-radius: var(--radius-sm);
}
.req-info {
  display: flex;
  flex-direction: column;
}
.req-name {
  font-weight: 600;
  font-size: 19px;
}
.req-email {
  font-size: 19px;
  color: var(--text-secondary);
}
.req-actions {
  display: flex;
  gap: 8px;
}
</style>
