export default function StatCards({ stats }) {
  const cards = [
    {
      icon: '💳',
      label: 'Total Transactions',
      value: stats.total_transactions.toLocaleString(),
      sub: 'Live count',
      grad: 'linear-gradient(90deg, #6366f1, #818cf8)',
      iconBg: 'rgba(99,102,241,0.15)',
    },
    {
      icon: '🚨',
      label: 'Fraud Detected',
      value: stats.fraud_count.toLocaleString(),
      sub: `${stats.alert_rate}% alert rate`,
      grad: 'linear-gradient(90deg, #ef4444, #f87171)',
      iconBg: 'rgba(239,68,68,0.12)',
      valueColor: '#fca5a5',
    },
    {
      icon: '⚠️',
      label: 'Medium Risk',
      value: stats.medium_risk_count.toLocaleString(),
      sub: 'Needs review',
      grad: 'linear-gradient(90deg, #f59e0b, #fbbf24)',
      iconBg: 'rgba(245,158,11,0.12)',
      valueColor: '#fcd34d',
    },
    {
      icon: '📊',
      label: 'Avg Fraud Score',
      value: (stats.avg_fraud_score * 100).toFixed(1) + '%',
      sub: score_label(stats.avg_fraud_score),
      grad: 'linear-gradient(90deg, #22c55e, #4ade80)',
      iconBg: 'rgba(34,197,94,0.12)',
      valueColor: score_color(stats.avg_fraud_score),
    },
  ]

  return (
    <div className="stat-grid">
      {cards.map((c, i) => (
        <div
          key={i}
          className="stat-card"
          style={{ '--accent-grad': c.grad }}
        >
          <div
            className="stat-icon"
            style={{ background: c.iconBg }}
          >
            {c.icon}
          </div>
          <div
            className="stat-value"
            style={{ color: c.valueColor || 'var(--text-primary)' }}
          >
            {c.value}
          </div>
          <div className="stat-label">{c.label}</div>
          <div className="stat-sub">{c.sub}</div>
        </div>
      ))}
    </div>
  )
}

function score_color(s) {
  if (s >= 0.7) return '#fca5a5'
  if (s >= 0.3) return '#fcd34d'
  return '#86efac'
}
function score_label(s) {
  if (s >= 0.7) return 'High risk average'
  if (s >= 0.3) return 'Medium risk average'
  return 'Healthy baseline'
}
