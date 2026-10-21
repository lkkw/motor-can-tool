import { createAlova } from 'alova'
import adapterFetch from 'alova/fetch'
import vueHook from 'alova/vue'

export const alova = createAlova({
  baseURL: '/api',
  statesHook: vueHook,
  requestAdapter: adapterFetch(),
  // Status/DBC/task endpoints reflect live backend state; never serve them from cache
  cacheFor: null,
  responded: {
    onSuccess: async (response: Response) => {
      if (!response.ok) {
        const body = await response.json().catch(() => ({}))
        throw new Error(body.detail ?? response.statusText)
      }
      if (response.status === 204) return null
      return response.json()
    },
    onError: (err: Error) => {
      console.error('[Alova]', err.message)
      throw err
    },
  },
})
