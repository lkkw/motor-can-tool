import { ref } from 'vue'
import { defineStore } from 'pinia'
import type { CanFrameEvent, CanStatusResponse, PeriodicTaskInfo } from '@/types'

const MAX_FRAMES = 1000

export const useCanStore = defineStore('can', () => {
  const status = ref<CanStatusResponse>({
    connected: false,
    interface: null,
    channel: null,
    bitrate: null,
    rx_count: 0,
    tx_count: 0,
    error_count: 0,
  })

  const frames = ref<CanFrameEvent[]>([])
  const paused = ref(false)
  const periodicTasks = ref<PeriodicTaskInfo[]>([])
  const filterText = ref('')

  function setStatus(s: CanStatusResponse) {
    status.value = s
  }

  function pushFrame(frame: CanFrameEvent) {
    if (paused.value) return
    frames.value.unshift(frame) // newest first
    if (frames.value.length > MAX_FRAMES) {
      frames.value.length = MAX_FRAMES
    }
    // RX/TX/ERR counts come from the backend via status polling (see DeviceSelector)
  }

  function clearFrames() {
    frames.value = []
  }

  function togglePause() {
    paused.value = !paused.value
  }

  // Bumped on every local add/remove so a poll that started earlier can't overwrite it with a stale list
  let tasksVersion = 0

  function getTasksVersion() {
    return tasksVersion
  }

  function setPeriodicTasks(tasks: PeriodicTaskInfo[]) {
    periodicTasks.value = tasks
  }

  function removePeriodicTask(taskId: string) {
    tasksVersion++
    periodicTasks.value = periodicTasks.value.filter(t => t.task_id !== taskId)
  }

  function addPeriodicTask(task: PeriodicTaskInfo) {
    tasksVersion++
    periodicTasks.value = [...periodicTasks.value, task]
  }

  const filteredFrames = () => {
    const q = filterText.value.trim().toLowerCase()
    if (!q) return frames.value
    return frames.value.filter(
      f => f.id_hex.toLowerCase().includes(q) || (f.name ?? '').toLowerCase().includes(q)
    )
  }

  return {
    status,
    frames,
    paused,
    periodicTasks,
    filterText,
    setStatus,
    pushFrame,
    clearFrames,
    togglePause,
    getTasksVersion,
    setPeriodicTasks,
    removePeriodicTask,
    addPeriodicTask,
    filteredFrames,
  }
})
