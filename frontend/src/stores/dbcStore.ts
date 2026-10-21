import { ref } from 'vue'
import { defineStore } from 'pinia'
import type { DbcParseResponse, MessageSchema } from '@/types'

export const useDbcStore = defineStore('dbc', () => {
  const filename = ref<string | null>(null)
  const messages = ref<MessageSchema[]>([])
  const selectedMessage = ref<MessageSchema | null>(null)

  function loadDbc(response: DbcParseResponse) {
    filename.value = response.filename
    messages.value = response.messages
    selectedMessage.value = null
  }

  function selectMessage(msg: MessageSchema | null) {
    selectedMessage.value = msg
  }

  function clear() {
    filename.value = null
    messages.value = []
    selectedMessage.value = null
  }

  return { filename, messages, selectedMessage, loadDbc, selectMessage, clear }
})
