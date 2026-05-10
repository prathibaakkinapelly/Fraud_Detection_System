"""
Transaction Stream Simulator
=============================
Generates realistic banking transactions and POSTs them to the FastAPI backend.
Mix: ~80% normal, ~20% fraudulent

Usage:
    python generate.py              # default: 1 tx/sec
    python generate.py --rate 2     # 2 second delay between transactions
    python generate.py --count 200  # stop after 200 transactions
"""

import argparse
import random
import time
import json
import urllib.request
import urllib.error
from datetime import datetime

API_URL = "http://localhost:8000/transactions"

CITIES = [
    "Mumbai", "Delhi", "Hyderabad", "Bangalore", "Chennai",
    "Kolkata", "Pune", "Ahmedabad", "Jaipur", "Lucknow",
    "Surat", "Chandigarh", "Bhopal", "Patna", "Nagpur",
]

TRANSACTION_TYPES = ["transfer", "purchase", "withdrawal"]

USER_PROFILES = {
    101: {"home_city": "Hyderabad", "typical_amount": (500, 5000)},
    102: {"home_city": "Mumbai",    "typical_amount": (1000, 8000)},
    103: {"home_city": "Delhi",     "typical_amount": (200, 3000)},
    104: {"home_city": "Bangalore", "typical_amount": (500, 6000)},
    105: {"home_city": "Chennai",   "typical_amount": (300, 4000)},
    106: {"home_city": "Kolkata",   "typical_amount": (400, 3500)},
    107: {"home_city": "Pune",      "typical_amount": (600, 7000)},
    108: {"home_city": "Jaipur",    "typical_amount": (250, 2500)},
}


def random_time(is_fraud: bool) -> str:
    """Return a random time string, biased toward night for fraud."""
    if is_fraud:
        # Night hours: 21–23 or 0–5
        hour = random.choice(list(range(21, 24)) + list(range(0, 6)))
    else:
        # Normal business hours: 8–20
        hour = random.randint(8, 20)
    minute = random.randint(0, 59)
    return f"{hour:02d}:{minute:02d}"


def generate_normal_transaction() -> dict:
    user_id = random.choice(list(USER_PROFILES.keys()))
    profile = USER_PROFILES[user_id]
    lo, hi = profile["typical_amount"]
    amount = round(random.uniform(lo, hi), 2)
    location = profile["home_city"] if random.random() < 0.85 else random.choice(CITIES)
    return {
        "user_id": user_id,
        "amount": amount,
        "location": location,
        "time": random_time(is_fraud=False),
        "transaction_type": random.choices(
            TRANSACTION_TYPES, weights=[0.5, 0.4, 0.1]
        )[0],
    }


def generate_fraudulent_transaction() -> dict:
    user_id = random.choice(list(USER_PROFILES.keys()))
    fraud_type = random.choice([
        "high_amount", "location_jump", "night_withdrawal", "rapid_fire"
    ])

    if fraud_type == "high_amount":
        amount = round(random.uniform(15000, 100000), 2)
        location = USER_PROFILES[user_id]["home_city"]
        tx_type = random.choice(["transfer", "withdrawal"])
    elif fraud_type == "location_jump":
        amount = round(random.uniform(2000, 20000), 2)
        # Pick a city far from home
        home = USER_PROFILES[user_id]["home_city"]
        foreign_cities = [c for c in CITIES if c != home]
        location = random.choice(foreign_cities)
        tx_type = "withdrawal"
    elif fraud_type == "night_withdrawal":
        amount = round(random.uniform(5000, 30000), 2)
        location = random.choice(CITIES)
        tx_type = "withdrawal"
    else:  # rapid_fire — small amounts but many
        amount = round(random.uniform(100, 1000), 2)
        location = random.choice(CITIES)
        tx_type = "transfer"

    return {
        "user_id": user_id,
        "amount": amount,
        "location": location,
        "time": random_time(is_fraud=True),
        "transaction_type": tx_type,
    }


def post_transaction(tx: dict) -> dict | None:
    """POST transaction to FastAPI and return response JSON."""
    data = json.dumps(tx).encode("utf-8")
    req = urllib.request.Request(
        API_URL,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.URLError as e:
        print(f"  ❌ Connection error: {e.reason} — Is the backend running?")
        return None
    except Exception as e:
        print(f"  ❌ Error: {e}")
        return None


def format_result(tx: dict, result: dict) -> str:
    score = result.get("fraud_score", 0)
    status = result.get("status", "UNKNOWN")
    flags = result.get("flags", [])

    # Color indicators
    if status == "HIGH RISK":
        indicator = "[HIGH]"
    elif status == "MEDIUM RISK":
        indicator = "[MED] "
    else:
        indicator = "[OK]  "

    flags_str = ", ".join(flags) if flags else "None"
    return (
        f"{indicator} User {tx['user_id']:>3} | ₹{tx['amount']:>10,.2f} | "
        f"{tx['location']:<12} | {tx['time']} | {status:<12} | Score: {score:.3f} | "
        f"Flags: {flags_str}"
    )


def run_simulator(rate: float = 1.0, count: int | None = None):
    print("=" * 90)
    print("  💳 FRAUD DETECTION SYSTEM — Transaction Simulator")
    print(f"  Rate: 1 transaction every {rate}s | Target API: {API_URL}")
    if count:
        print(f"  Running for {count} transactions")
    print("=" * 90)
    print(f"{'Indicator':<4} {'Info'}")
    print("-" * 90)

    sent = 0
    try:
        while count is None or sent < count:
            is_fraud = random.random() < 0.20  # 20% fraud rate
            tx = generate_fraudulent_transaction() if is_fraud else generate_normal_transaction()

            result = post_transaction(tx)
            if result:
                print(format_result(tx, result))
                sent += 1
            else:
                print("  Retrying in 3 seconds...")
                time.sleep(3)
                continue

            time.sleep(rate)

    except KeyboardInterrupt:
        print(f"\n\n⛔ Simulator stopped. Sent {sent} transactions.")


def main():
    parser = argparse.ArgumentParser(description="Fraud Detection Transaction Simulator")
    parser.add_argument("--rate", type=float, default=1.0,
                        help="Delay in seconds between transactions (default: 1.0)")
    parser.add_argument("--count", type=int, default=None,
                        help="Total transactions to send (default: infinite)")
    args = parser.parse_args()
    run_simulator(rate=args.rate, count=args.count)


if __name__ == "__main__":
    main()
