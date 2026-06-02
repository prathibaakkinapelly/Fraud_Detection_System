"""
Fraud Detection ML Engine
=========================
Phase 1: Rule-Based scoring (instant, no training needed)
Phase 2: Random Forest classifier (auto-activates after 100 transactions)
Phase 3: Isolation Forest anomaly detection layer

The engine seamlessly transitions between phases without restart.
"""

import os
import numpy as np
import pandas as pd
import joblib
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

FRAUD_THRESHOLD = float(os.getenv("FRAUD_THRESHOLD", 0.7))
MEDIUM_THRESHOLD = float(os.getenv("MEDIUM_THRESHOLD", 0.3))

MODEL_PATH = Path(__file__).parent / "saved_model.pkl"
ISO_MODEL_PATH = Path(__file__).parent / "iso_model.pkl"

# Indian metro cities for location change detection
CITIES = [
    "Mumbai", "Delhi", "Hyderabad", "Bangalore", "Chennai",
    "Kolkata", "Pune", "Ahmedabad", "Jaipur", "Lucknow",
    "Surat", "Chandigarh", "Bhopal", "Patna", "Nagpur"
]

# Global model state
_rf_model = None
_iso_model = None
_training_buffer: list[dict] = []
_phase = 1  # 1 = rules, 2 = RF, 3 = RF + Isolation Forest


def _parse_hour(time_str: str) -> int:
    """Parse 'HH:MM' string into hour integer."""
    try:
        return int(time_str.split(":")[0])
    except Exception:
        return datetime.utcnow().hour


def _is_night(hour: int) -> bool:
    return hour >= 21 or hour <= 5


def _extract_features(
    amount: float,
    hour: int,
    location_changed: bool,
    tx_frequency: int,
    transaction_type: str
) -> np.ndarray:
    """Convert raw inputs to a feature vector for ML models."""
    is_night_flag = int(_is_night(hour))
    loc_change_flag = int(location_changed)
    is_withdrawal = int(transaction_type == "withdrawal")
    high_amount = int(amount > 10000)
    very_high_amount = int(amount > 50000)
    freq_flag = int(tx_frequency > 5)

    return np.array([[
        amount,
        hour,
        is_night_flag,
        loc_change_flag,
        tx_frequency,
        is_withdrawal,
        high_amount,
        very_high_amount,
        freq_flag,
    ]])


def _rule_based_score(
    amount: float,
    hour: int,
    location_changed: bool,
    tx_frequency: int,
    transaction_type: str
) -> tuple[float, list[str]]:
    """Phase 1: Rule-based heuristic scoring."""
    score = 0.0
    flags = []

    if amount > 50000:
        score += 0.5
        flags.append("Extremely high amount (>₹50K)")
    elif amount > 10000:
        score += 0.3
        flags.append("High amount (>₹10K)")

    if _is_night(hour):
        score += 0.2
        flags.append("Night transaction (9PM–5AM)")

    if location_changed:
        score += 0.25
        flags.append("Location change detected")

    if tx_frequency > 10:
        score += 0.4
        flags.append(f"Very high frequency ({tx_frequency} tx/10min)")
    elif tx_frequency > 5:
        score += 0.2
        flags.append(f"High frequency ({tx_frequency} tx/10min)")

    if transaction_type == "withdrawal" and amount > 5000:
        score += 0.1
        flags.append("Large cash withdrawal")

    return min(score, 1.0), flags


def _generate_synthetic_training_data(n_samples: int = 500) -> pd.DataFrame:
    """Generate synthetic labeled dataset for RF training."""
    np.random.seed(42)
    rows = []

    for _ in range(n_samples):
        is_fraud = np.random.random() < 0.2  # 20% fraud rate
        if is_fraud:
            amount = np.random.choice([
                np.random.uniform(10000, 100000),
                np.random.uniform(100, 500),  # micro-fraud
            ])
            hour = np.random.choice([0, 1, 2, 3, 4, 22, 23])
            location_changed = np.random.random() < 0.8
            tx_frequency = np.random.randint(6, 20)
            tx_type = np.random.choice(["withdrawal", "transfer"], p=[0.6, 0.4])
        else:
            amount = np.random.uniform(100, 8000)
            hour = np.random.randint(8, 20)
            location_changed = np.random.random() < 0.1
            tx_frequency = np.random.randint(1, 4)
            tx_type = np.random.choice(["transfer", "purchase"], p=[0.5, 0.5])

        rows.append({
            "amount": amount,
            "hour": hour,
            "is_night": int(_is_night(hour)),
            "location_changed": int(location_changed),
            "tx_frequency": tx_frequency,
            "is_withdrawal": int(tx_type == "withdrawal"),
            "high_amount": int(amount > 10000),
            "very_high_amount": int(amount > 50000),
            "freq_flag": int(tx_frequency > 5),
            "label": int(is_fraud),
        })

    return pd.DataFrame(rows)


