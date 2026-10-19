<script setup>
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { useGroupStore } from '../stores/group'
import * as fileLogicApi from '../api/fileLogic'
import * as fileIoApi from '../api/fileIo'
import { downloadByUrl } from '../utils/download'
import { toast } from '../stores/toast'
import Card from '../components/ui/Card.vue'
import Button from '../components/ui/Button.vue'
import Spinner from '../components/ui/Spinner.vue'
import EmptyState from '../components/ui/EmptyState.vue'
import FileList from '../components/business/FileList.vue'
import FilePickerDialog from '../components/business/FilePickerDialog.vue'

const router = useRouter()
const auth = useAuthStore()
const group = useGroupStore()

const pageInfo = ref(null) // { groupId, groupName, publicPageId, announcement }
const pageFiles = ref([])
const announcement = ref('')
const loading = ref(true)
const saving = ref(false)

const addOpen = ref(false)
const removeOpen = ref(false)
const pickerTitle = ref('')

onMounted(() => load().catch(() => {}))

async function load() {
  loading.value = true
  try {
    await group.initGroup()
    const all = await fileLogicApi.getPublicPages()
    pageInfo.value = all.find((p) => p.groupId === group.groupId) || null
    if (pageInfo.value) {
      announcement.value = pageInfo.value.announcement || ''
      const res = await fileLogicApi.getPublicPageFiles(group.groupId)
      pageFiles.value = res.info || []
    }
  } finally {
    loading.value = false
  }
}

async function saveAnnouncement() {
  if (!pageInfo.value) return
  saving.value = true
  try {
    await fileLogicApi.updatePublicPageAnnouncement(
      group.groupId,
      pageInfo.value.publicPageId,
      announcement.value,
    )
    toast('公告已更新', 'success')
  } catch {
    /* 错误提示已由请求层统一处理 */
  } finally {
    saving.value = false
  }
}

function openAdd() {
  pickerTitle.value = '选择要添加到公开页的文件'
  addOpen.value = true
}

async function onAdd(fileIds) {
  try {
    for (const id of fileIds) {
      await fileLogicApi.addFileToPublicPage(group.groupId, id)
    }
    toast(`已添加 ${fileIds.length} 个文件`, 'success')
    await load()
  } catch {
    /* 错误提示已由拦截器处理 */
  }
}

function openRemove() {
  pickerTitle.value = '选择要从公开页移除的文件'
  removeOpen.value = true
}

async function onRemove(fileIds) {
  try {
    for (const id of fileIds) {
      await fileLogicApi.removeFileFromPublicPage(group.groupId, id)
    }
    toast(`已移除 ${fileIds.length} 个文件`, 'success')
    await load()
  } catch {
    /* 错误提示已由拦截器处理 */
  }
}

async function handleDownload(file) {
  const { fileURL, fileName } = await fileIoApi.getDownloadLink(group.groupId, file.fileId)
  downloadByUrl(fileURL, fileName)
}
</script>

<template>
  <div class="page">
    <header class="head">
      <button class="back-link" @click="router.push('/group-space')">← 组空间</button>
      <h2>公开页控制</h2>
      <p class="muted">修改本组公开页的公告，并管理公开页展示的文件。</p>
    </header>

    <Spinner v-if="loading" class="loading" :size="32" />
    <EmptyState
      v-else-if="!pageInfo"
      message="未找到本组的公开页"
      hint="请联系系统管理员确认公开页已创建"
    />

    <div v-else class="control-grid">
      <Card class="ctrl-card">
        <h3>修改公告</h3>
        <textarea
          v-model="announcement"
          class="announce-input"
          rows="4"
          placeholder="输入公开页公告内容…"
        />
        <Button :loading="saving" @click="saveAnnouncement">保存公告</Button>
      </Card>

      <Card class="ctrl-card">
        <div class="ctrl-head">
          <h3>页面文件（{{ pageFiles.length }}）</h3>
          <div class="ctrl-actions">
            <Button variant="ghost" size="sm" @click="openAdd">添加文件</Button>
            <Button variant="ghost" size="sm" @click="openRemove">移除文件</Button>
          </div>
        </div>
        <FileList :files="pageFiles" @download="handleDownload" />
      </Card>
    </div>

    <FilePickerDialog
      :group-id="group.groupId"
      :open="addOpen"
      :title="pickerTitle"
      :exclude-ids="pageFiles.map((f) => f.fileId)"
      @close="addOpen = false"
      @confirm="onAdd"
    />

    <FilePickerDialog
      :group-id="group.groupId"
      :open="removeOpen"
      :title="pickerTitle"
      :files="pageFiles"
      @close="removeOpen = false"
      @confirm="onRemove"
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
.loading {
  display: block;
  margin: 64px auto;
}
.control-grid {
  display: flex;
  flex-direction: column;
  gap: 20px;
}
.announce-input {
  width: 100%;
  padding: 10px 12px;
  background: var(--bg-cream);
  border: 1px solid var(--border-passive);
  border-radius: var(--radius-sm);
  font-size: 19px;
  resize: vertical;
  margin-bottom: 14px;
}
.announce-input:focus {
  outline: none;
  border-color: var(--color-accent);
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.5);
}
.ctrl-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
  margin-bottom: 12px;
}
.ctrl-head h3 {
  margin: 0;
}
.ctrl-actions {
  display: flex;
  gap: 8px;
}
</style>
