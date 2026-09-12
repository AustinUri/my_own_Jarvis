import { useCallback, useEffect, useRef, useState } from 'react'
import type { CameraStatus, ConfigState, Metrics, Snapshot, UiCommand } from './types'

const emptySnapshot: Snapshot = {
  version: 24,
  runtime: { assistantState: 'Idle', transcript: '', response: '', responseLanguage: 'en', spoken: '', logs: [], error: '' },
  config: {}, aiStatus: 'Connecting…', capabilities: [],
}

export function useJarvisSocket() {
  const [snapshot, setSnapshot] = useState<Snapshot>(emptySnapshot)
  const [metrics, setMetrics] = useState<Metrics>({ cpu: 0, ram: 0, battery: null })
  const [connected, setConnected] = useState(false)
  const [uiCommand, setUiCommand] = useState<UiCommand | null>(null)
  const [cameraStatus, setCameraStatus] = useState<CameraStatus>({ enabled: false, hasFrame: false })
  const socket = useRef<WebSocket | null>(null)

  useEffect(() => {
    let retry: number | undefined
    let disposed = false
    const connect = () => {
      if (disposed) return
      const proto = location.protocol === 'https:' ? 'wss' : 'ws'
      const ws = new WebSocket(`${proto}://${location.host}/ws`)
      socket.current = ws
      ws.onopen = () => setConnected(true)
      ws.onclose = () => {
        setConnected(false)
        if (!disposed) retry = window.setTimeout(connect, 1200)
      }
      ws.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data)
          const { type, payload } = message
          if (type === 'snapshot') setSnapshot(payload)
          else if (type === 'state') setSnapshot(s => ({ ...s, runtime: { ...s.runtime, assistantState: payload } }))
          else if (type === 'transcript') setSnapshot(s => ({ ...s, runtime: { ...s.runtime, transcript: payload.text || '' } }))
          else if (type === 'response') setSnapshot(s => ({ ...s, runtime: { ...s.runtime, response: payload.text || '', responseLanguage: payload.language || 'en' } }))
          else if (type === 'spoken') setSnapshot(s => ({ ...s, runtime: { ...s.runtime, spoken: payload || '' } }))
          else if (type === 'log') setSnapshot(s => ({ ...s, runtime: { ...s.runtime, logs: [...s.runtime.logs, String(payload)].slice(-300) } }))
          else if (type === 'error') setSnapshot(s => ({ ...s, runtime: { ...s.runtime, error: String(payload || '') } }))
          else if (type === 'config') setSnapshot(s => ({ ...s, config: payload }))
          else if (type === 'system_metrics') setMetrics(payload)
          else if (type === 'ui_command') setUiCommand({ action: String(payload?.action || ''), payload: payload?.payload || {}, nonce: Date.now() })
          else if (type === 'camera_status') setCameraStatus(payload || { enabled: false, hasFrame: false })
          else if (type === 'ai_status') setSnapshot(s => ({ ...s, aiStatus: String(payload || '') }))
        } catch { /* ignore malformed events */ }
      }
    }
    connect()
    return () => {
      disposed = true
      if (retry) clearTimeout(retry)
      socket.current?.close()
    }
  }, [])

  const send = useCallback((action: string, payload: Record<string, unknown> = {}) => {
    if (socket.current?.readyState === WebSocket.OPEN) {
      socket.current.send(JSON.stringify({ action, payload }))
    }
  }, [])

  const patchConfig = useCallback((patch: ConfigState) => send('config_patch', patch), [send])
  return { snapshot, metrics, connected, uiCommand, cameraStatus, send, patchConfig }
}
