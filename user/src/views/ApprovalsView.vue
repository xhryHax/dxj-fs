<script setup>
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useGroupStore } from '../stores/group'
import * as accountApi from '../api/account'
import { toast } from '../stores/toast'
import Card from '../components/ui/Card.vue'
import Button from '../components/ui/Button.vue'
import Spinner from '../components/ui/Spinner.vue'
import EmptyState from '../components/ui/EmptyState.vue'
import Tag from '../components/ui/Tag.vue'

const router = useRouter()
const group = useGroupStore()

const requests = ref([])
const loading = ref(true)
const pendingId = ref(null) // 正在处理的请求

onMounted(() => load().catch(() => {}))

async function load() {
  loading.value = true
  try {
    await group.initGroup()
    requests.value = await accountApi.getGroupJoinRequests(group.groupId)
  } finally {
    loading.value = false
  }
}

async function review(userId, status) {
  pendingId.value = userId
  try {
    await accountApi.reviewJoinRequest(group.groupId, userId, status)
    toast(status === 'APPROVED' ? '已通过该请求' : '已拒绝该请求', 'success')
    await load()
  } catch {
    /* 错误提示已由请求层统一处理 */
  } finally {
    pendingId.value = null
  }
}
</script>

<template>
  <div class="page">
    <header class="head">
      <button class="back-link" @click="router.push('/group-space')">← 组空间</button>
      <h2>审批加入请求</h2>
      <p class="muted">审批申请加入本组的用户请求。</p>
    </header>

    <Spinner v-if="loading" class="loading" :size="32" />

    <Card v-else class="approval-card">
      <EmptyState
        v-if="!requests.length"
        message="暂无待审批的加入请求"
        hint="新的加入请求会显示在这里"
      />
      <ul v-else class="req-list">
        <li v-for="r in requests" :key="r.userId" class="req-item">
          <div class="req-info">
            <span class="req-name">{{ r.userName || '未命名用户' }}</span>
            <span class="req-email">{{ r.email }}</span>
          </div>
          <div class="req-actions">
            <Tag v-if="r.status" tone="warning" size="md">{{ r.status }}</Tag>
            <Button
              variant="ghost"
              size="sm"
              :loading="pendingId === r.userId"
              @click="review(r.userId, 'APPROVED')"
            >
              通过
            </Button>
            <Button
              variant="ghost"
              size="sm"
              class="btn-reject"
              :disabled="pendingId === r.userId"
              @click="review(r.userId, 'REJECTED')"
            >
              拒绝
            </Button>
          </div>
        </li>
      </ul>
    </Card>
  </div>
</template>

<style scoped>
.head {
  margin-bottom: 24px;
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
  margin: 64px auto;
}
.req-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.req-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 14px 16px;
  border: 1px solid var(--border-passive);
  border-radius: var(--radius-sm);
  flex-wrap: wrap;
}
.req-item:hover {
  box-shadow: var(--shadow-focus);
}
.req-info {
  display: flex;
  flex-direction: column;
  min-width: 0;
}
.req-name {
  font-weight: 600;
}
.req-email {
  font-size: 19px;
  color: var(--text-secondary);
}
.req-actions {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}
.btn-reject {
  color: var(--color-danger);
}
</style>
