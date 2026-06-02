import { useState, useEffect, useRef, useCallback } from 'react'

const WS_URL = 'ws://localhost:8000/ws'
const PING_INTERVAL = 25000 // 25s

export function useWebSocket(onTransaction) {
  const [connected, setConnected] = useState(false)
  const wsRef = useRef(null)
  const pingRef = useRef(null)
  const reconnectRef = useRef(null)
  const mountedRef = useRef(true)

  const connect = useCallback(() => {
    if (!mountedRef.current) return
    try {
      const ws = new WebSocket(WS_URL)
      wsRef.current = ws

      ws.onopen = () => {
        if (!mountedRef.current) return
        setConnected(true)
        console.log('🔌 WebSocket connected')
        // Clear any pending reconnect timer
        if (reconnectRef.current) clearTimeout(reconnectRef.current)
        // Start ping to keep alive
        pingRef.current = setInterval(() => {
          if (ws.readyState === WebSocket.OPEN) ws.send('ping')
        }, PING_INTERVAL)
      }

      ws.onmessage = (event) => {
        if (!mountedRef.current) return
        try {
          const msg = JSON.parse(event.data)
          if (msg.type === 'transaction' && msg.data) {
            onTransaction(msg.data)
          } else if (msg.type === 'history' && Array.isArray(msg.data)) {
            // Load history in reverse (oldest first)
            msg.data.reverse().forEach(tx => onTransaction(tx, true))
          }
        } catch (e) {
          console.warn('WS parse error:', e)
        }
      }

      ws.onclose = () => {
        if (!mountedRef.current) return
        setConnected(false)
        if (pingRef.current) clearInterval(pingRef.current)
        console.log('🔌 WebSocket closed — reconnecting in 3s')
        reconnectRef.current = setTimeout(connect, 3000)
      }

      ws.onerror = (err) => {
        console.warn('WS error:', err)
        ws.close()
      }
    } catch (e) {
      console.error('WS connection failed:', e)
      reconnectRef.current = setTimeout(connect, 3000)
    }
  }, [onTransaction])

  useEffect(() => {
    mountedRef.current = true
    connect()
    return () => {
      mountedRef.current = false
      if (pingRef.current) clearInterval(pingRef.current)
      if (reconnectRef.current) clearTimeout(reconnectRef.current)
      if (wsRef.current) wsRef.current.close()
    }
  }, [connect])

  return { connected }
}
