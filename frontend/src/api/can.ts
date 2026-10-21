import { alova } from './client'
import type {
  CanConnectRequest,
  CanSendRequest,
  CanStatusResponse,
  PeriodicTaskInfo,
} from '@/types'

export const connectCan = (cfg: CanConnectRequest) =>
  alova.Post<CanStatusResponse>('/can/connect', cfg)

export const disconnectCan = () =>
  alova.Post<CanStatusResponse>('/can/disconnect', {})

export const getCanStatus = () =>
  alova.Get<CanStatusResponse>('/can/status')

export const sendFrame = (req: CanSendRequest) =>
  alova.Post<{ status: string; task_id?: string }>('/can/send', req)

export const stopPeriodic = (taskId: string) =>
  alova.Delete<{ status: string }>(`/can/periodic/${taskId}`)

export const listPeriodic = () =>
  alova.Get<PeriodicTaskInfo[]>('/can/periodic')
