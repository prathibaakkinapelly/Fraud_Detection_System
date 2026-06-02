"""
FastAPI Backend — Real-Time Fraud Detection System
===================================================
Endpoints:
  POST /transactions        — Score and store a transaction
  GET  /transactions        — Fetch recent transactions
  GET  /alerts              — Fetch HIGH RISK alerts
  GET  /stats               — Aggregated fraud statistics
  WS   /ws                  — WebSocket real-time feed
"""

import os
import json
from datetime import datetime, timezone
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from dotenv import load_dotenv

from schemas.transaction import TransactionIn, TransactionOut, StatsOut
from db.mongo import (
    connect_db, close_db,
    insert_transaction, insert_alert,
    get_recent_transactions, get_alerts, get_stats,
    get_user_recent_tx_count, get_user_last_location,
)
from models.fraud_model import score_transaction, initialize_models

load_dotenv()


# ─────────────────────────────────────────────
#  WebSocket Connection Manager
# ─────────────────────────────────────────────

class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, ws: WebSocket):
        await ws.accept()
        self.active_connections.append(ws)
        print(f"[WS] Connected. Total clients: {len(self.active_connections)}")

    def disconnect(self, ws: WebSocket):
        if ws in self.active_connections:
            self.active_connections.remove(ws)
        print(f"[WS] Disconnected. Total clients: {len(self.active_connections)}")

    async def broadcast(self, data: dict):
        """Send JSON to all connected WebSocket clients."""
        message = json.dumps(data, default=str)
        dead = []
        for ws in self.active_connections:
            try:
                await ws.send_text(message)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(ws)


manager = ConnectionManager()


# ─────────────────────────────────────────────
#  App Lifecycle
# ─────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await connect_db()
    initialize_models()
    yield
    # Shutdown
    await close_db()


app = FastAPI(
    title="Fraud Detection API",
    description="Real-time fraud detection system with ML scoring",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],          # tighten in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─────────────────────────────────────────────
#  API Routes
# ─────────────────────────────────────────────

@app.get("/", tags=["Health"])
async def root():
    return {"message": "Fraud Detection API is running 🚀", "status": "ok"}


@app.get("/health", tags=["Health"])
async def health():
    return {"status": "healthy", "timestamp": datetime.now(timezone.utc)}


@app.post("/transactions", response_model=TransactionOut, tags=["Transactions"])
async def create_transaction(tx: TransactionIn):
    """
    Submit a transaction for real-time fraud scoring.
    Returns the scored transaction and broadcasts it to WebSocket clients.
    """
    try:
        # Enrich with context from DB
        tx_frequency = await get_user_recent_tx_count(tx.user_id, minutes=10)
        last_location = await get_user_last_location(tx.user_id)

        # Score the transaction
        result = score_transaction(
            amount=tx.amount,
            time_str=tx.time,
            location=tx.location,
            last_location=last_location,
            tx_frequency=tx_frequency,
            transaction_type=tx.transaction_type,
        )

        # Build the full document
        now = datetime.now(timezone.utc)
        doc = {
            "user_id": tx.user_id,
            "amount": tx.amount,
            "location": tx.location,
            "time": tx.time,
            "transaction_type": tx.transaction_type,
            "fraud_score": result["fraud_score"],
            "status": result["status"],
            "alert": result["alert"],
            "flags": result["flags"],
            "timestamp": now,
        }

        # Persist to MongoDB
        doc_id = await insert_transaction(dict(doc))
        doc["id"] = doc_id

        # If HIGH RISK → also insert into alerts collection
        if result["alert"]:
            await insert_alert({
                "transaction_id": doc_id,
                "user_id": tx.user_id,
                "amount": tx.amount,
                "location": tx.location,
                "fraud_score": result["fraud_score"],
                "flags": result["flags"],
                "timestamp": now,
            })

        # Broadcast to all WebSocket clients in real-time
        await manager.broadcast({
            "type": "transaction",
            "data": {**doc, "timestamp": now.isoformat()},
        })

        return TransactionOut(**doc)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/transactions", tags=["Transactions"])
async def list_transactions(limit: int = 50) -> list[dict]:
    """Fetch the most recent transactions (default: 50)."""
    txs = await get_recent_transactions(limit=min(limit, 200))
    # Convert datetime to ISO string for JSON serialization
    for tx in txs:
        if isinstance(tx.get("timestamp"), datetime):
            tx["timestamp"] = tx["timestamp"].isoformat()
    return txs


@app.get("/alerts", tags=["Alerts"])
async def list_alerts(limit: int = 20) -> list[dict]:
    """Fetch recent HIGH RISK fraud alerts."""
    alerts = await get_alerts(limit=min(limit, 100))
    for a in alerts:
        if isinstance(a.get("timestamp"), datetime):
            a["timestamp"] = a["timestamp"].isoformat()
    return alerts


@app.get("/stats", response_model=StatsOut, tags=["Stats"])
async def stats() -> StatsOut:
    """Return aggregated fraud statistics."""
    data = await get_stats()
    return StatsOut(**data)


# ─────────────────────────────────────────────
#  WebSocket Endpoint
# ─────────────────────────────────────────────

@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    """
    WebSocket endpoint for real-time transaction streaming.
    Connected clients receive every scored transaction instantly.
    """
    await manager.connect(ws)
    try:
        # Send recent transactions on connect so dashboard populates immediately
        recent = await get_recent_transactions(limit=20)
        for tx in recent:
            if isinstance(tx.get("timestamp"), datetime):
                tx["timestamp"] = tx["timestamp"].isoformat()
        await ws.send_text(json.dumps({"type": "history", "data": recent}, default=str))

        # Keep connection alive — listen for pings from client
        while True:
            data = await ws.receive_text()
            if data == "ping":
                await ws.send_text(json.dumps({"type": "pong"}))
    except WebSocketDisconnect:
        manager.disconnect(ws)
    except Exception as e:
        print(f"WebSocket error: {e}")
        manager.disconnect(ws)
