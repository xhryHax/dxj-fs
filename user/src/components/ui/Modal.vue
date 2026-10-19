<script setup>
defineProps({
  open: { type: Boolean, default: false },
  title: { type: String, default: '' },
  width: { type: String, default: '560px' },
})
defineEmits(['close'])
</script>

<template>
  <Teleport to="body">
    <Transition name="modal">
      <div v-if="open" class="modal-mask" @click.self="$emit('close')">
        <div class="modal-panel" :style="{ maxWidth: width }" role="dialog" aria-modal="true">
          <header class="modal-head">
            <h3 class="modal-title">{{ title }}</h3>
            <button class="modal-close" aria-label="关闭" @click="$emit('close')">✕</button>
          </header>
          <div class="modal-body">
            <slot />
          </div>
          <footer v-if="$slots.footer" class="modal-foot">
            <slot name="footer" />
          </footer>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
.modal-mask {
  position: fixed;
  inset: 0;
  z-index: 1000;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 16px;
  background: rgba(28, 28, 28, 0.4);
}
.modal-panel {
  width: 100%;
  background: var(--bg-offwhite);
  border: 1px solid var(--border-passive);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-focus);
  max-height: 86vh;
  display: flex;
  flex-direction: column;
}
.modal-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 20px;
  border-bottom: 1px solid var(--border-passive);
}
.modal-title {
  font-size: 19px;
  margin: 0;
}
.modal-close {
  background: transparent;
  border: none;
  font-size: 19px;
  color: var(--text-secondary);
  cursor: pointer;
  padding: 4px;
  border-radius: var(--radius-full);
  line-height: 1;
}
.modal-close:hover {
  background: rgba(28, 28, 28, 0.05);
}
.modal-body {
  padding: 20px;
  overflow-y: auto;
}
.modal-foot {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  padding: 14px 20px;
  border-top: 1px solid var(--border-passive);
}
.modal-enter-active,
.modal-leave-active {
  transition: opacity 0.2s ease;
}
.modal-enter-from,
.modal-leave-to {
  opacity: 0;
}
.modal-enter-active .modal-panel,
.modal-leave-active .modal-panel {
  transition: transform 0.2s ease;
}
.modal-enter-from .modal-panel,
.modal-leave-to .modal-panel {
  transform: translateY(8px) scale(0.98);
}
</style>
