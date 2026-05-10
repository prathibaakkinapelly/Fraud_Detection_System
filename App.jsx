import { useState, useCallback, useRef, useEffect } from 'react'
import { useWebSocket } from './hooks/useWebSocket'
import Dashboard from './components/Dashboard'

const MAX_TRANSACTIONS = 200
const API_BASE = 'http://localhost:8000'

const DEFAULT_STATS = {
  total_transactions: 0,
  fraud_count: 0,
  medium_risk_count: 0,
  low_risk_count: 0,
  avg_fraud_score: 0,
  alert_rate: 0,
}

// ─── Toast system ──────────────────────────────────────────────────────────────
function ToastContainer({ toasts, onDismiss }) {
  return (
    <div className="toast-container">
      {toasts.map((t) => (
        <div key={t.id} className={`toast ${t.fading ? 'fade-out' : ''}`}>
          <span className="toast-icon">🚨</span>
          <div className="toast-body">
            <div className="toast-title">⚠ Suspicious Transaction Detected</div>
            <div className="toast-desc">
              User #{t.user_id} · ₹{Number(t.amount).toLocaleString('en-IN', { maximumFractionDigits: 0 })} · {t.location}
              <br />
              Score: <span className="toast-score">{(t.fraud_score * 100).toFixed(0)}%</span>
            </div>
          </div>
        </div>
      ))}
    </div>
  )
}

export default function App() {
  const [transactions, setTransactions] = useState([])
  const [stats, setStats] = useState(DEFAULT_STATS)
  const [toasts, setToasts] = useState([])
  const toastIdRef = useRef(0)

  // Fetch stats from API periodically
  const fetchStats = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/stats`)
      if (res.ok) {
        const data = await res.json()
        setStats(data)
      }
    } catch (_) {}
  }, [])

  useEffect(() => {
    fetchStats()
    const interval = setInterval(fetchStats, 5000)
    return () => clearInterval(interval)
  }, [fetchStats])

  // Handle incoming transactions from WebSocket
  const handleTransaction = useCallback((tx, isHistory = false) => {
    setTransactions((prev) => {
      // Avoid duplicates by id
      if (tx.id && prev.some((t) => t.id === tx.id)) return prev
      const next = isHistory ? [...prev, tx] : [tx, ...prev]
      return next.slice(0, MAX_TRANSACTIONS)
    })

    // Show toast for HIGH RISK (new only)
    if (!isHistory && tx.status === 'HIGH RISK') {
      const id = ++toastIdRef.current
      setToasts((prev) => [...prev, { ...tx, id, fading: false }])
      // Start fade-out after 3.5s, remove after 4s
      setTimeout(() => {
        setToasts((prev) => prev.map((t) => (t.id === id ? { ...t, fading: true } : t)))
      }, 3500)
      setTimeout(() => {
        setToasts((prev) => prev.filter((t) => t.id !== id))
      }, 4000)
    }
  }, [])

  const { connected } = useWebSocket(handleTransaction)

  return (
    <div className="app-wrapper">
      {/* ── Header ─────────────────────────────────────────── */}
      <header className="header">
        <div className="header-brand">
          <div className="header-logo">🛡️</div>
          <span className="header-title">FraudGuard</span>
        </div>

        <div className="header-right">
          <span className="ws-status-text">
            {connected ? 'ws://localhost:8000' : 'Reconnecting…'}
          </span>
          <div className={`live-badge ${connected ? '' : 'disconnected-badge'}`}>
            <div className="live-dot" />
            {connected ? 'LIVE' : 'OFFLINE'}
          </div>
        </div>
      </header>

      {/* ── Dashboard ──────────────────────────────────────── */}
      <Dashboard
        transactions={transactions}
        stats={stats}
        connected={connected}
      />

      {/* ── Toast alerts ───────────────────────────────────── */}
      <ToastContainer toasts={toasts} />
    </div>
  )
}
