<script setup>
defineProps({
  tone: { type: String, default: 'neutral' }, // neutral | success | danger | accent | warning
  size: { type: String, default: 'sm' }, // sm | md
})
</script>

<template>
  <span class="tag" :class="[`tag--${tone}`, `tag--${size}`]">
    <slot />
  </span>
</template>

<style scoped>
.tag {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  border-radius: var(--radius-full);
  font-weight: 600;
  white-space: nowrap;
}
.tag--sm {
  padding: 1px 8px;
  font-size: 19px;
}
.tag--md {
  padding: 3px 10px;
  font-size: 19px;
}
.tag--neutral {
  background: rgba(28, 28, 28, 0.06);
  color: var(--text-primary);
}
.tag--success {
  background: rgba(74, 124, 89, 0.14);
  color: var(--color-success);
}
.tag--danger {
  background: rgba(179, 65, 61, 0.14);
  color: var(--color-danger);
}
.tag--accent {
  background: rgba(59, 130, 246, 0.14);
  color: var(--color-accent);
}
.tag--warning {
  background: rgba(176, 118, 30, 0.14);
  color: var(--color-warning);
}
</style>
