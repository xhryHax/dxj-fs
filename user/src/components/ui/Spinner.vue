<script setup>
defineProps({
  size: { type: Number, default: 24 },
  color: { type: String, default: 'var(--text-primary)' },
})
</script>

<template>
  <span
    class="spinner"
    :style="{ width: `${size}px`, height: `${size}px`, borderColor: `${color}33`, borderTopColor: color }"
    role="status"
    aria-label="加载中"
  />
</template>

<style scoped>
.spinner {
  display: inline-block;
  border-radius: 50%;
  border-width: 2.5px;
  border-style: solid;
  animation: spin 0.7s linear infinite;
}
@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}
</style>
