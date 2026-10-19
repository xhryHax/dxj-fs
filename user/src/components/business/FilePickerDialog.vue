<script setup>
import { computed, ref, watch } from 'vue'
import * as fileLogicApi from '../../api/fileLogic'
import Modal from '../ui/Modal.vue'
import Button from '../ui/Button.vue'
import Spinner from '../ui/Spinner.vue'
import EmptyState from '../ui/EmptyState.vue'

const props = defineProps({
  groupId: { type: [String, Number], default: null },
  open: { type: Boolean, default: false },
  title: { type: String, default: '选择文件' },
  excludeIds: { type: Array, default: () => [] }, // 需要排除的文件（已存在于目标页面）
  files: { type: Array, default: null }, // 若提供则直接使用该文件源（移除场景）
})
const emit = defineEmits(['close', 'confirm'])

const files = ref([])
const selected = ref([])
const keyword = ref('')
const loading = ref(false)

async function load() {
  if (props.files) {
    files.value = props.files.filter((f) => !props.excludeIds.includes(f.fileId))
    selected.value = []
    return
  }
  loading.value = true
  try {
    const res = await fileLogicApi.getGroupFiles(props.groupId, 0, 5000)
    files.value = (res.info || []).filter((f) => !props.excludeIds.includes(f.fileId))
    selected.value = []
  } finally {
    loading.value = false
  }
}

watch(
  () => props.open,
  (v) => {
    if (v) {
      keyword.value = ''
      load().catch(() => {})
    }
  },
)

const filtered = computed(() => {
  const kw = keyword.value.trim().toLowerCase()
  if (!kw) return files.value
  return files.value.filter((f) => f.fileName.toLowerCase().includes(kw))
})

function toggle(id) {
  selected.value = selected.value.includes(id)
    ? selected.value.filter((x) => x !== id)
    : [...selected.value, id]
}

function confirm() {
  emit('confirm', selected.value)
  emit('close')
}
</script>

<template>
  <Modal :open="open" :title="title" width="640px" @close="emit('close')">
    <input v-model="keyword" class="search-input" placeholder="搜索文件名…" />
    <div class="picker-body">
      <Spinner v-if="loading" class="picker-loading" :size="24" />
      <EmptyState
        v-else-if="!files.length"
        message="组空间暂无可用文件"
        hint="请先在组空间中上传文件"
      />
      <ul v-else class="picker-list">
        <li v-for="f in filtered" :key="f.fileId" class="picker-item">
          <input
            type="checkbox"
            class="picker-check"
            :checked="selected.includes(f.fileId)"
            @change="toggle(f.fileId)"
          />
          <span class="picker-name">{{ f.fileName }}</span>
          <span class="picker-meta">{{ f.label || '未分类' }}</span>
        </li>
        <li v-if="!filtered.length" class="picker-none">没有匹配的文件</li>
      </ul>
    </div>
    <template #footer>
      <Button variant="ghost" @click="emit('close')">取消</Button>
      <Button :disabled="!selected.length" @click="confirm">
        添加选中（{{ selected.length }}）
      </Button>
    </template>
  </Modal>
</template>

<style scoped>
.search-input {
  width: 100%;
  padding: 8px 12px;
  background: var(--bg-cream);
  border: 1px solid var(--border-passive);
  border-radius: var(--radius-sm);
  font-size: 19px;
  margin-bottom: 14px;
}
.search-input:focus {
  outline: none;
  border-color: var(--color-accent);
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.5);
}
.picker-body {
  max-height: 320px;
  overflow-y: auto;
  min-height: 120px;
}
.picker-loading {
  display: block;
  margin: 32px auto;
}
.picker-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.picker-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 10px;
  border: 1px solid var(--border-passive);
  border-radius: var(--radius-sm);
}
.picker-item:hover {
  box-shadow: var(--shadow-focus);
}
.picker-check {
  width: 15px;
  height: 15px;
  accent-color: var(--text-primary);
  cursor: pointer;
}
.picker-name {
  flex: 1;
  font-size: 19px;
  font-weight: 600;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.picker-meta {
  font-size: 19px;
  color: var(--text-secondary);
  flex-shrink: 0;
}
.picker-none {
  padding: 16px;
  text-align: center;
  color: var(--text-secondary);
  font-size: 19px;
}
</style>
