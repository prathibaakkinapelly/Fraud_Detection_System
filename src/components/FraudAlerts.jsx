export default function FraudAlerts({ alerts }) {
  if (alerts.length === 0) {
    return (
      <div className="empty-state" style={{ minHeight: 200 }}>
        <div className="empty-state-icon">🛡️</div>
        <p>No alerts yet</p>
        <p className="text-muted">HIGH RISK transactions will appear here</p>
      </div>
    )
  }

  return (
    <div className="alert-feed">
      {alerts.map((alert, i) => (
        <div key={alert.id || i} className="alert-item">
          <div className="alert-header">
            <div className="alert-title">
              <span>⚠️</span>
              <span>Suspicious Transaction</span>
            </div>
            <span className="alert-score">{(alert.fraud_score * 100).toFixed(0)}%</span>
          </div>
          <div className="alert-detail">
            <span>👤 User #{alert.user_id}</span>
            <span>💰 ₹{Number(alert.amount).toLocaleString('en-IN', { maximumFractionDigits: 0 })}</span>
            <span>📍 {alert.location}</span>
          </div>
          {alert.flags && alert.flags.length > 0 && (
            <div className="alert-flags">
              {alert.flags.map((f, j) => (
                <span key={j} className="alert-flag">{f}</span>
              ))}
            </div>
          )}
          <div className="alert-time">
            {alert.timestamp
              ? new Date(alert.timestamp).toLocaleTimeString('en-IN')
              : 'Just now'}
          </div>
        </div>
      ))}
    </div>
  )
}
