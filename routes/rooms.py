"""
Room routes
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
    overlapping = Booking.query.filter(
        Booking.status.in_(['confirmed', 'pending_review', 'requires_prepayment', 'checked_in']),
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
        image_url       = data.get('image_url', ''),
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

    # Staff can update everything EXCEPT price — only admin can change price
    for field in ['room_number', 'room_type', 'type_label', 'capacity',
                  'description', 'image_url', 'is_available']:
        if field in data:
            if field == 'room_type':
                setattr(room, field, data[field].upper())
            elif field == 'capacity':
                setattr(room, field, int(data[field]))
            else:
                setattr(room, field, data[field])

    # Only admin can change price
    if 'price_per_night' in data:
        if user.role != 'admin':
            return jsonify({'error': 'Only admin can change room prices'}), 403
        room.price_per_night = float(data['price_per_night'])

    db.session.commit()
    return jsonify(room.to_dict()), 200


@rooms_bp.route('/<int:room_id>', methods=['DELETE'])
@jwt_required()
def delete_room(room_id):
    user = _get_current_user()
    if user.role != 'admin':
        return jsonify({'error': 'Admin access required'}), 403

    room = Room.query.get_or_404(room_id)

    # Check if room has any bookings
    has_bookings = Booking.query.filter_by(room_id=room_id).first()
    if has_bookings:
        # Deactivate instead of delete to preserve history
        room.is_available = False
        db.session.commit()
        return jsonify({
            'message': 'Room has booking history and cannot be deleted. It has been deactivated instead.',
            'room': room.to_dict()
        }), 200

    db.session.delete(room)
    db.session.commit()
    return jsonify({'message': 'Room deleted successfully.'}), 200
