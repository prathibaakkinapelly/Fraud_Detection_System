import StatCards from './StatCards'
import LiveChart from './LiveChart'
import TransactionFeed from './TransactionFeed'
import FraudAlerts from './FraudAlerts'

export default function Dashboard({ transactions, stats, connected }) {
  // Derive alerts from transaction list (HIGH RISK ones)
  const alerts = transactions.filter((tx) => tx.status === 'HIGH RISK').slice(0, 30)

  return (
    <main className="dashboard">
      {/* Row 1: Stat cards */}
      <StatCards stats={stats} />

      {/* Row 2: Live chart + mini alerts */}
      <div className="middle-grid">
        <div className="card">
          <div className="card-header">
            <span className="card-title">📈 Live Fraud Score Timeline</span>
            <span className="text-muted">{transactions.length} data points</span>
          </div>
          <LiveChart transactions={[...transactions].reverse()} />
        </div>

        <div className="card">
          <div className="card-header">
            <span className="card-title">
              🚨 Alert Stream
            </span>
            <span className={`count-badge alert-count-badge`}>{alerts.length}</span>
          </div>
          <div className="card-body" style={{ padding: '0.75rem' }}>
            <FraudAlerts alerts={alerts} />
          </div>
        </div>
      </div>

      {/* Row 3: Transaction feed */}
      <div className="card" style={{ minHeight: 0 }}>
        <div className="card-header">
          <span className="card-title">💳 Live Transaction Feed</span>
          <div className="flex items-center gap-2">
            <span className="count-badge">{transactions.length} total</span>
          </div>
        </div>
        <div className="card-body" style={{ padding: '0.75rem 1rem' }}>
          <TransactionFeed transactions={transactions} />
        </div>
      </div>
    </main>
  )
}
