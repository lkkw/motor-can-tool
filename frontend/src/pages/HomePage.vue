<script setup lang="ts">
import DbcUploader from '@/components/DbcUploader.vue'
import MessageTree from '@/components/MessageTree.vue'
import CanMonitor from '@/components/CanMonitor.vue'
import CanSendPanel from '@/components/CanSendPanel.vue'
import DeviceSelector from '@/components/DeviceSelector.vue'
import StatusBar from '@/components/StatusBar.vue'
import ResizeHandle from '@/components/ResizeHandle.vue'
import ThemeToggle from '@/components/ThemeToggle.vue'
import { ref } from 'vue'

// ── Resizable panels ─────────────────────────────────────────────────────────

const ASIDE_DEFAULT = 288 // px, left panel width
const ASIDE_MIN = 200
const MAIN_MIN = 420 // px left for the monitor/send column
const SEND_DEFAULT = 256 // px, send panel height
const SEND_MIN = 120
const MONITOR_MIN = 150

const LAYOUT_KEY = 'motorcan.layout'

function loadLayout(): { aside: number; send: number } {
  try {
    const saved = JSON.parse(localStorage.getItem(LAYOUT_KEY) ?? 'null')
    if (typeof saved?.aside === 'number' && typeof saved?.send === 'number') return saved
  } catch {
    // Storage unavailable or corrupt; fall back to defaults
  }
  return { aside: ASIDE_DEFAULT, send: SEND_DEFAULT }
}

function saveLayout() {
  try {
    localStorage.setItem(LAYOUT_KEY, JSON.stringify({ aside: asideWidth.value, send: sendHeight.value }))
  } catch {
    // Not persisted; layout still works for this session
  }
}

const initial = loadLayout()
const asideWidth = ref(initial.aside)
const sendHeight = ref(initial.send)

const rowEl = ref<HTMLElement | null>(null) // aside + main
const mainEl = ref<HTMLElement | null>(null) // monitor + send

const clamp = (v: number, min: number, max: number) => Math.round(Math.min(Math.max(v, min), Math.max(min, max)))

let dragStart = 0

function onAsideMove(delta: number) {
  asideWidth.value = clamp(dragStart + delta, ASIDE_MIN, (rowEl.value?.clientWidth ?? Infinity) - MAIN_MIN)
}

function onSendMove(delta: number) {
  // Handle sits above the send panel: dragging up (negative delta) makes it taller
  sendHeight.value = clamp(dragStart - delta, SEND_MIN, (mainEl.value?.clientHeight ?? Infinity) - MONITOR_MIN)
}
</script>

<template>
  <div class="flex flex-col h-screen bg-bg-primary text-fg overflow-hidden">

    <!-- Top Navbar -->
    <header class="h-12 flex items-center px-4 gap-4 border-b border-border bg-bg-secondary shrink-0">
      <div class="flex items-center gap-2">
        <!-- Logo -->
        <svg width="20" height="20" viewBox="0 0 20 20" fill="none" xmlns="http://www.w3.org/2000/svg">
          <circle cx="10" cy="10" r="8" stroke="#f97316" stroke-width="1.5"/>
          <circle cx="10" cy="10" r="3" fill="#f97316"/>
          <line x1="10" y1="2" x2="10" y2="6" stroke="#f97316" stroke-width="1.5"/>
          <line x1="10" y1="14" x2="10" y2="18" stroke="#f97316" stroke-width="1.5"/>
          <line x1="2" y1="10" x2="6" y2="10" stroke="#f97316" stroke-width="1.5"/>
          <line x1="14" y1="10" x2="18" y2="10" stroke="#f97316" stroke-width="1.5"/>
        </svg>
        <span class="text-sm font-bold text-accent-fg tracking-wider">MotorCAN</span>
        <span class="text-xs text-fg-faint hidden sm:inline">/ Motor MCU Debug Tool</span>
      </div>

      <div class="ml-auto flex items-center gap-3">
        <DeviceSelector />
        <ThemeToggle />
      </div>
    </header>

    <!-- Main content -->
    <div ref="rowEl" class="flex flex-1 overflow-hidden">

      <!-- Left panel: DBC + Message tree (resizable width) -->
      <aside
        class="flex flex-col border-r border-border shrink-0 overflow-hidden"
        :style="{ width: `${asideWidth}px`, minWidth: `${ASIDE_MIN}px`, maxWidth: `calc(100% - ${MAIN_MIN}px)` }"
      >
        <!-- DBC Upload -->
        <div class="border-b border-border shrink-0">
          <div class="px-3 pt-2 pb-0 text-[10px] text-fg-muted uppercase tracking-widest font-semibold">
            DBC File
          </div>
          <DbcUploader />
        </div>

        <!-- Message Tree -->
        <div class="flex-1 overflow-hidden flex flex-col">
          <div class="px-3 py-2 text-[10px] text-fg-muted uppercase tracking-widest font-semibold border-b border-border shrink-0">
            Messages
          </div>
          <MessageTree />
        </div>
      </aside>

      <ResizeHandle
        direction="x"
        @start="dragStart = asideWidth"
        @move="onAsideMove"
        @end="saveLayout"
        @reset="asideWidth = ASIDE_DEFAULT; saveLayout()"
      />

      <!-- Right panel: Monitor + Send -->
      <main ref="mainEl" class="flex-1 min-w-0 flex flex-col overflow-hidden">

        <!-- CAN Monitor (takes remaining height) -->
        <div class="flex-1 flex flex-col overflow-hidden border-b border-border">
          <CanMonitor />
        </div>

        <ResizeHandle
          direction="y"
          @start="dragStart = sendHeight"
          @move="onSendMove"
          @end="saveLayout"
          @reset="sendHeight = SEND_DEFAULT; saveLayout()"
        />

        <!-- Send panel (resizable height) -->
        <div
          class="flex flex-col overflow-hidden shrink-0"
          :style="{ height: `${sendHeight}px`, minHeight: `${SEND_MIN}px`, maxHeight: `calc(100% - ${MONITOR_MIN}px)` }"
        >
          <div class="px-3 py-2 text-[10px] text-fg-muted uppercase tracking-widest font-semibold border-b border-border shrink-0">
            Signal Editor & Send
          </div>
          <CanSendPanel class="flex-1 overflow-hidden" />
        </div>

      </main>
    </div>

    <!-- Status bar -->
    <StatusBar />
  </div>
</template>
