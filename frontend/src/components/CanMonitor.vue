<script setup lang="ts">
import { ref, onMounted, onUnmounted, computed } from 'vue'
import { useCanStore } from '@/stores/canStore'
import type { CanFrameEvent } from '@/types'

const canStore = useCanStore()

let es: EventSource | null = null
const latestId = ref<string | null>(null)

function startSSE() {
  if (es) return
  es = new EventSource('/api/sse/can-stream')
  es.onmessage = (event) => {
    const frame: CanFrameEvent = JSON.parse(event.data)
    canStore.pushFrame(frame)
    latestId.value = `${frame.id_hex}-${frame.timestamp}`
  }
  es.onerror = () => {
    // Auto-reconnects by browser
  }
}

function stopSSE() {
  es?.close()
  es = null
}

onMounted(startSSE)
onUnmounted(stopSSE)

const frames = computed(() => canStore.filteredFrames())

function formatTime(ts: number) {
  const d = new Date(ts * 1000)
  return d.toTimeString().slice(0, 8) + '.' + String(d.getMilliseconds()).padStart(3, '0')
}

function formatSignals(signals: Record<string, number | string>) {
  const entries = Object.entries(signals)
  if (entries.length === 0) return '—'
  return entries.map(([k, v]) => `${k}=${v}`).join('  ')
}
</script>

<template>
  <div class="flex flex-col h-full overflow-hidden">
    <!-- Toolbar -->
    <div class="flex items-center gap-2 px-3 py-2 border-b border-border shrink-0">
      <span class="text-xs font-semibold text-fg-soft">CAN Monitor</span>

      <input
        v-model="canStore.filterText"
        placeholder="Filter by ID / Name..."
        class="ml-2 flex-1 max-w-xs bg-bg-primary border border-border rounded px-2 py-0.5 text-xs text-fg placeholder-fg-faint focus:outline-none focus:border-orange-500"
      />

      <div class="ml-auto flex items-center gap-2">
        <button
          class="px-2 py-0.5 text-xs rounded border transition-colors"
          :class="canStore.paused
            ? 'border-green-500 text-success-fg hover:bg-green-500/10'
            : 'border-yellow-500 text-warning-fg hover:bg-yellow-500/10'"
          @click="canStore.togglePause"
        >
          {{ canStore.paused ? '▶ Resume' : '⏸ Pause' }}
        </button>

        <button
          class="px-2 py-0.5 text-xs rounded border border-border-strong text-fg-secondary hover:bg-bg-active transition-colors"
          @click="canStore.clearFrames"
        >
          Clear
        </button>
      </div>
    </div>

    <!-- Table header -->
    <div class="grid text-[10px] text-fg-muted uppercase tracking-wider px-3 py-1.5 border-b border-border shrink-0"
         style="grid-template-columns: 1fr 1.2fr 1.5fr 1fr 1fr 3fr">
      <span>Time</span>
      <span>ID</span>
      <span>Name</span>
      <span>Dir</span>
      <span>Raw (hex)</span>
      <span>Signals</span>
    </div>

    <!-- Frame rows -->
    <div class="flex-1 overflow-y-auto font-mono">
      <div
        v-for="frame in frames"
        :key="`${frame.id_hex}-${frame.timestamp}`"
        class="grid items-center px-3 py-1 border-b border-bg-secondary hover:bg-bg-hover transition-colors text-[11px]"
        style="grid-template-columns: 1fr 1.2fr 1.5fr 1fr 1fr 3fr"
        :class="{
          'flash-rx': frame.direction === 'rx',
          'flash-tx': frame.direction === 'tx',
        }"
      >
        <span class="text-fg-muted">{{ formatTime(frame.timestamp) }}</span>
        <span class="text-fg-soft">{{ frame.id_hex }}</span>
        <span class="text-fg-secondary truncate" :title="frame.name ?? ''">{{ frame.name ?? '—' }}</span>
        <span
          class="font-semibold"
          :class="frame.direction === 'rx' ? 'text-rx-fg' : 'text-accent-fg'"
        >
          {{ frame.direction.toUpperCase() }}
        </span>
        <span class="text-success-fg tracking-widest text-[10px]">{{ frame.raw_hex }}</span>
        <span class="text-fg-secondary truncate text-[10px]" :title="formatSignals(frame.signals)">
          {{ formatSignals(frame.signals) }}
        </span>
      </div>

      <div v-if="frames.length === 0" class="text-center text-fg-faint text-xs py-8">
        {{ canStore.status.connected ? 'Waiting for CAN frames...' : 'Connect to CAN bus to start monitoring' }}
      </div>
    </div>
  </div>
</template>
