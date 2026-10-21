<script setup lang="ts">
import { useCanStore } from '@/stores/canStore'
import { useRequest } from 'alova/client'
import { stopPeriodic } from '@/api/can'

const canStore = useCanStore()

const { send: doStop } = useRequest((id: string) => stopPeriodic(id), { immediate: false })

async function stopTask(taskId: string) {
  await doStop(taskId)
  canStore.removePeriodicTask(taskId)
}
</script>

<template>
  <div class="h-8 flex items-center px-4 gap-6 border-t border-border bg-bg-primary text-[11px] font-mono shrink-0">
    <span class="text-fg-muted">
      RX <span class="text-rx-fg">{{ canStore.status.rx_count }}</span>
    </span>
    <span class="text-fg-muted">
      TX <span class="text-accent-fg">{{ canStore.status.tx_count }}</span>
    </span>
    <span class="text-fg-muted">
      ERR <span class="text-danger-fg">{{ canStore.status.error_count }}</span>
    </span>

    <!-- Periodic tasks -->
    <div v-if="canStore.periodicTasks.length > 0" class="flex items-center gap-2 ml-4">
      <span class="text-fg-faint">Periodic:</span>
      <div
        v-for="task in canStore.periodicTasks"
        :key="task.task_id"
        class="flex items-center gap-1 bg-orange-500/10 border border-orange-500/30 rounded px-2 py-0.5"
      >
        <span class="text-accent-fg">{{ task.message_name ?? task.message_id }}</span>
        <span class="text-fg-faint">{{ task.interval_ms }}ms</span>
        <button
          class="text-fg-muted hover:text-danger-fg ml-1 transition-colors"
          @click="stopTask(task.task_id)"
        >×</button>
      </div>
    </div>

    <div class="ml-auto text-fg-ghost">Motor CAN Tool v0.1</div>
  </div>
</template>
