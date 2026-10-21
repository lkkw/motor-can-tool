import { alova } from './client'
import type { DbcParseResponse } from '@/types'

export const uploadDbc = (file: File) => {
  const form = new FormData()
  form.append('file', file)
  return alova.Post<DbcParseResponse>('/dbc/upload', form)
}

export const getMessages = () =>
  alova.Get<DbcParseResponse | null>('/dbc/messages')
