<template>
  <div class="min-h-screen bg-slate-50 text-slate-900">
    <header class="sticky top-0 z-10 border-b border-slate-200 bg-white">
      <div class="mx-auto max-w-6xl px-4 py-3 flex items-center gap-4">
        <div class="font-semibold">SF Wizard</div>

        <nav class="flex items-center gap-3 text-sm">
          <RouterLink class="hover:underline" to="/query">Query</RouterLink>
          <RouterLink class="hover:underline" to="/deploy">Deploy</RouterLink>
        </nav>

        <div class="ml-auto flex items-center gap-2">
          <OrgPicker @selected="onSelected" />
          <OrgBadge :alias="activeAlias" />
        </div>
      </div>
    </header>

    <main class="mx-auto max-w-6xl px-4 py-6">
      <RouterView @active-alias="setActiveAlias" />
    </main>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { RouterLink, RouterView } from 'vue-router'
import OrgBadge from '../components/OrgBadge.vue'
import OrgPicker from '../components/OrgPicker.vue'

const activeAlias = ref<string | null>(null)

function setActiveAlias(alias: string | null) {
  activeAlias.value = alias
}

function onSelected(alias: string | null) {
  activeAlias.value = alias
}
</script>
