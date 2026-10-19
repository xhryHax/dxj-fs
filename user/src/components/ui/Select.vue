<script setup>
import { computed } from 'vue'

const props = defineProps({
  modelValue: { type: [String, Number], default: '' },
  options: { type: Array, default: () => [] }, // [{value, label}] 或字符串数组
  label: { type: String, default: '' },
  placeholder: { type: String, default: '请选择' },
  disabled: { type: Boolean, default: false },
})
defineEmits(['update:modelValue'])

const normalized = computed(() =>
  props.options.map((o) =>
    typeof o === 'object' ? o : { value: o, label: String(o) },
  ),
)
</script>

<template>
  <label class="field">
    <span v-if="label" class="field-label">{{ label }}</span>
    <select
      class="field-select"
      :value="modelValue"
      :disabled="disabled"
      @change="$emit('update:modelValue', $event.target.value)"
    >
      <option value="" disabled>{{ placeholder }}</option>
      <option v-for="opt in normalized" :key="opt.value" :value="opt.value">
        {{ opt.label }}
      </option>
    </select>
  </label>
</template>

<style scoped>
.field {
  display: flex;
  flex-direction: column;
  gap: 6px;
  width: 100%;
}
.field-label {
  font-size: 19px;
  font-weight: 600;
}
.field-select {
  width: 100%;
  padding: 9px 12px;
  background: var(--bg-cream);
  border: 1px solid var(--border-passive);
  border-radius: var(--radius-sm);
  font-size: 19px;
  cursor: pointer;
  appearance: none;
  background-image: linear-gradient(45deg, transparent 50%, var(--text-primary) 50%),
    linear-gradient(135deg, var(--text-primary) 50%, transparent 50%);
  background-position:
    calc(100% - 18px) 55%,
    calc(100% - 13px) 55%;
  background-size: 5px 5px;
  background-repeat: no-repeat;
  padding-right: 32px;
}
.field-select:disabled {
  cursor: not-allowed;
  opacity: 0.5;
}
.field-select:focus {
  outline: none;
  border-color: var(--color-accent);
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.5);
}
</style>
