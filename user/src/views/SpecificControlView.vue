<script setup>
import { onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useGroupStore } from '../stores/group'
import * as accountApi from '../api/account'
import * as fileLogicApi from '../api/fileLogic'
import * as fileIoApi from '../api/fileIo'
import { downloadByUrl } from '../utils/download'
import { toast } from '../stores/toast'
import Card from '../components/ui/Card.vue'
import Button from '../components/ui/Button.vue'
import Modal from '../components/ui/Modal.vue'
import Spinner from '../components/ui/Spinner.vue'
import EmptyState from '../components/ui/EmptyState.vue'
import FileList from '../components/business/FileList.vue'
import FilePickerDialog from '../components/business/FilePickerDialog.vue'

const router = useRouter()
const group = useGroupStore()

const pages = ref([])
const current = ref(null) // { specificPageId, visibleGroups, announcement }
const pageFiles = ref([])
const announcement = ref('')
const loading = ref(true)
const pickOpen = ref(false)
const saving = ref(false)

const addOpen = ref(false)
const removeOpen = ref(false)
const pickerTitle = ref('')

const allGroups = ref([]) // [{groupId, groupName}] 用于可见组选择

const createOpen = ref(false)
const createForm = reactive({ announcement: '', visibleGroups: [] })
const creating = ref(false)

const visibleOpen = ref(false)
const visibleSelection = ref([])
const savingVisible = ref(false)

const deleteOpen = ref(false)
const deleting = ref(false)

function groupNameById(gid) {
  return allGroups.value.find((g) => g.groupId === gid)?.groupName ?? gid
}

async function loadGroups() {
  try {
    allGroups.value = await accountApi.getAllGroups()
  } catch {
    /* 组列表加载失败不阻塞页面 */
  }
}

onMounted(async () => {
  loading.value = true
  try {
    await group.initGroup()
    loadGroups()
    pages.value = await fileLogicApi.getGroupSpecificPages(group.groupId)
    if (pages.value.length === 1) {
      await selectPage(pages.value[0])
    } else {
      pickOpen.value = true
    }
  } catch {
    /* 错误提示已由请求层统一处理 */
  } finally {
    loading.value = false
  }
})

function openCreate() {
  createForm.announcement = ''
  createForm.visibleGroups = []
  createOpen.value = true
}

async function confirmCreate() {
  if (!createForm.announcement.trim()) {
    toast('请输入公告内容', 'warning')
    return
  }
  creating.value = true
  try {
    await fileLogicApi.createSpecificPage(group.groupId, {
      announcement: createForm.announcement.trim(),
      visibleGroups: createForm.visibleGroups,
    })
    toast('指定页创建成功', 'success')
    createOpen.value = false
    pages.value = await fileLogicApi.getGroupSpecificPages(group.groupId)
    if (pages.value.length === 1) {
      await selectPage(pages.value[0])
    } else {
      pickOpen.value = true
    }
  } catch {
    /* 错误提示已由请求层统一处理 */
  } finally {
    creating.value = false
  }
}

function openVisibleGroups() {
  if (!current.value) return
  visibleSelection.value = [...(current.value.visibleGroups || [])]
  visibleOpen.value = true
}

async function confirmVisibleGroups() {
  if (!current.value) return
  savingVisible.value = true
  try {
    const updated = await fileLogicApi.updateSpecificPage(
      group.groupId,
      current.value.specificPageId,
      { visibleGroups: visibleSelection.value },
    )
    current.value.visibleGroups = updated.visibleGroups ?? visibleSelection.value
    toast('可见组已更新', 'success')
    visibleOpen.value = false
  } catch {
    /* 错误提示已由请求层统一处理 */
  } finally {
    savingVisible.value = false
  }
}

function openDeleteConfirm() {
  deleteOpen.value = true
}

async function confirmDelete() {
  if (!current.value) return
  deleting.value = true
  try {
    await fileLogicApi.deleteSpecificPage(group.groupId, current.value.specificPageId)
    toast('指定页已删除', 'success')
    deleteOpen.value = false
    current.value = null
    pageFiles.value = []
    pages.value = await fileLogicApi.getGroupSpecificPages(group.groupId)
    if (pages.value.length === 1) {
      await selectPage(pages.value[0])
    } else {
      pickOpen.value = true
    }
  } catch {
    /* 错误提示已由请求层统一处理 */
  } finally {
    deleting.value = false
  }
}

