<script setup>
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import * as systemApi from '../api/system'
import { toast } from '../stores/toast'
import Card from '../components/ui/Card.vue'
import Button from '../components/ui/Button.vue'
import Input from '../components/ui/Input.vue'
import Spinner from '../components/ui/Spinner.vue'
import EmptyState from '../components/ui/EmptyState.vue'
import ConfirmDialog from '../components/ui/ConfirmDialog.vue'

const router = useRouter()

const domains = ref([])
const newDomain = ref('')
const loading = ref(true)
const adding = ref(false)
const removeTarget = ref('')
const removing = ref(false)

onMounted(load)

async function load() {
  loading.value = true
  try {
    domains.value = await systemApi.getAccessibleDomains()
  } finally {
    loading.value = false
  }
}

async function addDomain() {
  const value = newDomain.value.trim()
  if (!value) {
    toast('请输入可访问域', 'warning')
    return
  }
  adding.value = true
  try {
    await systemApi.addAccessibleDomain(value)
    toast('可访问域已添加', 'success')
    newDomain.value = ''
    await load()
  } catch {
    /* 错误提示已由请求层统一处理 */
  } finally {
    adding.value = false
  }
}

function askRemove(domain) {
  removeTarget.value = domain
}

async function confirmRemove() {
  removing.value = true
  try {
    await systemApi.removeAccessibleDomain(removeTarget.value)
    toast('可访问域已删除', 'success')
    removeTarget.value = ''
    await load()
  } catch {
    /* 错误提示已由请求层统一处理 */
  } finally {
    removing.value = false
  }
}
</script>

<template>
  <div class="page">
    <header class="head">
      <button class="back-link" @click="router.push('/admin')">← 系统管理员界面</button>
      <h2>可访问域</h2>
      <p class="muted">系统允许访问的网络域列表，添加后对应域可访问本系统。</p>
    </header>

    <Card class="add-card">
      <div class="add-row">
        <Input v-model="newDomain" placeholder="例如：example.com" />
        <Button :loading="adding" @click="addDomain">添加</Button>
      </div>
    </Card>

    <Card class="list-card">
      <Spinner v-if="loading" class="loading" :size="28" />
      <EmptyState
        v-else-if="!domains.length"
        message="暂无可访问域"
        hint="点击上方输入框添加"
      />
      <ul v-else class="domain-list">
        <li v-for="d in domains" :key="d" class="domain-item">
          <span class="domain-value">域： {{ d }}</span>
          <button class="remove-btn" title="删除" @click="askRemove(d)">✕</button>
        </li>
      </ul>
    </Card>

    <ConfirmDialog
      :open="!!removeTarget"
      title="删除可访问域"
      :message="`确定删除可访问域「${removeTarget}」吗？删除后该域将无法访问系统。`"
      confirm-text="删除"
      danger
      :loading="removing"
      @cancel="removeTarget = ''"
      @confirm="confirmRemove"
    />
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
.add-card {
  margin-bottom: 20px;
}
.add-row {
  display: flex;
  gap: 12px;
  align-items: flex-end;
}
.add-row > * {
  flex: 1;
}
.add-row > button {
  flex: 0 0 auto;
}
.loading {
  display: block;
  margin: 32px auto;
}
.domain-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.domain-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 14px;
  border: 1px solid var(--border-passive);
  border-radius: var(--radius-sm);
}
.domain-item:hover {
  box-shadow: var(--shadow-focus);
}
.domain-value {
  font-weight: 600;
  font-size: 19px;
}
.remove-btn {
  width: 28px;
  height: 28px;
  border: 1px solid var(--border-passive);
  background: transparent;
  border-radius: var(--radius-full);
  cursor: pointer;
  color: var(--color-danger);
}
.remove-btn:hover {
  box-shadow: var(--shadow-focus);
}
</style>
