<script setup lang="ts">
import { ref, computed } from 'vue'
import { useDbcStore } from '@/stores/dbcStore'
import type { MessageSchema } from '@/types'

const dbcStore = useDbcStore()
const search = ref('')
const expandedIds = ref<Set<number>>(new Set())

const filtered = computed(() => {
  const q = search.value.toLowerCase()
  if (!q) return dbcStore.messages
  return dbcStore.messages.filter(
    m => m.name.toLowerCase().includes(q) || m.id_hex.toLowerCase().includes(q)
  )
})

function toggleExpand(id: number) {
  if (expandedIds.value.has(id)) expandedIds.value.delete(id)
  else expandedIds.value.add(id)
}

function selectAndExpand(msg: MessageSchema) {
  dbcStore.selectMessage(msg)
  expandedIds.value.add(msg.id)
}
</script>

<template>
  <div class="flex flex-col h-full overflow-hidden">
    <!-- Search -->
    <div class="p-2 border-b border-border">
      <input
        v-model="search"
        placeholder="Search messages..."
        class="w-full bg-bg-primary border border-border rounded px-2 py-1 text-xs text-slate-200 placeholder-slate-600 focus:outline-none focus:border-orange-500"
      />
    </div>

    <!-- Message list -->
    <div class="flex-1 overflow-y-auto">
      <div v-if="dbcStore.messages.length === 0" class="text-slate-600 text-xs text-center py-8">
        No messages loaded
      </div>

      <div v-for="msg in filtered" :key="msg.id">
        <!-- Message row -->
        <div
          class="flex items-center gap-2 px-3 py-2 cursor-pointer hover:bg-bg-hover transition-colors border-b border-bg-secondary"
          :class="dbcStore.selectedMessage?.id === msg.id ? 'bg-bg-hover border-l-2 border-l-orange-500' : ''"
          @click="selectAndExpand(msg)"
        >
          <span
            class="text-[10px] text-slate-500 select-none w-3"
            @click.stop="toggleExpand(msg.id)"
          >
            {{ expandedIds.has(msg.id) ? '▼' : '▶' }}
          </span>
          <div class="flex-1 min-w-0">
            <div class="text-xs font-medium text-slate-200 truncate">{{ msg.name }}</div>
            <div class="text-[10px] text-slate-500">{{ msg.id_hex }} · {{ msg.length }}B · {{ msg.signals.length }} signals</div>
          </div>
          <button
            class="shrink-0 px-2 py-0.5 text-[10px] rounded border border-orange-500/50 text-orange-400 hover:bg-orange-500/20 transition-colors"
            @click.stop="dbcStore.selectMessage(msg)"
          >
            Send
          </button>
        </div>

        <!-- Signals (expanded) -->
        <div v-if="expandedIds.has(msg.id)">
          <div
            v-for="sig in msg.signals"
            :key="sig.name"
            class="pl-8 pr-3 py-1.5 flex items-center gap-2 border-b border-bg-secondary bg-bg-sunken"
          >
            <div class="flex-1 min-w-0">
              <span class="text-[11px] text-slate-300">{{ sig.name }}</span>
              <span v-if="sig.unit" class="text-[10px] text-slate-600 ml-1">[{{ sig.unit }}]</span>
            </div>
            <div class="text-[10px] text-slate-600 shrink-0">
              {{ sig.minimum ?? '?' }}..{{ sig.maximum ?? '?' }}
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
