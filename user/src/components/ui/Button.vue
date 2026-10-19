<script setup>
defineProps({
  variant: { type: String, default: 'primary' }, // primary | ghost | cream | pill | danger
  size: { type: String, default: 'md' }, // sm | md | lg
  loading: { type: Boolean, default: false },
  disabled: { type: Boolean, default: false },
  type: { type: String, default: 'button' },
  block: { type: Boolean, default: false },
})
</script>

<template>
  <button
    :type="type"
    class="btn"
    :class="[`btn--${variant}`, `btn--${size}`, { 'btn--block': block, 'btn--loading': loading }]"
    :disabled="disabled || loading"
  >
    <span v-if="loading" class="btn-spinner" aria-hidden="true" />
    <slot />
  </button>
</template>

<style scoped>
.btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  border-radius: var(--radius-sm);
  font-weight: 600;
  cursor: pointer;
  border: none;
  transition: opacity 0.15s ease, box-shadow 0.15s ease;
  user-select: none;
  white-space: nowrap;
}
.btn:disabled {
  cursor: not-allowed;
  opacity: 0.5;
}
.btn:not(:disabled):active {
  opacity: 0.8;
}
.btn--sm {
  padding: 4px 10px;
  font-size: 19px;
}
.btn--md {
  padding: 8px 16px;
  font-size: 19px;
}
.btn--lg {
  padding: 12px 20px;
  font-size: 19px;
}
.btn--block {
  display: flex;
  width: 100%;
}
.btn--primary {
  background: var(--text-primary);
  color: var(--text-on-dark);
  box-shadow: var(--btn-inset);
}
.btn--primary:not(:disabled):hover {
  box-shadow: var(--btn-inset), var(--shadow-focus);
}
.btn--ghost {
  background: transparent;
  color: var(--text-primary);
  border: 1px solid var(--border-interactive);
}
.btn--ghost:not(:disabled):hover {
  box-shadow: var(--shadow-focus);
}
.btn--cream {
  background: var(--bg-cream);
  color: var(--text-primary);
  border: 1px solid var(--border-passive);
}
.btn--cream:not(:disabled):hover {
  box-shadow: var(--shadow-focus);
}
.btn--pill {
  background: transparent;
  color: var(--text-primary);
  border-radius: var(--radius-full);
  border: 1px solid var(--border-interactive);
}
.btn--pill:not(:disabled):hover {
  box-shadow: var(--shadow-focus);
}
.btn--danger {
  background: var(--color-danger);
  color: var(--text-on-dark);
  box-shadow: var(--btn-inset);
}
.btn--danger:not(:disabled):hover {
  box-shadow: var(--btn-inset), var(--shadow-focus);
}
.btn-spinner {
  width: 14px;
  height: 14px;
  border: 2px solid currentColor;
  border-top-color: transparent;
  border-radius: 50%;
  animation: btn-spin 0.7s linear infinite;
}
@keyframes btn-spin {
  to {
    transform: rotate(360deg);
  }
}
</style>
