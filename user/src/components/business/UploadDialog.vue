<script setup>
import { ref } from 'vue'
import { UPLOAD_CHUNK_SIZE } from '../../constants'
import * as fileIoApi from '../../api/fileIo'
import { toast } from '../../stores/toast'
import Modal from '../ui/Modal.vue'
import Button from '../ui/Button.vue'
import Input from '../ui/Input.vue'

const props = defineProps({
  groupId: { type: [String, Number], default: null },
  open: { type: Boolean, default: false },
})
const emit = defineEmits(['close', 'uploaded'])

const file = ref(null)
const label = ref('')
const progress = ref(0)
const uploading = ref(false)

function onPick(event) {
  file.value = event.target.files[0] || null
  progress.value = 0
}

async function startUpload() {
  if (!props.groupId) return
  if (!file.value) {
    toast('请先选择要上传的文件', 'warning')
    return
  }
  uploading.value = true
  progress.value = 0
  try {
    const gid = props.groupId
    const f = file.value

    // 尝试复用服务端未完成的上传记录（断点续传）
    let info = null
    const existing = await fileIoApi.getUploadInfos(gid).catch(() => [])
    const match = existing.find(
      (e) => e.fileName === f.name && e.size === f.size && (e.progress ?? 0) < e.size,
    )
    info = match
      ? match
      : await fileIoApi.prepareUpload(gid, {
          size: f.size,
          fileName: f.name,
          label: label.value,
        })

    let uploaded = Math.min(info.progress ?? 0, info.size)
    while (uploaded < f.size) {
      const end = Math.min(uploaded + UPLOAD_CHUNK_SIZE, f.size)
      const chunk = f.slice(uploaded, end)
      await fileIoApi.uploadChunk(gid, info.uploadInfoId, chunk, uploaded, end - 1, f.size)
      uploaded = end
      progress.value = Math.round((uploaded / f.size) * 100)
    }

    const done = await fileIoApi.completeUpload(gid, info.uploadInfoId)
    toast('上传完成', 'success')
    emit('uploaded', done)
    emit('close')
  } catch {
    /* 错误提示已由请求层统一处理，上传进度保留以支持重试 */
  } finally {
    uploading.value = false
    progress.value = 0
  }
}
</script>

<template>
  <Modal :open="open" title="上传文件" width="480px" @close="emit('close')">
    <div class="upload-body">
      <label class="pick-zone">
        <input type="file" class="pick-input" @change="onPick" />
        <template v-if="file">
          <span class="pick-name">{{ file.name }}</span>
          <span class="pick-size">{{ (file.size / 1024).toFixed(1) }} KB</span>
        </template>
        <template v-else>
          <span class="pick-hint">点击选择要上传的文件</span>
        </template>
      </label>

      <Input v-model="label" label="文件标签（可选）" placeholder="例如：成果展示、期中报告" />

      <div v-if="uploading" class="progress">
        <div class="progress-bar">
          <div class="progress-fill" :style="{ width: `${progress}%` }" />
        </div>
        <span class="progress-text">{{ progress }}%</span>
      </div>
    </div>

    <template #footer>
      <Button variant="ghost" :disabled="uploading" @click="emit('close')">取消</Button>
      <Button :loading="uploading" @click="startUpload">
        {{ uploading ? '上传中…' : '开始上传' }}
      </Button>
    </template>
  </Modal>
</template>

<style scoped>
.upload-body {
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.pick-zone {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 6px;
  padding: 32px 16px;
  border: 1px dashed var(--border-interactive);
  border-radius: var(--radius-sm);
  cursor: pointer;
  text-align: center;
}
.pick-zone:hover {
  box-shadow: var(--shadow-focus);
}
.pick-input {
  display: none;
}
.pick-name {
  font-weight: 600;
  word-break: break-all;
}
.pick-size {
  font-size: 19px;
  color: var(--text-secondary);
}
.pick-hint {
  font-size: 19px;
  color: var(--text-secondary);
}
.progress {
  display: flex;
  align-items: center;
  gap: 10px;
}
.progress-bar {
  flex: 1;
  height: 8px;
  background: rgba(28, 28, 28, 0.08);
  border-radius: var(--radius-full);
  overflow: hidden;
}
.progress-fill {
  height: 100%;
  background: var(--color-accent);
  border-radius: var(--radius-full);
  transition: width 0.2s ease;
}
.progress-text {
  font-size: 19px;
  font-weight: 600;
  min-width: 42px;
  text-align: right;
}
</style>
