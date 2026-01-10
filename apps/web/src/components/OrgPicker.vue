<template>
  <div class="flex items-center gap-2">
    <select class="select" v-model="selected" @change="selectOrg">
      <option :value="''">Select org…</option>
      <option v-for="o in orgs" :key="o.alias" :value="o.alias">
        {{ o.alias }}
      </option>
    </select>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import api from '../api/client'

type OrgItem = { alias: string; lastSelectedAt?: string | null }
type OrgsResponse = { activeAlias: string | null; orgs: OrgItem[] }

const orgs = ref<OrgItem[]>([])
const selected = ref<string>('')

const emit = defineEmits<{ (e: 'selected', alias: string | null): void }>()

async function refresh() {
  const data = await api.get<OrgsResponse>('/orgs')
  orgs.value = data.orgs
  selected.value = data.activeAlias || ''
  emit('selected', data.activeAlias || null)
}

async function selectOrg() {
  const alias = selected.value
  if (!alias) {
    emit('selected', null)
    return
  }
  await api.post('/orgs/select', { alias })
  await refresh()
}

onMounted(() => {
  refresh().catch(() => {
    // Swallow errors in header; page will show more details.
  })
})
</script>
