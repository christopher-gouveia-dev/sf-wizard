<template>
  <div class="card overflow-hidden">
    <div class="border-b border-slate-200 px-3 py-2 text-sm font-medium">Logs</div>
    <div class="p-3 font-mono text-xs whitespace-pre-wrap text-slate-700 max-h-[320px] overflow-auto">
      <div v-if="!lines.length" class="text-slate-500">No logs yet.</div>
      <div v-else>
        <div v-for="(l, idx) in lines" :key="idx">{{ l }}</div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
defineProps<{ lines: string[] }>()
</script>