async function selectPage(page) {
  current.value = page
  announcement.value = page.announcement || ''
  pickOpen.value = false
  const res = await fileLogicApi.getSpecificPageFiles(group.groupId, page.specificPageId)
  pageFiles.value = res.info || []
}

function backToList() {
  pickOpen.value = true
}

async function saveAnnouncement() {
  if (!current.value) return
  saving.value = true
  try {
    await fileLogicApi.updateSpecificPage(group.groupId, current.value.specificPageId, {
      announcement: announcement.value,
    })
    toast('公告已更新', 'success')
  } catch {
    /* 错误提示已由请求层统一处理 */
  } finally {
    saving.value = false
  }
}

function openAdd() {
  pickerTitle.value = '选择要添加到指定页的文件'
  addOpen.value = true
}

async function onAdd(fileIds) {
  try {
    for (const id of fileIds) {
      await fileLogicApi.addFileToSpecificPage(group.groupId, current.value.specificPageId, id)
    }
    toast(`已添加 ${fileIds.length} 个文件`, 'success')
    await selectPage(current.value)
  } catch {
    /* 错误提示已由拦截器处理 */
  }
}

function openRemove() {
  pickerTitle.value = '选择要从指定页移除的文件'
  removeOpen.value = true
}

async function onRemove(fileIds) {
  try {
    for (const id of fileIds) {
      await fileLogicApi.removeFileFromSpecificPage(
        group.groupId,
        current.value.specificPageId,
        id,
      )
    }
    toast(`已移除 ${fileIds.length} 个文件`, 'success')
    await selectPage(current.value)
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
      <h2>指定页控制</h2>
      <p class="muted">选择指定页进行管理：修改公告、添加或移除文件。</p>
    </header>

    <Spinner v-if="loading" class="loading" :size="32" />

    <template v-else-if="current">
      <div class="current-bar">
        <span class="current-label">当前指定页</span>
        <span class="current-id">#{{ current.specificPageId }}</span>
        <Button variant="ghost" size="sm" @click="backToList">切换指定页</Button>
        <Button variant="danger" size="sm" @click="openDeleteConfirm">删除指定页</Button>
      </div>

      <div class="control-grid">
        <Card class="ctrl-card">
          <h3>修改公告</h3>
          <textarea
            v-model="announcement"
            class="announce-input"
            rows="4"
            placeholder="输入指定页公告内容…"
          />
          <Button :loading="saving" @click="saveAnnouncement">保存公告</Button>
        </Card>

        <Card class="ctrl-card">
          <div class="ctrl-head">
            <h3>可见组（{{ current.visibleGroups.length }}）</h3>
            <Button variant="ghost" size="sm" @click="openVisibleGroups">编辑可见组</Button>
          </div>
          <div v-if="current.visibleGroups.length" class="group-tags">
            <span v-for="gid in current.visibleGroups" :key="gid" class="group-tag">
              {{ groupNameById(gid) }}
            </span>
          </div>
          <p v-else class="muted">暂无可见组，其他组将无法查看本指定页</p>
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
    </template>

    <EmptyState v-else message="请选择要管理的指定页" hint="点击下方按钮打开指定页列表" />

    <!-- 选择指定页的拟态框 -->
    <Modal :open="pickOpen" title="选择指定页" width="520px" @close="router.push('/group-space')">
      <p class="muted pick-hint">进入指定页控制前，请选择要管理的指定页。</p>
      <div class="pick-create">
        <Button variant="cream" size="sm" @click="openCreate">＋ 创建指定页</Button>
      </div>
      <div class="page-select-list">
        <button
          v-for="p in pages"
          :key="p.specificPageId"
          class="page-select-item"
          @click="selectPage(p)"
        >
          <span class="item-id">指定页 #{{ p.specificPageId }}</span>
          <span class="item-desc">{{ p.announcement || '暂无公告' }}</span>
        </button>
        <EmptyState
          v-if="!pages.length"
          message="本组暂无指定页"
          hint="点击上方按钮创建第一个指定页"
        />
      </div>
    </Modal>

    <!-- 创建指定页的拟态框 -->
    <Modal :open="createOpen" title="创建指定页" width="520px" @close="createOpen = false">
      <div class="form-item">
        <label class="form-label">公告内容</label>
        <textarea
          v-model="createForm.announcement"
          class="announce-input"
          rows="4"
          placeholder="输入指定页公告内容…"
        />
      </div>
      <div class="form-item">
        <label class="form-label">可见组（{{ createForm.visibleGroups.length }}）</label>
        <div class="group-check-list">
          <label
            v-for="g in allGroups"
            :key="g.groupId"
            class="group-check-item"
            :class="{ 'is-checked': createForm.visibleGroups.includes(g.groupId) }"
          >
            <input v-model="createForm.visibleGroups" type="checkbox" :value="g.groupId" />
            <span>{{ g.groupName }}</span>
          </label>
          <p v-if="!allGroups.length" class="muted">组列表加载中…</p>
        </div>
      </div>
      <template #footer>
        <Button variant="ghost" @click="createOpen = false">取消</Button>
        <Button :loading="creating" @click="confirmCreate">创建</Button>
      </template>
    </Modal>

    <!-- 编辑可见组的拟态框 -->
    <Modal :open="visibleOpen" title="编辑可见组" width="520px" @close="visibleOpen = false">
      <p class="muted pick-hint">勾选可查看本指定页的组，未勾选的组将无法看到该页。</p>
      <div class="group-check-list">
        <label
          v-for="g in allGroups"
          :key="g.groupId"
          class="group-check-item"
          :class="{ 'is-checked': visibleSelection.includes(g.groupId) }"
        >
          <input v-model="visibleSelection" type="checkbox" :value="g.groupId" />
          <span>{{ g.groupName }}</span>
        </label>
        <p v-if="!allGroups.length" class="muted">组列表加载中…</p>
      </div>
      <template #footer>
        <Button variant="ghost" @click="visibleOpen = false">取消</Button>
        <Button :loading="savingVisible" @click="confirmVisibleGroups">保存</Button>
      </template>
    </Modal>

    <!-- 删除指定页的确认拟态框 -->
    <Modal :open="deleteOpen" title="删除指定页" width="460px" @close="deleteOpen = false">
      <p>确定要删除指定页 <strong>#{{ current?.specificPageId }}</strong> 吗？</p>
      <p class="muted">删除后将移除该页及其全部可见组关系，且不可恢复。</p>
      <template #footer>
        <Button variant="ghost" @click="deleteOpen = false">取消</Button>
        <Button variant="danger" :loading="deleting" @click="confirmDelete">确认删除</Button>
      </template>
    </Modal>

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
.current-bar {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 20px;
}
.current-label {
  color: var(--text-secondary);
  font-size: 19px;
}
.current-id {
  font-weight: 600;
  font-size: 19px;
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
.pick-hint {
  margin-bottom: 16px;
  font-size: 19px;
}
.page-select-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.page-select-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
  align-items: flex-start;
  padding: 12px 14px;
  background: var(--bg-cream);
  border: 1px solid var(--border-passive);
  border-radius: var(--radius-sm);
  cursor: pointer;
  text-align: left;
}
.page-select-item:hover {
  box-shadow: var(--shadow-focus);
}
.item-id {
  font-weight: 600;
}
.item-desc {
  font-size: 19px;
  color: var(--text-secondary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  width: 100%;
}
.group-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
.group-tag {
  padding: 4px 12px;
  background: var(--bg-cream);
  border: 1px solid var(--border-passive);
  border-radius: var(--radius-full);
  font-size: 19px;
  color: var(--text-primary);
}
.pick-create {
  margin-bottom: 16px;
}
.form-item {
  margin-bottom: 16px;
}
.form-label {
  display: block;
  margin-bottom: 8px;
  font-weight: 600;
}
.group-check-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
  max-height: 260px;
  overflow-y: auto;
}
.group-check-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  background: var(--bg-cream);
  border: 1px solid var(--border-passive);
  border-radius: var(--radius-sm);
  cursor: pointer;
  font-size: 19px;
}
.group-check-item.is-checked {
  border-color: var(--color-accent);
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.15);
}
.group-check-item input {
  width: 16px;
  height: 16px;
  accent-color: var(--color-accent);
}
</style>
