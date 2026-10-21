<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRequest } from 'alova/client'
import { connectCan, disconnectCan, getCanStatus, listPeriodic } from '@/api/can'
import { useCanStore } from '@/stores/canStore'

const canStore = useCanStore()

const showPanel = ref(false)
const form = ref({
  interface: 'virtual',
  channel: 'vcan0',
  bitrate: 500000,
  // ZLG only
  device_type: 4,
  device_index: 0,
  channel_index: 0,
  libpath: '',
  resistance: true,
})

const INTERFACES = ['virtual', 'pcan', 'socketcan', 'kvaser', 'zlgcan', 'usb2can']
const BITRATES = [125000, 250000, 500000, 1000000]
// ZCANDeviceType values from the zlgcan plugin
const ZLG_DEVICE_TYPES = [
  { value: 3, label: 'USBCAN-I' },
  { value: 4, label: 'USBCAN-II' },
]

const isZlg = computed(() => form.value.interface === 'zlgcan')

const { send: doConnect, loading: connecting } = useRequest(
  () => connectCan({
    ...form.value,
    libpath: form.value.libpath.trim() || null,  // empty = backend default (backend/library)
  }),
  { immediate: false }
)

const { send: doDisconnect, loading: disconnecting } = useRequest(
  () => disconnectCan(),
  { immediate: false }
)

// Backend is the source of truth for connection state, counters and periodic tasks.
// Poll it so a page reload restores state and RX/TX/ERR stay accurate.
const POLL_INTERVAL_MS = 1000
let pollTimer: ReturnType<typeof setTimeout> | null = null
let polling = true

async function syncFromBackend() {
  try {
    const version = canStore.getTasksVersion()
    const [s, tasks] = await Promise.all([getCanStatus(), listPeriodic()])
    canStore.setStatus(s)
    if (canStore.getTasksVersion() === version) canStore.setPeriodicTasks(tasks)
  } catch {
    // Backend unreachable; keep last known state and retry on next tick
  }
  if (polling) pollTimer = setTimeout(syncFromBackend, POLL_INTERVAL_MS)
}

onMounted(syncFromBackend)
onUnmounted(() => {
  polling = false
  if (pollTimer) clearTimeout(pollTimer)
})

async function handleConnect() {
  try {
    const s = await doConnect()
    canStore.setStatus(s)
    showPanel.value = false
  } catch (e: any) {
    alert(e.message)
  }
}

async function handleDisconnect() {
  const s = await doDisconnect()
  canStore.setStatus(s)
}

const connected = computed(() => canStore.status.connected)
</script>

<template>
  <div class="relative">
    <!-- Status badge -->
    <div class="flex items-center gap-3">
      <div class="flex items-center gap-2">
        <span
          class="w-2 h-2 rounded-full"
          :class="connected ? 'bg-green-400 shadow-[0_0_6px_#4ade80]' : 'bg-red-500'"
        />
        <span class="text-sm" :class="connected ? 'text-success-fg' : 'text-fg-secondary'">
          {{ connected
            ? `${canStore.status.interface?.toUpperCase()} · ${canStore.status.channel} · ${(canStore.status.bitrate! / 1000)}kbps`
            : 'Disconnected' }}
        </span>
      </div>

      <button
        v-if="!connected"
        class="px-3 py-1 text-xs rounded border border-orange-500 text-accent-fg hover:bg-orange-500/10 transition-colors"
        @click="showPanel = !showPanel"
      >
        Connect
      </button>
      <button
        v-else
        class="px-3 py-1 text-xs rounded border border-red-500 text-danger-fg hover:bg-red-500/10 transition-colors"
        :disabled="disconnecting"
        @click="handleDisconnect"
      >
        {{ disconnecting ? '...' : 'Disconnect' }}
      </button>
    </div>

    <!-- Connect panel dropdown -->
    <div
      v-if="showPanel && !connected"
      class="absolute right-0 top-10 z-50 w-72 rounded-lg border border-border bg-bg-card p-4 shadow-2xl"
    >
      <h3 class="text-sm font-semibold text-fg mb-3">CAN Interface Settings</h3>

      <div class="space-y-3">
        <div>
          <label class="text-xs text-fg-secondary mb-1 block">Interface</label>
          <select
            v-model="form.interface"
            class="w-full bg-bg-primary border border-border rounded px-2 py-1.5 text-sm text-fg focus:outline-none focus:border-orange-500"
          >
            <option v-for="iface in INTERFACES" :key="iface" :value="iface">{{ iface }}</option>
          </select>
        </div>

        <div v-if="!isZlg">
          <label class="text-xs text-fg-secondary mb-1 block">Channel</label>
          <input
            v-model="form.channel"
            class="w-full bg-bg-primary border border-border rounded px-2 py-1.5 text-sm text-fg focus:outline-none focus:border-orange-500"
            placeholder="e.g. PCAN_USBBUS1 / vcan0"
          />
        </div>

        <template v-else>
          <div>
            <label class="text-xs text-fg-secondary mb-1 block">Device Type</label>
            <select
              v-model.number="form.device_type"
              class="w-full bg-bg-primary border border-border rounded px-2 py-1.5 text-sm text-fg focus:outline-none focus:border-orange-500"
            >
              <option v-for="d in ZLG_DEVICE_TYPES" :key="d.value" :value="d.value">{{ d.label }}</option>
            </select>
          </div>

          <div class="flex gap-2">
            <div class="flex-1">
              <label class="text-xs text-fg-secondary mb-1 block">CAN Channel</label>
              <select
                v-model.number="form.channel_index"
                class="w-full bg-bg-primary border border-border rounded px-2 py-1.5 text-sm text-fg focus:outline-none focus:border-orange-500"
              >
                <option :value="0">CAN1</option>
                <option :value="1">CAN2</option>
              </select>
            </div>
            <div class="w-24">
              <label class="text-xs text-fg-secondary mb-1 block" title="Which card, when several of the same type are plugged in">Device Index</label>
              <input
                v-model.number="form.device_index"
                type="number"
                min="0"
                class="w-full bg-bg-primary border border-border rounded px-2 py-1.5 text-sm text-fg focus:outline-none focus:border-orange-500"
              />
            </div>
          </div>

          <label class="flex items-center gap-2 text-xs text-fg-secondary">
            <input v-model="form.resistance" type="checkbox" class="accent-orange-500" />
            120Ω terminal resistor
          </label>

          <div>
            <label class="text-xs text-fg-secondary mb-1 block">Driver Library Path</label>
            <input
              v-model="form.libpath"
              class="w-full bg-bg-primary border border-border rounded px-2 py-1.5 text-sm text-fg placeholder-fg-faint focus:outline-none focus:border-orange-500"
              placeholder="empty = backend/library"
            />
          </div>
        </template>

        <div>
          <label class="text-xs text-fg-secondary mb-1 block">Bitrate</label>
          <select
            v-model.number="form.bitrate"
            class="w-full bg-bg-primary border border-border rounded px-2 py-1.5 text-sm text-fg focus:outline-none focus:border-orange-500"
          >
            <option v-for="br in BITRATES" :key="br" :value="br">{{ br / 1000 }} kbps</option>
          </select>
        </div>

        <button
          class="w-full py-2 rounded bg-orange-500 hover:bg-orange-600 text-white text-sm font-medium transition-colors disabled:opacity-50"
          :disabled="connecting"
          @click="handleConnect"
        >
          {{ connecting ? 'Connecting...' : 'Connect' }}
        </button>
      </div>
    </div>
  </div>
</template>
