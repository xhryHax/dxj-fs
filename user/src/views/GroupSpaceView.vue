<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { useGroupStore } from '../stores/group'
import * as fileLogicApi from '../api/fileLogic'
import * as fileIoApi from '../api/fileIo'
import { DEFAULT_FILE_PAGE_SIZE } from '../constants'
import { downloadByUrl } from '../utils/download'
import { toast } from '../stores/toast'
import Button from '../components/ui/Button.vue'
import Card from '../components/ui/Card.vue'
import Tag from '../components/ui/Tag.vue'
import Spinner from '../components/ui/Spinner.vue'
import ConfirmDialog from '../components/ui/ConfirmDialog.vue'
import MemberSidebar from '../components/business/MemberSidebar.vue'
import FileFilterBar from '../components/business/FileFilterBar.vue'
import FileTable from '../components/business/FileTable.vue'
import UploadDialog from '../components/business/UploadDialog.vue'
import RenameDialog from '../components/business/RenameDialog.vue'
import RestoreDialog from '../components/business/RestoreDialog.vue'

const router = useRouter()
const auth = useAuthStore()
const group = useGroupStore()

const files = ref([])
const loading = ref(true)
const selected = ref([])
const filters = reactive({ label: '', uploader: '', sortBy: 'atCreated', sortDir: 'desc' })

const uploadOpen = ref(false)
const renameOpen = ref(false)
const renameTargets = ref([])
const restoreOpen = ref(false)
const confirmRemoveOpen = ref(false)
const removing = ref(false)

onMounted(() => load().catch(() => {}))

async function load() {
  loading.value = true
  try {
    await group.initGroup()
    await loadFiles()
  } finally {
    loading.value = false
  }
}

async function loadFiles() {
  const res = await fileLogicApi.getGroupFiles(group.groupId, 0, DEFAULT_FILE_PAGE_SIZE)
  files.value = res.info || []
  selected.value = []
}

const labels = computed(() => [...new Set(files.value.map((f) => f.label).filter(Boolean))])
const uploaders = computed(() => [...new Set(files.value.map((f) => f.uploader).filter(Boolean))])

const filteredFiles = computed(() => {
  let list = files.value.filter(
    (f) =>
      (!filters.label || f.label === filters.label) &&
      (!filters.uploader || f.uploader === filters.uploader),
  )
  list = [...list].sort((a, b) => {
    const r =
      filters.sortBy === 'size'
        ? Number(a.size) - Number(b.size)
        : new Date(a.atCreated) - new Date(b.atCreated)
    return filters.sortDir === 'desc' ? -r : r
  })
  return list
})

function toggleAll(checked) {
  selected.value = checked ? filteredFiles.value.map((f) => f.fileId) : []
}

function onSelect(next) {
  selected.value = next
}

async function handleDownload(file) {
  try {
    const { fileURL, fileName } = await fileIoApi.getDownloadLink(group.groupId, file.fileId)
    downloadByUrl(fileURL, fileName)
  } catch {
    /* 错误提示已由拦截器统一处理 */
  }
}

async function downloadSelected() {
  for (const id of selected.value) {
    const f = files.value.find((x) => x.fileId === id)
    if (f) await handleDownload(f)
  }
}

function openRename(file) {
  renameTargets.value = file
    ? [file]
    : files.value.filter((f) => selected.value.includes(f.fileId))
  renameOpen.value = true
}

function askRemove(file) {
  renameTargets.value = file ? [file] : []
  confirmRemoveOpen.value = true
}

async function confirmRemove() {
  const targets = renameTargets.value.length
    ? renameTargets.value
    : files.value.filter((f) => selected.value.includes(f.fileId))
  if (!targets.length) {
    toast('请先选择要删除的文件', 'warning')
    confirmRemoveOpen.value = false
    return
  }
  removing.value = true
  try {
    for (const f of targets) {
      await fileLogicApi.softDeleteFile(group.groupId, f.fileId)
    }
    toast(`已删除 ${targets.length} 个文件`, 'success')
    confirmRemoveOpen.value = false
    await loadFiles()
  } catch {
    /* 错误提示已由请求层统一处理 */
  } finally {
    removing.value = false
  }
}

