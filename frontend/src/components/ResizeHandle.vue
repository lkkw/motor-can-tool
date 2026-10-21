<script setup lang="ts">
import { ref } from 'vue'

// Zero-size drag handle laid over an existing panel border.
// Emits pixel deltas relative to where the drag started; the parent owns size and clamping.
const props = defineProps<{
  direction: 'x' | 'y' // x = drag left/right (resizes width), y = drag up/down (resizes height)
}>()

const emit = defineEmits<{
  start: []
  move: [delta: number]
  end: []
  reset: []
}>()

const dragging = ref(false)
let origin = 0

function onPointerDown(e: PointerEvent) {
  if (e.button !== 0) return
  e.preventDefault()
  ;(e.currentTarget as HTMLElement).setPointerCapture(e.pointerId)
  origin = props.direction === 'x' ? e.clientX : e.clientY
  dragging.value = true
  // Keep the resize cursor and avoid selecting text while the pointer is over other panels
  document.body.style.cursor = props.direction === 'x' ? 'col-resize' : 'row-resize'
  document.body.style.userSelect = 'none'
  emit('start')
}

function onPointerMove(e: PointerEvent) {
  if (!dragging.value) return
  emit('move', (props.direction === 'x' ? e.clientX : e.clientY) - origin)
}

function onPointerUp() {
  if (!dragging.value) return
  dragging.value = false
  document.body.style.cursor = ''
  document.body.style.userSelect = ''
  emit('end')
}

const KEY_STEP = 16

function onKeydown(e: KeyboardEvent) {
  const keys = props.direction === 'x' ? ['ArrowLeft', 'ArrowRight'] : ['ArrowUp', 'ArrowDown']
  const idx = keys.indexOf(e.key)
  if (idx === -1) return
  e.preventDefault()
  emit('start')
  emit('move', idx === 0 ? -KEY_STEP : KEY_STEP)
  emit('end')
}
</script>

<template>
  <div class="relative shrink-0" :class="direction === 'x' ? 'w-0' : 'h-0'">
    <div
      role="separator"
      :aria-orientation="direction === 'x' ? 'vertical' : 'horizontal'"
      tabindex="0"
      title="Drag to resize · double-click to reset"
      class="group absolute z-20 flex items-center justify-center outline-none"
      :class="direction === 'x'
        ? 'inset-y-0 -left-[3px] w-[6px] cursor-col-resize'
        : 'inset-x-0 -top-[3px] h-[6px] cursor-row-resize'"
      @pointerdown="onPointerDown"
      @pointermove="onPointerMove"
      @pointerup="onPointerUp"
      @pointercancel="onPointerUp"
      @dblclick="emit('reset')"
      @keydown="onKeydown"
    >
      <!-- Accent line shown on hover / focus / drag, centered on the panel border -->
      <div
        class="bg-accent transition-opacity"
        :class="[
          direction === 'x' ? 'w-[2px] h-full' : 'h-[2px] w-full',
          dragging ? 'opacity-100' : 'opacity-0 group-hover:opacity-60 group-focus-visible:opacity-100',
        ]"
      />
    </div>
  </div>
</template>
