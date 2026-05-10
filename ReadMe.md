# Real-Time Fraud Detection System — Implementation Plan

A full-stack, real-time fraud detection system built with FastAPI (Python), ML (scikit-learn), MongoDB, React, and Chart.js.

---

## Architecture Overview

```
Transaction Generator (Python script)
        ↓ POST /transactions
Backend API (FastAPI)
        ↓ scores every transaction
ML Engine (Rule-based → Random Forest → Isolation Forest)
        ↓ persists results
MongoDB (transactions + alerts collections)
        ↓ WebSocket push
Frontend Dashboard (React + Chart.js + WebSocket)
        ↓ real-time alerts
Alert Panel ("⚠ Suspicious transaction detected")
```

---

## Project Structure

```
fraud_detection_system/
├── backend/
│   ├── main.py                  # FastAPI app + WebSocket server
│   ├── models/
│   │   └── fraud_model.py       # ML scoring engine
│   ├── db/
│   │   └── mongo.py             # MongoDB client + collections
│   ├── schemas/
│   │   └── transaction.py       # Pydantic models
│   ├── simulator/
│   │   └── generate.py          # Transaction stream generator
│   ├── requirements.txt
│   └── .env                     # MongoDB URI, thresholds
└── frontend/
    ├── src/
    │   ├── App.jsx
    │   ├── components/
    │   │   ├── Dashboard.jsx
    │   │   ├── TransactionFeed.jsx
    │   │   ├── FraudAlerts.jsx
    │   │   ├── LiveChart.jsx
    │   │   └── StatCards.jsx
    │   ├── hooks/
    │   │   └── useWebSocket.js
    │   └── index.css
    ├── index.html
    └── vite.config.js
```

---

## Phase 1 — Backend Foundation

### [NEW] `backend/requirements.txt`
- `fastapi`, `uvicorn[standard]`, `motor` (async MongoDB), `pydantic`, `python-dotenv`, `scikit-learn`, `numpy`, `pandas`, `websockets`

### [NEW] `backend/schemas/transaction.py`
Pydantic models:
- `TransactionIn`: `user_id`, `amount`, `location`, `time`, `transaction_type`
- `TransactionOut`: inherits `TransactionIn` + `fraud_score`, `status`, `alert`, `timestamp`

### [NEW] `backend/db/mongo.py`
- Async Motor client
- Two collections: `transactions`, `alerts`
- Helper functions: `insert_transaction`, `get_recent_transactions`, `get_alerts`

### [NEW] `backend/main.py`
- `POST /transactions` → score → store → broadcast via WebSocket
- `GET /transactions?limit=50` → last N transactions
- `GET /alerts` → fraud alerts only
- `GET /stats` → aggregated stats (total, fraud count, avg score)
- `WS /ws` → real-time push to connected frontend clients

---

## Phase 2 — ML Fraud Engine (3 Phases)

### [NEW] `backend/models/fraud_model.py`

**Phase 1 (Rule-Based MVP)**
```
amount > 10,000          → +0.4 score
21:00–05:00 (night)     → +0.2 score
location != last known  → +0.3 score
>5 transactions/10 min  → +0.3 score
Final: clamp(score, 0, 1)
```
Status mapping:
- `< 0.3`  → LOW RISK ✅
- `0.3–0.7` → MEDIUM RISK ⚠️
- `> 0.7`  → HIGH RISK 🚨

**Phase 2 (Random Forest)**
- Trained on synthetic labeled dataset (generated at startup)
- Features: `amount`, `hour`, `is_night`, `location_change`, `tx_frequency`
- Model persisted with `joblib`

**Phase 3 (Isolation Forest)**
- Unsupervised anomaly detection on top of Random Forest ensemble score

The engine will start with Phase 1 at startup and progressively use Phase 2 once 100+ transactions are recorded.

---

## Phase 3 — Transaction Simulator

### [NEW] `backend/simulator/generate.py`
- Sends synthetic transactions to `POST /transactions` every 1–3 seconds
- Mix: 80% normal, 20% fraudulent (high amount, night time, location jumps)
- Realistic cities: Mumbai, Delhi, Hyderabad, Bangalore, Chennai, Kolkata
- CLI arg `--rate` to control speed

---

## Phase 4 — Frontend Dashboard

Tech stack: **React (Vite) + Chart.js + WebSocket**

### Pages & Components

| Component | Description |
|---|---|
| `StatCards` | Total transactions, fraud detected, avg score, alert count |
| `LiveChart` | Real-time line chart of fraud scores (last 50 transactions) |
| `TransactionFeed` | Live scrolling table with color-coded risk badges |
| `FraudAlerts` | Alert panel with `⚠ Suspicious` banners, auto-dismiss |
| `Dashboard` | Main layout assembling all components |

**WebSocket hook**: auto-reconnects, appends incoming transactions to state, triggers alert animation when `status === "HIGH RISK"`

### Design
- Dark mode glassmorphism theme
- Red/orange/green risk color coding
- Animated alert banners
- Chart.js live updating line graph
- Smooth scroll feed with pulse animation on new HIGH RISK entries

---

## Phase 5 — Integration & Polish

- CORS configured on FastAPI for localhost:5173
- `.env` for `MONGO_URI` (default: `mongodb://localhost:27017`)
- WebSocket manager broadcasts to all connected clients simultaneously
- Graceful ML model upgrade mid-session (no restart needed)
- README with setup instructions

---

## Open Questions

> [!IMPORTANT]
> **Database Choice**: The plan uses **MongoDB** with Motor (async driver) since it's schema-flexible and easy to run locally. Would you prefer **PostgreSQL** instead? (Requires more setup but better for relational queries)

> [!IMPORTANT]
> **Should I install MongoDB locally**, or would you prefer a **MongoDB Atlas** (cloud free tier) connection string? If Atlas, please share the URI after I scaffold the project.

> [!NOTE]
> The ML model starts as rule-based (no training needed) and automatically upgrades to Random Forest once enough data is collected — so the dashboard works immediately on first run.

---

## Verification Plan

### Automated
1. Start MongoDB → `mongod`
2. Start backend → `uvicorn main:app --reload`
3. Start simulator → `python simulator/generate.py`
4. Start frontend → `npm run dev`
5. Use browser subagent to capture live dashboard screenshot

### Manual Verification
- Confirm WebSocket messages received in browser DevTools
- Trigger a high-amount transaction and verify alert appears
- Verify MongoDB collections have data via `mongosh`
