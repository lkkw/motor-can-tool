export interface SignalSchema {
  name: string
  start_bit: number
  length: number
  byte_order: 'little_endian' | 'big_endian'
  is_signed: boolean
  scale: number
  offset: number
  minimum: number | null
  maximum: number | null
  unit: string
  choices: Record<string, string> | null
}

export interface MessageSchema {
  id: number
  id_hex: string
  name: string
  length: number
  is_extended_id: boolean
  signals: SignalSchema[]
}

export interface DbcParseResponse {
  filename: string
  message_count: number
  messages: MessageSchema[]
}

export interface CanConnectRequest {
  interface: string
  channel: string
  bitrate: number
  // ZLG (interface === 'zlgcan') only
  device_type?: number
  device_index?: number
  channel_index?: number
  libpath?: string | null
  resistance?: boolean
}

export interface CanSendRequest {
  message_id: number
  is_extended_id: boolean
  signals: Record<string, number>
  interval_ms: number
}

export interface CanFrameEvent {
  timestamp: number
  id: number
  id_hex: string
  name: string | null
  length: number
  raw_hex: string
  signals: Record<string, number | string>
  direction: 'rx' | 'tx'
}

export interface CanStatusResponse {
  connected: boolean
  interface: string | null
  channel: string | null
  bitrate: number | null
  rx_count: number
  tx_count: number
  error_count: number
}

export interface PeriodicTaskInfo {
  task_id: string
  message_id: number
  message_name: string | null
  interval_ms: number
}
