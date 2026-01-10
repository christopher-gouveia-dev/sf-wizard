<template>
  <div class="space-y-4">
    <div class="flex items-start justify-between gap-4">
      <div>
        <h1 class="text-2xl font-semibold">SOQL Query</h1>
        <p class="text-sm text-slate-600">
          Runs queries through SF CLI (<span class="font-mono">sf data query</span>).
        </p>
      </div>
      <div class="text-right text-sm text-slate-600">
        <div v-if="activeAlias">Active org: <span class="font-mono">{{ activeAlias }}</span></div>
        <div v-else class="text-amber-700">Select an org in the header to run queries.</div>
      </div>
    </div>

    <div class="card p-4 space-y-3">
      <label class="text-sm font-medium">SOQL</label>
      <SoqlEditor v-model="soql" />

      <div class="flex items-center gap-3">
        <label class="inline-flex items-center gap-2 text-sm">
          <input type="checkbox" v-model="includeDeleted" />
          Include deleted records (adds <span class="font-mono">ALL ROWS</span>)
        </label>

        <button class="btn ml-auto" :disabled="!activeAlias || isRunning" @click="run">
          {{ isRunning ? 'Running…' : 'Run query' }}
        </button>
      </div>

      <div v-if="error" class="text-sm text-red-700">{{ error }}</div>
    </div>

    <div class="flex items-center gap-2">
      <button class="btn" :class="tab==='results' ? 'bg-slate-100' : ''" @click="tab='results'">Results</button>
      <button class="btn" :class="tab==='logs' ? 'bg-slate-100' : ''" @click="tab='logs'">Logs</button>
    </div>

    <ResultsTable v-if="tab==='results'" :rows="rows" />
    <LogsPanel v-else :lines="logs" />
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import api from '../api/client'
import SoqlEditor from '../components/SoqlEditor.vue'
import ResultsTable from '../components/ResultsTable.vue'
import LogsPanel from '../components/LogsPanel.vue'

const soql = ref('SELECT Id, Name FROM Account LIMIT 10')
const includeDeleted = ref(false)

const activeAlias = ref<string | null>(null)
const rows = ref<any[]>([])
const logs = ref<string[]>([])
const error = ref<string>('')

const tab = ref<'results' | 'logs'>('results')
const isRunning = ref(false)

const emit = defineEmits<{ (e: 'active-alias', alias: string | null): void }>()

async function refreshActiveOrg() {
  const res = await api.get<{ activeAlias: string | null }>('/orgs/active')
  activeAlias.value = res.activeAlias
  emit('active-alias', res.activeAlias)
}

async function run() {
  error.value = ''
  rows.value = []
  logs.value = []
  tab.value = 'results'
  isRunning.value = true

  try {
    const created = await api.post<{ runId: string }>('/query/run', {
      query: soql.value,
      includeDeleted: includeDeleted.value
    })

    const runId = created.runId
    // Start SSE for logs
    const es = new EventSource(`/api/runs/${runId}/events`)
    es.addEventListener('log', (evt: MessageEvent) => {
      try {
        const payload = JSON.parse(evt.data)
        logs.value.push(payload.line)
      } catch {}
    })
    es.addEventListener('status', async (evt: MessageEvent) => {
      es.close()
      try {
        const status = JSON.parse(evt.data).status
        if (status === 'success') {
          const res = await api.get<any>(`/runs/${runId}/result`)
          const recs = (res.result && res.result.records) || []
          // Remove SF internal attributes key if present
          rows.value = recs.map((r: any) => {
            const copy: any = { ...r }
            delete copy.attributes
            return copy
          })
        } else {
          const res = await api.get<any>(`/runs/${runId}/result`).catch(() => null)
          error.value = (res && res.error) || 'Query failed'
          tab.value = 'logs'
        }
      } finally {
        isRunning.value = false
      }
    })
    es.addEventListener('error', () => {
      // Keep logs; likely server closed
    })
  } catch (e: any) {
    error.value = e?.message || String(e)
    tab.value = 'logs'
    isRunning.value = false
  }
}

onMounted(() => {
  refreshActiveOrg().catch(() => {})
})
</script>
