<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRequest } from 'alova/client'
import { uploadDbc, getMessages } from '@/api/dbc'
import { useDbcStore } from '@/stores/dbcStore'

const dbcStore = useDbcStore()
const isDragging = ref(false)

// Restore the DBC already loaded on the backend (e.g. after a page reload)
onMounted(async () => {
  if (dbcStore.filename) return
  try {
    const res = await getMessages()
    if (res) dbcStore.loadDbc(res)
  } catch {
    // Backend unreachable; user can upload manually
  }
})

const { send, loading } = useRequest((file: File) => uploadDbc(file), { immediate: false })

async function handleFile(file: File) {
  if (!file.name.endsWith('.dbc')) {
    alert('Please select a .dbc file')
    return
  }
  try {
    const res = await send(file)
    dbcStore.loadDbc(res)
  } catch (e: any) {
    alert(`Parse failed: ${e.message}`)
  }
}

function onDrop(e: DragEvent) {
  isDragging.value = false
  const file = e.dataTransfer?.files[0]
  if (file) handleFile(file)
}

function onInput(e: Event) {
  const file = (e.target as HTMLInputElement).files?.[0]
  if (file) handleFile(file)
}
</script>

<template>
  <div class="p-3">
    <label
      class="flex flex-col items-center justify-center gap-2 w-full h-20 rounded-lg border-2 border-dashed cursor-pointer transition-colors"
      :class="isDragging
        ? 'border-orange-400 bg-orange-500/10'
        : 'border-border hover:border-orange-500/50 hover:bg-bg-hover'"
      @dragover.prevent="isDragging = true"
      @dragleave="isDragging = false"
      @drop.prevent="onDrop"
    >
      <input type="file" accept=".dbc" class="hidden" @change="onInput" />

      <div v-if="loading" class="text-accent-fg text-sm animate-pulse">Parsing DBC...</div>
      <div v-else-if="dbcStore.filename" class="text-center">
        <div class="text-xs text-success-fg">✓ {{ dbcStore.filename }}</div>
        <div class="text-xs text-fg-muted mt-0.5">{{ dbcStore.messages.length }} messages · click to reload</div>
      </div>
      <div v-else class="text-center">
        <div class="text-fg-secondary text-xs">Drop .dbc file here</div>
        <div class="text-fg-faint text-xs mt-0.5">or click to browse</div>
      </div>
    </label>
  </div>
</template>
