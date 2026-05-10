import { useEffect, useRef } from 'react'
import { format } from 'date-fns'

function RiskBadge({ status }) {
  const cls = status === 'HIGH RISK' ? 'high' : status === 'MEDIUM RISK' ? 'medium' : 'low'
  const icon = status === 'HIGH RISK' ? '🚨' : status === 'MEDIUM RISK' ? '⚠️' : '✅'
  return (
    <span className={`risk-badge ${cls}`}>
      {icon} {status}
    </span>
  )
}

function ScoreBar({ score }) {
  const pct = Math.round(score * 100)
  let color = '#22c55e'
  if (score >= 0.7) color = '#ef4444'
  else if (score >= 0.3) color = '#f59e0b'
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
      <div className="score-bar-wrap">
        <div className="score-bar" style={{ width: pct + '%', background: color }} />
      </div>
      <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.72rem', color: color, fontWeight: 600 }}>
        {pct}%
      </span>
    </div>
  )
}

export default function TransactionFeed({ transactions }) {
  const feedRef = useRef(null)
  const prevLen = useRef(0)

  // Auto-scroll to top when new transaction comes in
  useEffect(() => {
    if (transactions.length > prevLen.current && feedRef.current) {
      feedRef.current.scrollTo({ top: 0, behavior: 'smooth' })
    }
    prevLen.current = transactions.length
  }, [transactions.length])

  if (transactions.length === 0) {
    return (
      <div className="empty-state" style={{ minHeight: 200 }}>
        <div className="empty-state-icon">💳</div>
        <p>Waiting for transactions…</p>
        <p className="text-muted">Run the simulator to stream live data</p>
      </div>
    )
  }

  return (
    <>
      <div className="tx-table-header">
        <span>USER</span>
        <span>AMOUNT</span>
        <span>LOCATION</span>
        <span>TIME</span>
        <span>STATUS</span>
        <span>SCORE</span>
      </div>
      <div className="tx-feed" ref={feedRef}>
        {transactions.map((tx, i) => {
          const isHigh = tx.status === 'HIGH RISK'
          return (
            <div
              key={tx.id || `${tx.user_id}-${i}`}
              className={`tx-row ${isHigh ? 'high-risk' : ''} ${i === 0 ? 'new-entry' : ''}`}
            >
              <span className="tx-cell user-id">#{tx.user_id}</span>
              <span className="tx-cell amount">₹{Number(tx.amount).toLocaleString('en-IN', { maximumFractionDigits: 0 })}</span>
              <span className="tx-cell location">{tx.location}</span>
              <span className="tx-cell mono">{tx.time}</span>
              <RiskBadge status={tx.status} />
              <ScoreBar score={tx.fraud_score} />
            </div>
          )
        })}
      </div>
    </>
  )
}
