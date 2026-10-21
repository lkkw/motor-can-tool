<script setup lang="ts">
import { ref, watch } from 'vue'
import { useRequest } from 'alova/client'
import { sendFrame, stopPeriodic } from '@/api/can'
import { useDbcStore } from '@/stores/dbcStore'
import { useCanStore } from '@/stores/canStore'
import type { PeriodicTaskInfo } from '@/types'

const dbcStore = useDbcStore()
const canStore = useCanStore()

// Signal values map: signal name -> raw input string
const signalValues = ref<Record<string, string>>({})
const intervalMs = ref(0)
const activeTaskId = ref<string | null>(null)

// Reset values when message changes
watch(
  () => dbcStore.selectedMessage,
  (msg) => {
    signalValues.value = {}
    if (msg) {
      for (const sig of msg.signals) {
        // Default to minimum or 0
        signalValues.value[sig.name] = String(sig.minimum ?? 0)
      }
    }
    activeTaskId.value = null
  }
)

// Drop the local task handle once the backend no longer has it (stopped elsewhere or bus disconnected)
watch(
  () => canStore.periodicTasks,
  (tasks) => {
    if (activeTaskId.value && !tasks.some(t => t.task_id === activeTaskId.value)) {
      activeTaskId.value = null
    }
  }
)

const { send: doSend, loading: sending } = useRequest(
  () => {
    const msg = dbcStore.selectedMessage!
    const signals: Record<string, number> = {}
    for (const [k, v] of Object.entries(signalValues.value)) {
      signals[k] = parseFloat(v) || 0
    }
    return sendFrame({
      message_id: msg.id,
      is_extended_id: msg.is_extended_id,
      signals,
      interval_ms: intervalMs.value,
    })
  },
  { immediate: false }
)

const { send: doStop, loading: stopping } = useRequest(
  () => stopPeriodic(activeTaskId.value!),
  { immediate: false }
)

async function handleSend() {
  if (!canStore.status.connected) {
    alert('CAN bus not connected')
    return
  }
  const res = await doSend()
  if (res.task_id) {
    activeTaskId.value = res.task_id
    // Register periodic task in store
    const msg = dbcStore.selectedMessage!
    canStore.addPeriodicTask({
      task_id: res.task_id,
      message_id: msg.id,
      message_name: msg.name,
      interval_ms: intervalMs.value,
    } as PeriodicTaskInfo)
  }
}

async function handleStop() {
  if (!activeTaskId.value) return
  await doStop()
  canStore.removePeriodicTask(activeTaskId.value)
  activeTaskId.value = null
}

function getSignalValidation(sig: any, val: string) {
  const n = parseFloat(val)
  if (isNaN(n)) return 'error'
  if (sig.minimum !== null && n < sig.minimum) return 'warn'
  if (sig.maximum !== null && n > sig.maximum) return 'warn'
  return 'ok'
}
</script>

<template>
  <div class="h-full flex flex-col overflow-hidden">
    <!-- Empty state -->
    <div v-if="!dbcStore.selectedMessage" class="flex-1 flex items-center justify-center text-slate-600 text-sm">
      Select a message from the left panel to send
    </div>

    <template v-else>
      <!-- Message header -->
      <div class="px-4 py-3 border-b border-border flex items-center gap-3 shrink-0">
        <div>
          <div class="text-sm font-semibold text-orange-400">{{ dbcStore.selectedMessage.name }}</div>
          <div class="text-xs text-slate-500">
            {{ dbcStore.selectedMessage.id_hex }} · {{ dbcStore.selectedMessage.length }} bytes ·
            {{ dbcStore.selectedMessage.is_extended_id ? 'Extended' : 'Standard' }}
          </div>
        </div>
        <div class="ml-auto flex items-center gap-2">
          <!-- Interval selector -->
          <div class="flex items-center gap-1.5">
            <span class="text-xs text-slate-500">Interval</span>
            <select
              v-model.number="intervalMs"
              class="bg-bg-primary border border-border rounded px-2 py-1 text-xs text-slate-200 focus:outline-none focus:border-orange-500"
              :disabled="!!activeTaskId"
            >
              <option :value="0">Once</option>
              <option :value="10">10 ms</option>
              <option :value="20">20 ms</option>
              <option :value="50">50 ms</option>
              <option :value="100">100 ms</option>
              <option :value="200">200 ms</option>
              <option :value="500">500 ms</option>
              <option :value="1000">1000 ms</option>
            </select>
          </div>

          <!-- Stop periodic -->
          <button
            v-if="activeTaskId"
            class="px-3 py-1 text-xs rounded bg-red-500/20 border border-red-500 text-red-400 hover:bg-red-500/30 transition-colors"
            :disabled="stopping"
            @click="handleStop"
          >
            {{ stopping ? '...' : '■ Stop' }}
          </button>

          <!-- Send / Start -->
          <button
            v-else
            class="px-4 py-1.5 text-xs rounded bg-orange-500 hover:bg-orange-600 text-white font-medium transition-colors disabled:opacity-50"
            :disabled="sending || !canStore.status.connected"
            @click="handleSend"
          >
            {{ sending ? 'Sending...' : intervalMs > 0 ? '▶ Start Periodic' : '▶ Send Once' }}
          </button>
        </div>
      </div>

      <!-- Signal editors -->
      <div class="flex-1 overflow-y-auto p-3 space-y-2">
        <div
          v-for="sig in dbcStore.selectedMessage.signals"
          :key="sig.name"
          class="bg-bg-secondary rounded-lg p-3 border border-border"
        >
          <div class="flex items-start gap-3">
            <div class="flex-1 min-w-0">
              <div class="flex items-center gap-2 mb-1">
                <span class="text-xs font-medium text-slate-200">{{ sig.name }}</span>
                <span v-if="sig.unit" class="text-[10px] text-slate-600 bg-bg-primary px-1.5 rounded">{{ sig.unit }}</span>
              </div>
              <div class="text-[10px] text-slate-600">
                {{ sig.start_bit }}bit · {{ sig.length }}b · {{ sig.byte_order === 'little_endian' ? 'LE' : 'BE' }} ·
                scale={{ sig.scale }} offset={{ sig.offset }}
                <span v-if="sig.minimum !== null || sig.maximum !== null">
                  · [{{ sig.minimum ?? '-∞' }}, {{ sig.maximum ?? '+∞' }}]
                </span>
              </div>
            </div>

            <!-- Enum select -->
            <div v-if="sig.choices" class="w-36">
              <select
                v-model="signalValues[sig.name]"
                class="w-full bg-bg-primary border border-border rounded px-2 py-1 text-xs text-slate-200 focus:outline-none focus:border-orange-500"
              >
                <option v-for="(label, val) in sig.choices" :key="val" :value="val">
                  {{ val }} - {{ label }}
                </option>
              </select>
            </div>

            <!-- Numeric input -->
            <div v-else class="w-36">
              <input
                v-model="signalValues[sig.name]"
                type="number"
                :min="sig.minimum ?? undefined"
                :max="sig.maximum ?? undefined"
                :step="sig.scale"
                class="w-full bg-bg-primary rounded px-2 py-1 text-xs text-slate-200 focus:outline-none border transition-colors"
                :class="{
                  'border-red-500': getSignalValidation(sig, signalValues[sig.name] ?? '') === 'error',
                  'border-yellow-500': getSignalValidation(sig, signalValues[sig.name] ?? '') === 'warn',
                  'border-border focus:border-orange-500': getSignalValidation(sig, signalValues[sig.name] ?? '') === 'ok',
                }"
              />
            </div>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>
