import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Filler,
  Tooltip,
  Legend,
} from 'chart.js'
import { Line } from 'react-chartjs-2'

ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, Filler, Tooltip, Legend)

const MAX_POINTS = 50

export default function LiveChart({ transactions }) {
  const recent = transactions.slice(-MAX_POINTS)

  const labels = recent.map((tx) => tx.time || '??:??')

  const fraudScores = recent.map((tx) => +(tx.fraud_score * 100).toFixed(1))

  const bgColors = recent.map((tx) => {
    if (tx.status === 'HIGH RISK') return 'rgba(239,68,68,0.8)'
    if (tx.status === 'MEDIUM RISK') return 'rgba(245,158,11,0.8)'
    return 'rgba(34,197,94,0.8)'
  })

  const data = {
    labels,
    datasets: [
      {
        label: 'Fraud Score %',
        data: fraudScores,
        borderColor: 'rgba(99,102,241,0.9)',
        backgroundColor: 'rgba(99,102,241,0.08)',
        borderWidth: 2,
        pointBackgroundColor: bgColors,
        pointBorderColor: bgColors,
        pointRadius: 5,
        pointHoverRadius: 7,
        fill: true,
        tension: 0.4,
      },
    ],
  }

  const options = {
    responsive: true,
    maintainAspectRatio: false,
    animation: { duration: 300 },
    plugins: {
      legend: { display: false },
      tooltip: {
        backgroundColor: 'rgba(13,20,36,0.95)',
        borderColor: 'rgba(255,255,255,0.1)',
        borderWidth: 1,
        titleColor: '#94a3b8',
        bodyColor: '#f1f5f9',
        padding: 10,
        callbacks: {
          label: (ctx) => {
            const tx = recent[ctx.dataIndex]
            return [
              `Score: ${ctx.raw}%`,
              `Status: ${tx?.status || 'N/A'}`,
              `Amount: ₹${tx?.amount?.toLocaleString() || '—'}`,
              `User: ${tx?.user_id || '—'}`,
            ]
          },
        },
      },
    },
    scales: {
      x: {
        ticks: {
          color: '#475569',
          font: { family: "'JetBrains Mono'", size: 10 },
          maxTicksLimit: 10,
          maxRotation: 0,
        },
        grid: { color: 'rgba(255,255,255,0.04)' },
      },
      y: {
        min: 0,
        max: 100,
        ticks: {
          color: '#475569',
          font: { family: "'JetBrains Mono'", size: 10 },
          callback: (v) => v + '%',
        },
        grid: { color: 'rgba(255,255,255,0.04)' },
      },
    },
  }

  if (transactions.length === 0) {
    return (
      <div className="chart-wrap" style={{ display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <div className="empty-state">
          <div className="empty-state-icon">📈</div>
          <p>Waiting for transactions…</p>
          <p className="text-muted">Start the simulator to see live data</p>
        </div>
      </div>
    )
  }

  return (
    <div className="chart-wrap">
      <Line data={data} options={options} />
    </div>
  )
}
