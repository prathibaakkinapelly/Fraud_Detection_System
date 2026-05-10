import os
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
from datetime import datetime
from typing import Optional

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
DB_NAME = os.getenv("DB_NAME", "fraud_detection")

client: Optional[AsyncIOMotorClient] = None
db = None


async def connect_db():
    """Initialize MongoDB connection."""
    global client, db
    client = AsyncIOMotorClient(MONGO_URI)
    db = client[DB_NAME]
    # Create indexes for fast querying
    await db.transactions.create_index("timestamp")
    await db.transactions.create_index("user_id")
    await db.transactions.create_index("status")
    await db.alerts.create_index("timestamp")
    print(f"[OK] Connected to MongoDB: {DB_NAME}")


async def close_db():
    """Close MongoDB connection."""
    global client
    if client:
        client.close()
        print("[CLOSED] MongoDB connection closed")


async def insert_transaction(tx: dict) -> str:
    """Insert a scored transaction and return its ID."""
    result = await db.transactions.insert_one(tx)
    return str(result.inserted_id)


async def insert_alert(alert: dict) -> str:
    """Insert a fraud alert."""
    result = await db.alerts.insert_one(alert)
    return str(result.inserted_id)


async def get_recent_transactions(limit: int = 50) -> list[dict]:
    """Fetch the most recent N transactions."""
    cursor = db.transactions.find().sort("timestamp", -1).limit(limit)
    transactions = []
    async for doc in cursor:
        doc["id"] = str(doc.pop("_id"))
        transactions.append(doc)
    return transactions


async def get_alerts(limit: int = 20) -> list[dict]:
    """Fetch recent HIGH RISK alerts."""
    cursor = db.alerts.find().sort("timestamp", -1).limit(limit)
    alerts = []
    async for doc in cursor:
        doc["id"] = str(doc.pop("_id"))
        alerts.append(doc)
    return alerts


async def get_stats() -> dict:
    """Aggregate fraud statistics."""
    pipeline = [
        {
            "$group": {
                "_id": None,
                "total": {"$sum": 1},
                "fraud_count": {
                    "$sum": {"$cond": [{"$eq": ["$status", "HIGH RISK"]}, 1, 0]}
                },
                "medium_count": {
                    "$sum": {"$cond": [{"$eq": ["$status", "MEDIUM RISK"]}, 1, 0]}
                },
                "low_count": {
                    "$sum": {"$cond": [{"$eq": ["$status", "LOW RISK"]}, 1, 0]}
                },
                "avg_score": {"$avg": "$fraud_score"},
            }
        }
    ]
    result = await db.transactions.aggregate(pipeline).to_list(1)
    if not result:
        return {
            "total_transactions": 0,
            "fraud_count": 0,
            "medium_risk_count": 0,
            "low_risk_count": 0,
            "avg_fraud_score": 0.0,
            "alert_rate": 0.0,
        }
    r = result[0]
    total = r["total"]
    return {
        "total_transactions": total,
        "fraud_count": r["fraud_count"],
        "medium_risk_count": r["medium_count"],
        "low_risk_count": r["low_count"],
        "avg_fraud_score": round(r["avg_score"], 4),
        "alert_rate": round((r["fraud_count"] / total) * 100, 2) if total > 0 else 0.0,
    }


async def get_user_recent_tx_count(user_id: int, minutes: int = 10) -> int:
    """Count how many transactions a user did in the last N minutes (for frequency check)."""
    from datetime import timedelta
    cutoff = datetime.utcnow() - timedelta(minutes=minutes)
    count = await db.transactions.count_documents({
        "user_id": user_id,
        "timestamp": {"$gte": cutoff}
    })
    return count


async def get_user_last_location(user_id: int) -> Optional[str]:
    """Get the most recent location for a user."""
    doc = await db.transactions.find_one(
        {"user_id": user_id},
        sort=[("timestamp", -1)]
    )
    return doc["location"] if doc else None
