<script setup>
import { ref, watch } from 'vue'
import * as fileLogicApi from '../../api/fileLogic'
import { toast } from '../../stores/toast'
import { formatBytes, formatDateTime } from '../../utils/format'
import Modal from '../ui/Modal.vue'
import Button from '../ui/Button.vue'
import EmptyState from '../ui/EmptyState.vue'
import Spinner from '../ui/Spinner.vue'

const props = defineProps({
  groupId: { type: [String, Number], default: null },
  open: { type: Boolean, default: false },
})
const emit = defineEmits(['close', 'restored', 'deleted'])

const deleted = ref([])
const selected = ref([])
const loading = ref(false)
const restoring = ref(false)
const deleting = ref(false)
const confirmDelete = ref(false)

async function load() {
  loading.value = true
  try {
    const res = await fileLogicApi.getDeletedFiles(props.groupId, 0, 5000)
    deleted.value = res.info || []
    selected.value = []
  } finally {
    loading.value = false
  }
}

watch(
  () => props.open,
  (v) => {
    if (v) load().catch(() => {})
  },
)

function toggle(id) {
  selected.value = selected.value.includes(id)
    ? selected.value.filter((x) => x !== id)
    : [...selected.value, id]
}

async function restore() {
  if (!selected.value.length) {
    toast('请先选择要恢复的文件', 'warning')
    return
  }
  restoring.value = true
  try {
    for (const id of selected.value) {
      await fileLogicApi.restoreFile(props.groupId, id)
    }
    toast('文件恢复成功', 'success')
    emit('restored')
    emit('close')
  } catch {
    /* 错误提示已由请求层统一处理 */
  } finally {
    restoring.value = false
  }
}

async function hardDelete() {
  if (!selected.value.length) return
  deleting.value = true
  try {
    for (const id of selected.value) {
      await fileLogicApi.hardDeleteFile(props.groupId, id)
    }
    toast('文件已彻底删除', 'success')
    emit('deleted')
    emit('close')
  } catch {
    /* 错误提示已由请求层统一处理 */
  } finally {
    deleting.value = false
    confirmDelete.value = false
  }
}
</script>

<template>
  <Modal :open="open" title="恢复已删除文件" width="640px" @close="emit('close')">
    <div class="restore-body">
      <Spinner v-if="loading" class="restore-loading" :size="24" />
      <EmptyState
        v-else-if="!deleted.length"
        message="回收站是空的"
        hint="被删除的文件会出现在这里，可选中后恢复"
      />
      <template v-else>
        <ul class="deleted-list">
          <li v-for="f in deleted" :key="f.fileId" class="deleted-item">
            <input
              type="checkbox"
              class="deleted-check"
              :checked="selected.includes(f.fileId)"
              @change="toggle(f.fileId)"
            />
            <div class="deleted-info">
              <span class="deleted-name">{{ f.fileName }}</span>
              <span class="deleted-meta">
                {{ formatBytes(f.size) }} · 删除于 {{ formatDateTime(f.atDeleted) }}
              </span>
            </div>
          </li>
        </ul>
      </template>
    </div>
    <template #footer>
      <template v-if="confirmDelete">
        <span class="confirm-text">将彻底删除 {{ selected.length }} 个文件，此操作不可恢复</span>
        <Button variant="ghost" :disabled="deleting" @click="confirmDelete = false">取消</Button>
        <Button variant="danger" :loading="deleting" @click="hardDelete">确认彻底删除</Button>
      </template>
      <template v-else>
        <Button
          variant="ghost"
          class="delete-btn"
          :disabled="!selected.length || restoring"
          @click="confirmDelete = true"
        >
          彻底删除
        </Button>
        <span class="foot-spacer" />
        <Button variant="ghost" :disabled="restoring || deleting" @click="emit('close')">取消</Button>
        <Button :loading="restoring" :disabled="!selected.length" @click="restore">
          恢复选中（{{ selected.length }}）
        </Button>
      </template>
    </template>
  </Modal>
</template>

<style scoped>
.restore-body {
  min-height: 120px;
}
.restore-loading {
  display: block;
  margin: 32px auto;
}
.deleted-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.deleted-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 12px;
  border: 1px solid var(--border-passive);
  border-radius: var(--radius-sm);
}
.deleted-item:hover {
  box-shadow: var(--shadow-focus);
}
.deleted-check {
  width: 16px;
  height: 16px;
  accent-color: var(--text-primary);
  cursor: pointer;
}
.deleted-info {
  display: flex;
  flex-direction: column;
  min-width: 0;
}
.deleted-name {
  font-weight: 600;
  font-size: 19px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.deleted-meta {
  font-size: 19px;
  color: var(--text-secondary);
}
.foot-spacer {
  flex: 1;
}
.delete-btn {
  color: var(--color-danger);
}
.confirm-text {
  margin-right: auto;
  color: var(--color-danger);
  align-self: center;
}
</style>
