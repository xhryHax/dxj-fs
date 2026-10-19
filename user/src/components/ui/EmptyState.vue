<script setup>
defineProps({
  message: { type: String, default: '暂无数据' },
  hint: { type: String, default: '' },
})
</script>

<template>
  <div class="empty">
    <div class="empty-icon" aria-hidden="true">◇</div>
    <p class="empty-msg">{{ message }}</p>
    <p v-if="hint" class="empty-hint">{{ hint }}</p>
  </div>
</template>

<style scoped>
.empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 48px 16px;
  text-align: center;
}
.empty-icon {
  font-size: 28px;
  color: var(--border-interactive);
  margin-bottom: 8px;
}
.empty-msg {
  margin: 0 0 4px;
  font-weight: 600;
  color: var(--text-primary);
}
.empty-hint {
  margin: 0;
  font-size: 19px;
  color: var(--text-secondary);
}
</style>
