# Grand Vista Hotel — ML-Based Booking System

## Quick Start

### 1. Install Python dependencies
```bash
pip install -r requirements.txt
```

### 2. Run the server
```bash
python app.py
```

### 3. Open in browser
```
http://localhost:5000
```

---

## Default Accounts

| Role  | Email               | Password  |
|-------|---------------------|-----------|
| Admin | admin@hotel.com     | admin123  |
| Staff | staff@hotel.com     | staff123  |
| Guest | guest@hotel.com     | guest123  |

---

## Project Structure

```
grand_vista_hotel/
├── app.py                  ← Flask entry point (run this)
├── requirements.txt
├── ml/
│   ├── predictor.py        ← ML predict() function
│   ├── model.pkl           ← Trained Random Forest
│   ├── le_room.pkl         ← Room type encoder
│   ├── le_season.pkl       ← Season encoder
│   └── features.pkl        ← Feature order
├── models/
│   └── models.py           ← SQLAlchemy models (User, Room, Booking)
├── routes/
│   ├── auth.py             ← /api/auth/*
│   ├── rooms.py            ← /api/rooms/*
│   ├── bookings.py         ← /api/bookings/*
│   └── admin.py            ← /api/admin/*
└── static_build/           ← React frontend (pre-built)
```

---

## ML Model Details

- **Algorithm:** Random Forest Classifier
- **Dataset:** Hotel Booking Demand (119,390 bookings)
- **Accuracy:** 77.9%
- **Output:** Risk score 0–100 → LOW / MEDIUM / HIGH

**Top prediction features:**
1. Payment type (48%) — pay-at-hotel = higher risk
2. Lead time (19%) — further in advance = higher risk
3. Past cancellations (12%)
4. Special requests (10%) — more requests = lower risk

---

## Booking Flow

```
Guest submits booking
        │
        ▼
   ML Model scores (0-100)
        │
   ┌────┴────┐
   │         │
LOW/MED     HIGH
   │         │
Auto-confirm  Hold → Staff alerted
              │
         Staff reviews
         ┌───┼───┐
      Approve  Prepay  Reject
         │       │       │
      Confirm  Guest   Cancel
              pays
```

---

## API Endpoints

| Method | Endpoint                        | Access       |
|--------|---------------------------------|--------------|
| POST   | /api/auth/register              | Public       |
| POST   | /api/auth/login                 | Public       |
| GET    | /api/rooms/available            | Public       |
| POST   | /api/bookings                   | Guest        |
| GET    | /api/bookings                   | Guest/Staff  |
| POST   | /api/bookings/:id/review        | Staff/Admin  |
| GET    | /api/bookings/alerts            | Staff/Admin  |
| GET    | /api/admin/reports/summary      | Staff/Admin  |
| PUT    | /api/admin/config               | Admin        |
| GET    | /api/admin/users                | Admin        |
