<script setup>
import { formatBytes, formatDateTime } from '../../utils/format'
import EmptyState from '../ui/EmptyState.vue'

defineProps({
  files: { type: Array, default: () => [] },
})
const emit = defineEmits(['download'])
</script>

<template>
  <div class="file-list">
    <table class="list-table">
      <thead>
        <tr>
          <th>文件名</th>
          <th>大小</th>
          <th>上传者</th>
          <th>创建时间</th>
          <th class="col-actions">操作</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="f in files" :key="f.fileId">
          <td class="col-name" :title="f.fileName">{{ f.fileName }}</td>
          <td>{{ formatBytes(f.size) }}</td>
          <td>{{ f.uploader }}</td>
          <td>{{ formatDateTime(f.atCreated) }}</td>
          <td class="col-actions">
            <button class="row-btn" title="下载" @click="emit('download', f)">↓</button>
          </td>
        </tr>
      </tbody>
    </table>
    <EmptyState v-if="!files.length" message="该页面暂无文件" hint="由组管理员添加文件后展示" />
  </div>
</template>

<style scoped>
.file-list {
  overflow-x: auto;
}
.list-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 19px;
  min-width: 560px;
}
.list-table th,
.list-table td {
  text-align: left;
  padding: 10px 12px;
  border-bottom: 1px solid var(--border-passive);
}
.list-table th {
  font-size: 19px;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--text-secondary);
  font-weight: 600;
  white-space: nowrap;
}
.list-table tbody tr:hover {
  background: rgba(28, 28, 28, 0.03);
}
.list-table tbody tr:last-child td {
  border-bottom: none;
}
.col-name {
  max-width: 280px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-weight: 600;
}
.col-actions {
  text-align: right;
  white-space: nowrap;
}
.row-btn {
  width: 28px;
  height: 28px;
  border: 1px solid var(--border-passive);
  background: transparent;
  border-radius: var(--radius-full);
  cursor: pointer;
  font-size: 19px;
  line-height: 1;
}
.row-btn:hover {
  box-shadow: var(--shadow-focus);
}
</style>
