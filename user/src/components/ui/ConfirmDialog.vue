<script setup>
import Modal from './Modal.vue'
import Button from './Button.vue'

defineProps({
  open: { type: Boolean, default: false },
  title: { type: String, default: '确认操作' },
  message: { type: String, default: '' },
  confirmText: { type: String, default: '确认' },
  cancelText: { type: String, default: '取消' },
  danger: { type: Boolean, default: false },
  loading: { type: Boolean, default: false },
})
const emit = defineEmits(['confirm', 'cancel'])
</script>

<template>
  <Modal :open="open" :title="title" width="420px" @close="emit('cancel')">
    <p class="confirm-msg">{{ message }}</p>
    <template #footer>
      <Button variant="ghost" :disabled="loading" @click="emit('cancel')">{{ cancelText }}</Button>
      <Button :variant="danger ? 'danger' : 'primary'" :loading="loading" @click="emit('confirm')">
        {{ confirmText }}
      </Button>
    </template>
  </Modal>
</template>

<style scoped>
.confirm-msg {
  margin: 0;
  line-height: 1.7;
}
</style>
