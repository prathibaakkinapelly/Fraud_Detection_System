from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class TransactionIn(BaseModel):
    user_id: int
    amount: float
    location: str
    time: str  # "HH:MM" format
    transaction_type: Optional[str] = "transfer"  # transfer, purchase, withdrawal

    model_config = {"json_schema_extra": {
        "example": {
            "user_id": 101,
            "amount": 5000,
            "location": "Hyderabad",
            "time": "22:30",
            "transaction_type": "transfer"
        }
    }}


class TransactionOut(BaseModel):
    id: Optional[str] = None
    user_id: int
    amount: float
    location: str
    time: str
    transaction_type: str
    fraud_score: float
    status: str         # LOW RISK / MEDIUM RISK / HIGH RISK
    alert: bool
    flags: list[str]    # human-readable reasons
    timestamp: datetime

    model_config = {"json_schema_extra": {
        "example": {
            "user_id": 101,
            "amount": 15000,
            "location": "Mumbai",
            "time": "02:15",
            "transaction_type": "withdrawal",
            "fraud_score": 0.87,
            "status": "HIGH RISK",
            "alert": True,
            "flags": ["High amount", "Night transaction", "Location change"],
            "timestamp": "2024-01-01T02:15:00"
        }
    }}


class StatsOut(BaseModel):
    total_transactions: int
    fraud_count: int
    medium_risk_count: int
    low_risk_count: int
    avg_fraud_score: float
    alert_rate: float  # percentage
