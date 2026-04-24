"""
Booking routes
  POST   /api/bookings                    — guest creates a booking (triggers ML)
  GET    /api/bookings                    — list bookings (guest=own, staff=all)
  GET    /api/bookings/<id>               — booking detail
  POST   /api/bookings/<id>/cancel        — guest cancels own booking
  POST   /api/bookings/<id>/review        — staff approves / requires_prepayment / rejects
  GET    /api/bookings/alerts             — staff: all HIGH risk pending_review bookings
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'ml'))

from datetime import datetime, date
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from models.models import db, User, Room, Booking, SystemConfig
import predictor as ml

bookings_bp = Blueprint('bookings', __name__, url_prefix='/api/bookings')


def _get_current_user():
    user_id = int(get_jwt_identity())
    return User.query.get(user_id)


def _get_threshold(key, default):
    cfg = SystemConfig.query.get(key)
    return int(cfg.value) if cfg else default


def _rooms_booked_on(check_in: date, check_out: date, exclude_id=None):
    q = Booking.query.filter(
        Booking.status.in_(['confirmed', 'pending_review', 'requires_prepayment']),
        Booking.check_in  < check_out,
        Booking.check_out > check_in,
    )
    if exclude_id:
        q = q.filter(Booking.id != exclude_id)
    return {b.room_id for b in q.all()}


# ── Create booking ────────────────────────────────────────────────────────────
@bookings_bp.route('', methods=['POST'])
@jwt_required()
def create_booking():
    user = _get_current_user()
    data = request.get_json()

    # Validate required fields
    required = ['room_id', 'check_in', 'check_out', 'adults', 'pay_now']
    for f in required:
        if data.get(f) is None:
            return jsonify({'error': f'{f} is required'}), 400

    try:
        check_in  = date.fromisoformat(data['check_in'])
        check_out = date.fromisoformat(data['check_out'])
    except ValueError:
        return jsonify({'error': 'Invalid date format. Use YYYY-MM-DD'}), 400

    if check_in >= check_out:
        return jsonify({'error': 'check_out must be after check_in'}), 400

    if check_in < date.today():
        return jsonify({'error': 'check_in cannot be in the past'}), 400

    # Check room exists and is available
    room = Room.query.get(data['room_id'])
    if not room or not room.is_available:
        return jsonify({'error': 'Room not found or unavailable'}), 404

    booked_ids = _rooms_booked_on(check_in, check_out)
    if room.id in booked_ids:
        return jsonify({'error': 'Room is already booked for these dates'}), 409

    adults           = int(data['adults'])
    pay_now          = bool(data['pay_now'])
    special_requests = data.get('special_requests', '')
    num_special      = int(data.get('num_special_requests', 0))

    # Count past cancellations for this guest
    past_cancellations = Booking.query.filter_by(
        guest_id=user.id, status='cancelled'
    ).count()

    is_repeat = Booking.query.filter(
        Booking.guest_id == user.id,
        Booking.status == 'confirmed',
    ).count() > 0

    total_nights = (check_out - check_in).days
    lead_time    = (check_in - date.today()).days

    # ── Call ML model ─────────────────────────────────────────────────────────
    ml_result = ml.predict(
        lead_time              = lead_time,
        pay_now                = pay_now,
        room_type              = room.room_type,
        arrival_month          = check_in.month,
        arrival_day            = check_in.day,
        total_nights           = total_nights,
        is_repeated_guest      = is_repeat,
        previous_cancellations = past_cancellations,
        adults                 = adults,
        special_requests       = num_special,
    )

    risk_score = ml_result['score']
    risk_level = ml_result['level']

    # Override thresholds from DB config if set by admin
    low_threshold  = _get_threshold('risk_threshold_low',    40)
    high_threshold = _get_threshold('risk_threshold_high',   70)

    if risk_score < low_threshold:
        risk_level = 'LOW'
    elif risk_score < high_threshold:
        risk_level = 'MEDIUM'
    else:
        risk_level = 'HIGH'

    # ── Determine initial booking status ──────────────────────────────────────
    if risk_level == 'HIGH':
        status = 'pending_review'   # hold for staff
    else:
        status = 'confirmed'        # auto-confirm

    booking = Booking(
        guest_id             = user.id,
        room_id              = room.id,
        check_in             = check_in,
        check_out            = check_out,
        adults               = adults,
        special_requests     = special_requests,
        num_special_requests = num_special,
        pay_now              = pay_now,
        risk_score           = risk_score,
        risk_level           = risk_level,
        risk_probability     = ml_result['probability'],
        status               = status,
    )
    db.session.add(booking)
    db.session.commit()

    return jsonify({
        'booking': booking.to_dict(),
        'message': (
            'Booking confirmed! Confirmation sent to your email.'
            if status == 'confirmed'
            else 'Booking received. Our staff will review it shortly due to high risk flag.'
        )
    }), 201


# ── List bookings ─────────────────────────────────────────────────────────────
@bookings_bp.route('', methods=['GET'])
@jwt_required()
def list_bookings():
    user = _get_current_user()
    status_filter = request.args.get('status')

    if user.role in ('staff', 'admin'):
        q = Booking.query
    else:
        q = Booking.query.filter_by(guest_id=user.id)

    if status_filter:
        q = q.filter(Booking.status == status_filter)

    bookings = q.order_by(Booking.created_at.desc()).all()
    return jsonify([b.to_dict() for b in bookings]), 200


# ── Booking detail ────────────────────────────────────────────────────────────
@bookings_bp.route('/<int:booking_id>', methods=['GET'])
@jwt_required()
def get_booking(booking_id):
    user = _get_current_user()
    booking = Booking.query.get_or_404(booking_id)

    if user.role == 'guest' and booking.guest_id != user.id:
        return jsonify({'error': 'Access denied'}), 403

    return jsonify(booking.to_dict()), 200


# ── Guest: cancel booking ─────────────────────────────────────────────────────
@bookings_bp.route('/<int:booking_id>/cancel', methods=['POST'])
@jwt_required()
def cancel_booking(booking_id):
    user    = _get_current_user()
    booking = Booking.query.get_or_404(booking_id)

    if booking.guest_id != user.id and user.role == 'guest':
        return jsonify({'error': 'Access denied'}), 403

    if booking.status in ('rejected', 'cancelled'):
        return jsonify({'error': 'Booking is already closed'}), 400

    booking.status = 'cancelled'
    db.session.commit()
    return jsonify({'message': 'Booking cancelled', 'booking': booking.to_dict()}), 200


# ── Staff: review HIGH risk booking ──────────────────────────────────────────
@bookings_bp.route('/<int:booking_id>/review', methods=['POST'])
@jwt_required()
def review_booking(booking_id):
    user = _get_current_user()
    if user.role not in ('staff', 'admin'):
        return jsonify({'error': 'Staff access required'}), 403

    booking = Booking.query.get_or_404(booking_id)

    if booking.status != 'pending_review':
        return jsonify({'error': 'Booking is not pending review'}), 400

    data   = request.get_json()
    action = data.get('action')   # 'approve' | 'require_prepayment' | 'reject'
    notes  = data.get('notes', '')

    if action == 'approve':
        booking.status = 'confirmed'
    elif action == 'require_prepayment':
        booking.status = 'requires_prepayment'
    elif action == 'reject':
        booking.status = 'rejected'
    else:
        return jsonify({'error': "action must be 'approve', 'require_prepayment', or 'reject'"}), 400

    booking.reviewed_at    = datetime.utcnow()
    booking.reviewed_by_id = user.id
    booking.staff_notes    = notes
    db.session.commit()

    return jsonify({
        'message': f'Booking {action}d successfully.',
        'booking': booking.to_dict()
    }), 200


# ── Staff: get all HIGH risk alerts ──────────────────────────────────────────
@bookings_bp.route('/alerts', methods=['GET'])
@jwt_required()
def get_alerts():
    user = _get_current_user()
    if user.role not in ('staff', 'admin'):
        return jsonify({'error': 'Staff access required'}), 403

    alerts = Booking.query.filter_by(
        status='pending_review'
    ).order_by(Booking.created_at.desc()).all()

    return jsonify([b.to_dict() for b in alerts]), 200
