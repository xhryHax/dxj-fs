<script setup>
defineProps({
  modelValue: { type: Boolean, default: false },
  label: { type: String, default: '' },
  disabled: { type: Boolean, default: false },
})
defineEmits(['update:modelValue'])
</script>

<template>
  <label class="check" :class="{ 'check--disabled': disabled }">
    <input
      type="checkbox"
      class="check-input"
      :checked="modelValue"
      :disabled="disabled"
      @change="$emit('update:modelValue', $event.target.checked)"
    />
    <span v-if="label" class="check-label">{{ label }}</span>
  </label>
</template>

<style scoped>
.check {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
}
.check--disabled {
  cursor: not-allowed;
  opacity: 0.5;
}
.check-input {
  width: 16px;
  height: 16px;
  accent-color: var(--text-primary);
  cursor: pointer;
}
.check-label {
  font-size: 19px;
}
</style>
