<script setup>
import { toastState } from '../../stores/toast'
</script>

<template>
  <Teleport to="body">
    <div class="toast-wrap" aria-live="polite">
      <TransitionGroup name="toast">
        <div
          v-for="t in toastState.list"
          :key="t.id"
          class="toast"
          :class="`toast--${t.type}`"
        >
          {{ t.message }}
        </div>
      </TransitionGroup>
    </div>
  </Teleport>
</template>

<style scoped>
.toast-wrap {
  position: fixed;
  top: 16px;
  left: 50%;
  transform: translateX(-50%);
  z-index: 2000;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  pointer-events: none;
  width: min(92vw, 420px);
}
.toast {
  width: 100%;
  padding: 10px 16px;
  background: var(--text-primary);
  color: var(--text-on-dark);
  border-radius: var(--radius-sm);
  font-size: 19px;
  box-shadow: var(--shadow-focus);
  text-align: center;
}
.toast--success {
  background: var(--color-success);
}
.toast--error {
  background: var(--color-danger);
}
.toast--info {
  background: var(--color-accent);
}
.toast--warning {
  background: var(--color-warning);
}
.toast-enter-active,
.toast-leave-active {
  transition: all 0.25s ease;
}
.toast-enter-from,
.toast-leave-to {
  opacity: 0;
  transform: translateY(-8px);
}
</style>
