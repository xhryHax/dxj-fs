<script setup>
defineProps({
  filters: { type: Object, required: true }, // { label, uploader, sortBy, sortDir }
  labels: { type: Array, default: () => [] },
  uploaders: { type: Array, default: () => [] },
})
const emit = defineEmits(['update'])
</script>

<template>
  <div class="filter-bar">
    <select
      class="filter-select"
      :value="filters.label"
      @change="emit('update', { ...filters, label: $event.target.value })"
    >
      <option value="">全部标签</option>
      <option v-for="l in labels" :key="l" :value="l">{{ l }}</option>
    </select>

    <select
      class="filter-select"
      :value="filters.uploader"
      @change="emit('update', { ...filters, uploader: $event.target.value })"
    >
      <option value="">全部上传者</option>
      <option v-for="u in uploaders" :key="u" :value="u">{{ u }}</option>
    </select>

    <select
      class="filter-select"
      :value="filters.sortBy"
      @change="emit('update', { ...filters, sortBy: $event.target.value })"
    >
      <option value="atCreated">按创建时间排序</option>
      <option value="size">按大小排序</option>
    </select>

    <select
      class="filter-select"
      :value="filters.sortDir"
      @change="emit('update', { ...filters, sortDir: $event.target.value })"
    >
      <option value="desc">降序</option>
      <option value="asc">升序</option>
    </select>

    <button
      class="filter-reset"
      @click="emit('update', { label: '', uploader: '', sortBy: 'atCreated', sortDir: 'desc' })"
    >
      重置
    </button>
  </div>
</template>

<style scoped>
.filter-bar {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
  align-items: center;
}
.filter-select {
  padding: 7px 10px;
  background: var(--bg-cream);
  border: 1px solid var(--border-passive);
  border-radius: var(--radius-sm);
  font-size: 19px;
  cursor: pointer;
}
.filter-reset {
  padding: 7px 12px;
  background: transparent;
  border: 1px solid var(--border-interactive);
  border-radius: var(--radius-sm);
  font-size: 19px;
  font-weight: 600;
  cursor: pointer;
}
.filter-reset:hover {
  box-shadow: var(--shadow-focus);
}
</style>
