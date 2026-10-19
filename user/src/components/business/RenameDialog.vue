<script setup>
import { reactive, ref, watch } from 'vue'
import * as fileLogicApi from '../../api/fileLogic'
import { toast } from '../../stores/toast'
import Modal from '../ui/Modal.vue'
import Button from '../ui/Button.vue'

const props = defineProps({
  groupId: { type: [String, Number], default: null },
  open: { type: Boolean, default: false },
  files: { type: Array, default: () => [] }, // 待重命名的文件
})
const emit = defineEmits(['close', 'renamed'])

const names = reactive({})
const loading = ref(false)

watch(
  () => props.open,
  (v) => {
    if (v) {
      for (const f of props.files) names[f.fileId] = f.fileName
    }
  },
)

async function submit() {
  if (!props.groupId) return
  loading.value = true
  try {
    for (const f of props.files) {
      const value = (names[f.fileId] || '').trim()
      if (!value) {
        toast(`「${f.fileName}」的新名称不能为空`, 'warning')
        continue
      }
      await fileLogicApi.renameFile(props.groupId, f.fileId, value)
    }
    toast('重命名完成', 'success')
    emit('renamed')
    emit('close')
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <Modal :open="open" title="重命名文件" width="520px" @close="emit('close')">
    <p class="hint">正在重命名 {{ files.length }} 个文件，请为每个文件填写新名称。</p>
    <div class="rename-fields">
      <label v-for="f in files" :key="f.fileId" class="rename-row">
        <span class="rename-old">{{ f.fileName }}</span>
        <input v-model="names[f.fileId]" class="rename-input" />
      </label>
    </div>
    <template #footer>
      <Button variant="ghost" :disabled="loading" @click="emit('close')">取消</Button>
      <Button :loading="loading" @click="submit">保存</Button>
    </template>
  </Modal>
</template>

<style scoped>
.hint {
  color: var(--text-secondary);
  font-size: 19px;
  margin-bottom: 16px;
}
.rename-fields {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.rename-row {
  display: grid;
  grid-template-columns: 1fr 1.4fr;
  gap: 12px;
  align-items: center;
}
.rename-old {
  font-size: 19px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  color: var(--text-secondary);
}
.rename-input {
  width: 100%;
  padding: 7px 10px;
  background: var(--bg-cream);
  border: 1px solid var(--border-passive);
  border-radius: var(--radius-sm);
  font-size: 19px;
}
.rename-input:focus {
  outline: none;
  border-color: var(--color-accent);
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.5);
}
</style>
