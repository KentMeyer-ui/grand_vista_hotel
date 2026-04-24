"""
Room routes
  GET    /api/rooms                  — list all rooms (public)
  GET    /api/rooms/<id>             — room detail (public)
  GET    /api/rooms/available        — search available rooms by dates
  POST   /api/rooms                  — create room (admin only)
  PUT    /api/rooms/<id>             — update room (admin/staff)
  DELETE /api/rooms/<id>             — delete room (admin only)
"""

from datetime import date
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from models.models import db, User, Room, Booking

rooms_bp = Blueprint('rooms', __name__, url_prefix='/api/rooms')


def _get_current_user():
    user_id = int(get_jwt_identity())
    return User.query.get(user_id)


def _rooms_booked_on(check_in: date, check_out: date):
    """Return set of room IDs that overlap with the requested dates."""
    overlapping = Booking.query.filter(
        Booking.status.in_(['confirmed', 'pending_review', 'requires_prepayment']),
        Booking.check_in  < check_out,
        Booking.check_out > check_in,
    ).all()
    return {b.room_id for b in overlapping}


@rooms_bp.route('', methods=['GET'])
def list_rooms():
    rooms = Room.query.order_by(Room.room_number).all()
    return jsonify([r.to_dict() for r in rooms]), 200


@rooms_bp.route('/available', methods=['GET'])
def available_rooms():
    check_in_str  = request.args.get('check_in')
    check_out_str = request.args.get('check_out')
    adults        = request.args.get('adults', 1, type=int)

    if not check_in_str or not check_out_str:
        return jsonify({'error': 'check_in and check_out are required'}), 400

    try:
        check_in  = date.fromisoformat(check_in_str)
        check_out = date.fromisoformat(check_out_str)
    except ValueError:
        return jsonify({'error': 'Invalid date format. Use YYYY-MM-DD'}), 400

    if check_in >= check_out:
        return jsonify({'error': 'check_out must be after check_in'}), 400

    if check_in < date.today():
        return jsonify({'error': 'check_in cannot be in the past'}), 400

    booked_ids = _rooms_booked_on(check_in, check_out)

    rooms = Room.query.filter(
        Room.is_available == True,
        Room.capacity >= adults,
        ~Room.id.in_(booked_ids),
    ).order_by(Room.price_per_night).all()

    return jsonify([r.to_dict() for r in rooms]), 200


@rooms_bp.route('/<int:room_id>', methods=['GET'])
def get_room(room_id):
    room = Room.query.get_or_404(room_id)
    return jsonify(room.to_dict()), 200


@rooms_bp.route('', methods=['POST'])
@jwt_required()
def create_room():
    user = _get_current_user()
    if user.role != 'admin':
        return jsonify({'error': 'Admin access required'}), 403

    data = request.get_json()
    required = ['room_number', 'room_type', 'type_label', 'price_per_night']
    for f in required:
        if not data.get(f):
            return jsonify({'error': f'{f} is required'}), 400

    if Room.query.filter_by(room_number=data['room_number']).first():
        return jsonify({'error': 'Room number already exists'}), 409

    room = Room(
        room_number     = data['room_number'],
        room_type       = data['room_type'].upper(),
        type_label      = data['type_label'],
        price_per_night = float(data['price_per_night']),
        capacity        = int(data.get('capacity', 2)),
        description     = data.get('description', ''),
        is_available    = data.get('is_available', True),
    )
    db.session.add(room)
    db.session.commit()
    return jsonify(room.to_dict()), 201


@rooms_bp.route('/<int:room_id>', methods=['PUT'])
@jwt_required()
def update_room(room_id):
    user = _get_current_user()
    if user.role not in ('admin', 'staff'):
        return jsonify({'error': 'Staff access required'}), 403

    room = Room.query.get_or_404(room_id)
    data = request.get_json()

    for field in ['room_number', 'room_type', 'type_label',
                  'price_per_night', 'capacity', 'description', 'is_available']:
        if field in data:
            if field == 'room_type':
                setattr(room, field, data[field].upper())
            elif field == 'price_per_night':
                setattr(room, field, float(data[field]))
            elif field in ('capacity',):
                setattr(room, field, int(data[field]))
            else:
                setattr(room, field, data[field])

    db.session.commit()
    return jsonify(room.to_dict()), 200


@rooms_bp.route('/<int:room_id>', methods=['DELETE'])
@jwt_required()
def delete_room(room_id):
    user = _get_current_user()
    if user.role != 'admin':
        return jsonify({'error': 'Admin access required'}), 403

    room = Room.query.get_or_404(room_id)
    db.session.delete(room)
    db.session.commit()
    return jsonify({'message': 'Room deleted'}), 200
