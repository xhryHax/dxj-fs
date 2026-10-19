<script setup>
defineProps({
  padded: { type: Boolean, default: true },
  radius: { type: String, default: 'md' }, // md | lg | sm
})
</script>

<template>
  <div class="card" :class="[`card--${radius}`, { 'card--bare': !padded }]">
    <slot />
  </div>
</template>

<style scoped>
.card {
  background: var(--bg-cream);
  border: 1px solid var(--border-passive);
}
.card--md {
  border-radius: var(--radius-md);
}
.card--lg {
  border-radius: var(--radius-lg);
}
.card--sm {
  border-radius: var(--radius-sm);
}
.card--bare {
  padding: 0;
}
.card:not(.card--bare) {
  padding: 20px;
}
</style>
