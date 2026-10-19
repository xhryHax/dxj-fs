<script setup>
import { computed } from 'vue'
import { formatBytes, percent } from '../../utils/format'

const props = defineProps({
  groupName: { type: String, default: '' },
  members: { type: Array, default: () => [] },
  storage: { type: Object, default: null }, // { size, occupied }
})

const quotaText = computed(() => {
  if (!props.storage) return '加载中…'
  const unlimited = props.storage.size === -1
  return unlimited
    ? `已使用 ${formatBytes(props.storage.occupied)}（不限量）`
    : `${formatBytes(props.storage.occupied)} / ${formatBytes(props.storage.size)}`
})

const usedPercent = computed(() => percent(props.storage?.occupied, props.storage?.size))
</script>

<template>
  <aside class="sidebar">
    <div class="sidebar-block">
      <h4 class="sidebar-title">组信息</h4>
      <p class="group-name">{{ groupName || '—' }}</p>
    </div>

    <div class="sidebar-block">
      <div class="storage-head">
        <h4 class="sidebar-title">云存储</h4>
      </div>
      <div class="storage-bar">
        <div class="storage-fill" :style="{ width: `${usedPercent}%` }" />
      </div>
      <p class="storage-text">{{ quotaText }}</p>
    </div>

    <div class="sidebar-block sidebar-members">
      <h4 class="sidebar-title">成员（{{ members.length }}）</h4>
      <ul class="member-list">
        <li v-for="m in members" :key="m.userId" class="member-item">
          <span class="member-dot" aria-hidden="true" />
          <div class="member-info">
            <span class="member-name">{{ m.userName || '未命名' }}</span>
            <span class="member-email">{{ m.email }}</span>
          </div>
        </li>
      </ul>
    </div>
  </aside>
</template>

<style scoped>
.sidebar {
  display: flex;
  flex-direction: column;
  gap: 20px;
  background: var(--bg-cream);
  border: 1px solid var(--border-passive);
  border-radius: var(--radius-md);
  padding: 20px;
  min-width: 220px;
}
.sidebar-title {
  font-size: 19px;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: var(--text-secondary);
  margin-bottom: 8px;
}
.group-name {
  font-weight: 600;
  margin: 0;
}
.storage-bar {
  height: 8px;
  background: rgba(28, 28, 28, 0.08);
  border-radius: var(--radius-full);
  overflow: hidden;
}
.storage-fill {
  height: 100%;
  background: var(--text-primary);
  border-radius: var(--radius-full);
  transition: width 0.4s ease;
}
.storage-text {
  font-size: 19px;
  color: var(--text-secondary);
  margin: 6px 0 0;
}
.sidebar-members {
  flex: 1;
  overflow-y: auto;
  max-height: 420px;
}
.member-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.member-item {
  display: flex;
  align-items: center;
  gap: 10px;
}
.member-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--color-success);
  flex-shrink: 0;
}
.member-info {
  display: flex;
  flex-direction: column;
  min-width: 0;
}
.member-name {
  font-size: 19px;
  font-weight: 600;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.member-email {
  font-size: 19px;
  color: var(--text-secondary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
</style>