def _train_random_forest():
    """Train (or load) Random Forest model."""
    global _rf_model

    from sklearn.ensemble import RandomForestClassifier
    from sklearn.model_selection import train_test_split

    if MODEL_PATH.exists():
        _rf_model = joblib.load(MODEL_PATH)
        print("[MODEL] Loaded existing Random Forest model")
        return

    print("[TRAINING] Training Random Forest model on synthetic data...")
    df = _generate_synthetic_training_data(1000)
    features = ["amount", "hour", "is_night", "location_changed", "tx_frequency",
                 "is_withdrawal", "high_amount", "very_high_amount", "freq_flag"]
    X = df[features].values
    y = df["label"].values

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    clf = RandomForestClassifier(n_estimators=100, random_state=42, class_weight="balanced")
    clf.fit(X_train, y_train)

    acc = clf.score(X_test, y_test)
    print(f"[OK] Random Forest trained -- Accuracy: {acc:.2%}")
    joblib.dump(clf, MODEL_PATH)
    _rf_model = clf


def _train_isolation_forest():
    """Train Isolation Forest for anomaly detection."""
    global _iso_model

    from sklearn.ensemble import IsolationForest

    if ISO_MODEL_PATH.exists():
        _iso_model = joblib.load(ISO_MODEL_PATH)
        print("[MODEL] Loaded existing Isolation Forest model")
        return

    print("[TRAINING] Training Isolation Forest...")
    df = _generate_synthetic_training_data(2000)
    features = ["amount", "hour", "is_night", "location_changed", "tx_frequency",
                 "is_withdrawal", "high_amount", "very_high_amount", "freq_flag"]
    # Train only on normal transactions
    X_normal = df[df["label"] == 0][features].values
    iso = IsolationForest(contamination=0.15, random_state=42, n_estimators=100)
    iso.fit(X_normal)
    joblib.dump(iso, ISO_MODEL_PATH)
    _iso_model = iso
    print("[OK] Isolation Forest trained")


def initialize_models():
    """Pre-train both models at startup so they're ready immediately."""
    global _phase
    _train_random_forest()
    _train_isolation_forest()
    _phase = 3
    print(f"[READY] Fraud Engine ready -- Phase {_phase} (RF + Isolation Forest)")


def _classify_status(score: float) -> str:
    if score >= FRAUD_THRESHOLD:
        return "HIGH RISK"
    elif score >= MEDIUM_THRESHOLD:
        return "MEDIUM RISK"
    return "LOW RISK"


def score_transaction(
    amount: float,
    time_str: str,
    location: str,
    last_location: str | None,
    tx_frequency: int,
    transaction_type: str,
) -> dict:
    """
    Main scoring function. Returns fraud_score, status, alert flag, and flags list.
    """
    global _phase

    hour = _parse_hour(time_str)
    location_changed = (last_location is not None) and (location != last_location)
    features = _extract_features(amount, hour, location_changed, tx_frequency, transaction_type)

    rule_score, flags = _rule_based_score(amount, hour, location_changed, tx_frequency, transaction_type)

    final_score = rule_score  # default: rule-based

    if _phase >= 2 and _rf_model is not None:
        # RF gives probability of fraud
        rf_prob = _rf_model.predict_proba(features)[0][1]
        # Blend: 40% rules, 60% RF
        final_score = 0.4 * rule_score + 0.6 * rf_prob

    if _phase >= 3 and _iso_model is not None:
        # Isolation Forest: -1 = anomaly, 1 = normal
        iso_pred = _iso_model.predict(features)[0]
        iso_score_raw = -_iso_model.score_samples(features)[0]  # higher = more anomalous
        iso_contribution = min(max(iso_score_raw * 0.3, 0), 0.3)

        if iso_pred == -1:
            # Anomaly detected — boost score
            final_score = min(final_score + iso_contribution, 1.0)
            if "Anomaly detected (Isolation Forest)" not in flags:
                flags.append("Anomaly detected (Isolation Forest)")

    final_score = round(min(final_score, 1.0), 4)
    status = _classify_status(final_score)
    alert = status == "HIGH RISK"

    if location_changed and last_location:
        # Update flag to be specific
        flags = [f for f in flags if "Location change" not in f]
        flags.append(f"Location changed: {last_location} → {location}")

    return {
        "fraud_score": final_score,
        "status": status,
        "alert": alert,
        "flags": flags,
        "phase_used": _phase,
    }
