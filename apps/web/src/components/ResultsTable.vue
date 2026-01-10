<template>
  <div class="card overflow-hidden">
    <div class="border-b border-slate-200 px-3 py-2 text-sm flex items-center justify-between">
      <div class="font-medium">Results</div>
      <button class="btn" :disabled="!rows.length" @click="copyExcel">Copy Excel</button>
    </div>

    <div v-if="!rows.length" class="p-4 text-sm text-slate-500">
      No rows yet.
    </div>

    <div v-else class="overflow-auto">
      <table class="min-w-full text-sm">
        <thead class="bg-slate-50 border-b border-slate-200">
          <tr>
            <th v-for="h in headers" :key="h" class="text-left px-3 py-2 font-medium">{{ h }}</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="(r, idx) in rows" :key="idx" class="border-b border-slate-100">
            <td v-for="h in headers" :key="h" class="px-3 py-2 align-top whitespace-nowrap">
              {{ formatCell(r[h]) }}
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{ rows: any[] }>()

const headers = computed(() => {
  if (!props.rows.length) return []
  const first = props.rows[0]
  // Keep stable order: Id first if present, then alphabetical
  const keys = Object.keys(first || {})
  const idIdx = keys.indexOf('Id')
  if (idIdx >= 0) {
    keys.splice(idIdx, 1)
    return ['Id', ...keys.sort()]
  }
  return keys.sort()
})

function formatCell(v: any) {
  if (v === null || v === undefined) return ''
  if (typeof v === 'object') return JSON.stringify(v)
  return String(v)
}

async function copyExcel() {
  const hs = headers.value
  const lines = [
    hs.join('\t'),
    ...props.rows.map(r => hs.map(h => formatCell(r[h]).replace(/\t/g, ' ')).join('\t'))
  ]
  const tsv = lines.join('\n')
  await navigator.clipboard.writeText(tsv)
}
</script>
