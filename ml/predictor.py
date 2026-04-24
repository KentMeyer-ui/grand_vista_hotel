"""
Hotel No-Show Predictor
-----------------------
Load once, call predict() for every new booking.
Returns a risk score (0-100) and risk level (LOW / MEDIUM / HIGH).
"""

import os
import joblib
import numpy as np

# Paths (relative to this file)
BASE = os.path.dirname(__file__)
_model    = joblib.load(os.path.join(BASE, 'model.pkl'))
_le_room  = joblib.load(os.path.join(BASE, 'le_room.pkl'))
_le_season = joblib.load(os.path.join(BASE, 'le_season.pkl'))
_features  = joblib.load(os.path.join(BASE, 'features.pkl'))

# Risk thresholds (configurable by Admin in the real system)
LOW_THRESHOLD    = 40   # 0–39  → LOW
MEDIUM_THRESHOLD = 70   # 40–69 → MEDIUM
                        # 70–100 → HIGH

MONTH_TO_SEASON = {
    1: 'Winter', 2: 'Winter', 12: 'Winter',
    3: 'Spring', 4: 'Spring', 5: 'Spring',
    6: 'Summer', 7: 'Summer', 8: 'Summer',
    9: 'Fall',  10: 'Fall',  11: 'Fall',
}


def _encode_room(room_type: str) -> int:
    """Encode room type letter. Unknown types default to 'A'."""
    room_type = room_type.upper()
    if room_type not in _le_room.classes_:
        room_type = 'A'
    return int(_le_room.transform([room_type])[0])


def _encode_season(month: int) -> int:
    season = MONTH_TO_SEASON.get(month, 'Summer')
    return int(_le_season.transform([season])[0])


def predict(
    lead_time: int,
    pay_now: bool,
    room_type: str,
    arrival_month: int,
    arrival_day: int,
    total_nights: int,
    is_repeated_guest: bool,
    previous_cancellations: int,
    adults: int,
    special_requests: int,
) -> dict:
    """
    Parameters
    ----------
    lead_time              : days between booking and arrival
    pay_now                : True = paid upfront, False = pay at hotel
    room_type              : single letter e.g. 'A', 'B', 'C' …
    arrival_month          : 1–12
    arrival_day            : 1–31 (used to approximate day-of-week)
    total_nights           : total length of stay
    is_repeated_guest      : True/False
    previous_cancellations : number of past cancellations
    adults                 : number of adults
    special_requests       : number of special requests

    Returns
    -------
    {
        'score': int (0–100),
        'level': 'LOW' | 'MEDIUM' | 'HIGH',
        'probability': float (0.0–1.0)
    }
    """
    row = {
        'lead_time':                 lead_time,
        'pay_now':                   int(pay_now),
        'reserved_room_type':        _encode_room(room_type),
        'arrival_dow':               arrival_day % 7,
        'total_nights':              total_nights,
        'is_repeated_guest':         int(is_repeated_guest),
        'season':                    _encode_season(arrival_month),
        'previous_cancellations':    previous_cancellations,
        'adults':                    adults,
        'total_of_special_requests': special_requests,
    }

    import pandas as pd
    X = pd.DataFrame([row])[_features]
    prob = float(_model.predict_proba(X)[0][1])   # probability of no-show
    score = int(round(prob * 100))

    if score < LOW_THRESHOLD:
        level = 'LOW'
    elif score < MEDIUM_THRESHOLD:
        level = 'MEDIUM'
    else:
        level = 'HIGH'

    return {
        'score': score,
        'level': level,
        'probability': prob,
    }


# ── Quick self-test ───────────────────────────────────────────────────────────
if __name__ == '__main__':
    # LOW risk: repeat guest, pay now, short lead time
    low = predict(
        lead_time=2, pay_now=True, room_type='A',
        arrival_month=7, arrival_day=15, total_nights=3,
        is_repeated_guest=True, previous_cancellations=0,
        adults=2, special_requests=2,
    )
    print(f"LOW  risk booking  → {low}")

    # HIGH risk: pay at hotel, long lead time, history of cancellations
    high = predict(
        lead_time=180, pay_now=False, room_type='D',
        arrival_month=1, arrival_day=3, total_nights=1,
        is_repeated_guest=False, previous_cancellations=3,
        adults=1, special_requests=0,
    )
    print(f"HIGH risk booking  → {high}")
