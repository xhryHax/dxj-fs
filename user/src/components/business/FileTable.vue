<script setup>
import { computed } from 'vue'
import { formatBytes, formatDateTime } from '../../utils/format'
import Tag from '../ui/Tag.vue'
import EmptyState from '../ui/EmptyState.vue'

const props = defineProps({
  files: { type: Array, default: () => [] },
  selected: { type: Array, default: () => [] }, // selected fileIds
})
const emit = defineEmits(['select', 'toggleAll', 'rename', 'download', 'remove'])

const allChecked = computed(
  () => props.files.length > 0 && props.selected.length === props.files.length,
)
const someChecked = computed(
  () => props.selected.length > 0 && props.selected.length < props.files.length,
)

function onToggleAll(checked) {
  emit('toggleAll', checked)
}

function onToggle(id) {
  const next = props.selected.includes(id)
    ? props.selected.filter((x) => x !== id)
    : [...props.selected, id]
  emit('select', next)
}
</script>

<template>
  <div class="table-wrap">
    <table class="file-table">
      <thead>
        <tr>
          <th class="col-check">
            <input
              type="checkbox"
              :checked="allChecked"
              :indeterminate="someChecked"
              @change="onToggleAll($event.target.checked)"
            />
          </th>
          <th>文件名</th>
          <th>标签</th>
          <th>大小</th>
          <th>上传者</th>
          <th>创建时间</th>
          <th class="col-actions">操作</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="f in files" :key="f.fileId">
          <td class="col-check">
            <input
              type="checkbox"
              :checked="selected.includes(f.fileId)"
              @change="onToggle(f.fileId)"
            />
          </td>
          <td class="col-name" :title="f.fileName">{{ f.fileName }}</td>
          <td><Tag>{{ f.label || '未分类' }}</Tag></td>
          <td>{{ formatBytes(f.size) }}</td>
          <td>{{ f.uploader }}</td>
          <td>{{ formatDateTime(f.atCreated) }}</td>
          <td class="col-actions">
            <button class="row-btn" title="下载" @click="emit('download', f)">↓</button>
            <button class="row-btn" title="重命名" @click="emit('rename', f)">✎</button>
            <button class="row-btn row-btn--danger" title="删除" @click="emit('remove', f)">✕</button>
          </td>
        </tr>
      </tbody>
    </table>

    <EmptyState v-if="!files.length" message="暂无文件" hint="点击右上角「上传文件」开始添加" />
  </div>
</template>

<style scoped>
.table-wrap {
  background: var(--bg-cream);
  border: 1px solid var(--border-passive);
  border-radius: var(--radius-md);
  overflow: hidden;
}
.file-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 19px;
  min-width: 640px;
}
.file-table th,
.file-table td {
  text-align: left;
  padding: 10px 12px;
  border-bottom: 1px solid var(--border-passive);
  vertical-align: middle;
}
.file-table th {
  font-size: 19px;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--text-secondary);
  font-weight: 600;
  white-space: nowrap;
}
.file-table tbody tr:hover {
  background: rgba(28, 28, 28, 0.03);
}
.file-table tbody tr:last-child td {
  border-bottom: none;
}
.col-check {
  width: 40px;
}
.col-name {
  max-width: 260px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-weight: 600;
}
.col-actions {
  white-space: nowrap;
  text-align: right;
}
.row-btn {
  width: 28px;
  height: 28px;
  border: 1px solid var(--border-passive);
  background: transparent;
  border-radius: var(--radius-full);
  cursor: pointer;
  margin-left: 4px;
  font-size: 19px;
  line-height: 1;
  transition: box-shadow 0.15s ease, opacity 0.15s ease;
}
.row-btn:hover {
  box-shadow: var(--shadow-focus);
}
.row-btn:active {
  opacity: 0.8;
}
.row-btn--danger {
  color: var(--color-danger);
}
</style>
