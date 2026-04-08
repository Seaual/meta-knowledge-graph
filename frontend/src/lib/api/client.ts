// frontend/src/lib/api/client.ts
import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  headers: {
    'Content-Type': 'application/json',
  },
})

// Device ID management
const DEVICE_ID_KEY = 'mkg_device_id'

function getOrCreateDeviceId(): string {
  let deviceId = localStorage.getItem(DEVICE_ID_KEY)
  if (!deviceId) {
    deviceId = crypto.randomUUID()
    localStorage.setItem(DEVICE_ID_KEY, deviceId)
  }
  return deviceId
}

// Add device ID header to all requests
api.interceptors.request.use((config) => {
  const deviceId = getOrCreateDeviceId()
  config.headers['X-Device-ID'] = deviceId
  return config
})

export default api
export { getOrCreateDeviceId }