function onUploaded() {
  loadFiles()
}
</script>

<template>
  <div class="page">
    <header class="gs-head">
      <div>
        <button class="back-link" @click="router.push('/profile')">← 个人中心</button>
        <h2 class="gs-title">组空间 · {{ group.groupName || `组 #${auth.user?.groupId}` }}</h2>
      </div>
      <Tag v-if="group.isGroupAdmin" tone="warning" size="md">组管理员</Tag>
    </header>

    <Spinner v-if="loading" class="gs-loading" :size="36" />

    <div v-else class="gs-layout">
      <MemberSidebar
        :group-name="group.groupName"
        :members="group.members"
        :storage="group.storageQuota"
      />

      <main class="gs-main">
        <div class="toolbar">
          <Button @click="uploadOpen = true">上传文件</Button>
          <Button variant="ghost" :disabled="!selected.length" @click="downloadSelected">
            下载
          </Button>
          <Button variant="ghost" :disabled="!selected.length" @click="openRename(null)">
            重命名
          </Button>
          <Button variant="ghost" :disabled="!selected.length" class="btn-danger" @click="askRemove(null)">
            删除
          </Button>

          <span class="toolbar-spacer" />

          <template v-if="group.isGroupAdmin">
            <Button variant="cream" @click="restoreOpen = true">文件恢复</Button>
            <Button variant="cream" @click="router.push('/group-space/approvals')">
              审批加入请求
            </Button>
            <Button variant="cream" @click="router.push('/group-space/public-control')">
              公开页控制
            </Button>
            <Button variant="cream" @click="router.push('/group-space/specific-control')">
              指定页控制
            </Button>
          </template>
        </div>

        <Card padded>
          <FileFilterBar
            :filters="filters"
            :labels="labels"
            :uploaders="uploaders"
            @update="Object.assign(filters, $event)"
          />
        </Card>

        <FileTable
          :files="filteredFiles"
          :selected="selected"
          @select="onSelect"
          @toggle-all="toggleAll"
          @rename="openRename($event)"
          @download="handleDownload($event)"
          @remove="askRemove($event)"
        />

        <p class="file-count">共加载 {{ files.length }} 个文件 · 当前显示 {{ filteredFiles.length }} 个</p>
      </main>
    </div>

    <UploadDialog
      :group-id="group.groupId"
      :open="uploadOpen"
      @close="uploadOpen = false"
      @uploaded="onUploaded"
    />

    <RenameDialog
      :group-id="group.groupId"
      :open="renameOpen"
      :files="renameTargets"
      @close="renameOpen = false"
      @renamed="loadFiles"
    />

    <RestoreDialog
      :group-id="group.groupId"
      :open="restoreOpen"
      @close="restoreOpen = false"
      @restored="loadFiles"
      @deleted="loadFiles"
    />

    <ConfirmDialog
      :open="confirmRemoveOpen"
      title="删除文件"
      message="删除后文件将移入回收站，组管理员可将其恢复。确定继续吗？"
      confirm-text="删除"
      danger
      :loading="removing"
      @cancel="confirmRemoveOpen = false"
      @confirm="confirmRemove"
    />
  </div>
</template>

<style scoped>
.gs-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
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
.gs-title {
  margin: 4px 0 0;
}
.gs-loading {
  display: block;
  margin: 80px auto;
}
.gs-layout {
  display: grid;
  grid-template-columns: 260px 1fr;
  gap: 20px;
  align-items: start;
}
.gs-main {
  display: flex;
  flex-direction: column;
  gap: 14px;
  min-width: 0;
}
.toolbar {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
  align-items: center;
}
.toolbar-spacer {
  flex: 1;
}
.btn-danger {
  color: var(--color-danger);
}
.file-count {
  font-size: 19px;
  color: var(--text-secondary);
  margin: 0;
}
@media (max-width: 900px) {
  .gs-layout {
    grid-template-columns: 1fr;
  }
}
</style>
