<script setup>
defineProps({
  modelValue: { type: String, default: '' },
  label: { type: String, default: '' },
  type: { type: String, default: 'text' },
  placeholder: { type: String, default: '' },
  required: { type: Boolean, default: false },
  autocomplete: { type: String, default: 'off' },
})
defineEmits(['update:modelValue'])
</script>

<template>
  <label class="field">
    <span v-if="label" class="field-label">
      {{ label }}<span v-if="required" class="req">*</span>
    </span>
    <input
      class="field-input"
      :type="type"
      :value="modelValue"
      :placeholder="placeholder"
      :autocomplete="autocomplete"
      @input="$emit('update:modelValue', $event.target.value)"
    />
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
  color: var(--text-primary);
}
.req {
  color: var(--color-danger);
  margin-left: 2px;
}
.field-input {
  width: 100%;
  padding: 9px 12px;
  background: var(--bg-cream);
  border: 1px solid var(--border-passive);
  border-radius: var(--radius-sm);
  font-size: 19px;
  transition: border-color 0.15s ease, box-shadow 0.15s ease;
}
.field-input::placeholder {
  color: var(--text-secondary);
}
.field-input:focus {
  outline: none;
  border-color: var(--color-accent);
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.5);
}
</style>
