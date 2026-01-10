<template>
  <span class="inline-flex items-center gap-2 rounded-full border border-slate-200 bg-slate-50 px-3 py-1 text-xs">
    <span>🔌</span>
    <span v-if="alias">{{ alias }}</span>
    <span v-else class="text-slate-500">No org</span>
  </span>
</template>

<script setup lang="ts">
defineProps<{ alias: string | null }>()
</script>
