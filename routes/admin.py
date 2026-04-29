"""
Admin / Staff routes
"""

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from werkzeug.security import generate_password_hash
from models.models import db, User, Booking, SystemConfig

admin_bp = Blueprint('admin', __name__, url_prefix='/api/admin')


def _get_current_user():
    user_id = int(get_jwt_identity())
    return User.query.get(user_id)


@admin_bp.route('/users', methods=['GET'])
@jwt_required()
def list_users():
    user = _get_current_user()
    if user.role != 'admin':
        return jsonify({'error': 'Admin access required'}), 403
    users = User.query.order_by(User.created_at.desc()).all()
    return jsonify([u.to_dict() for u in users]), 200


@admin_bp.route('/users', methods=['POST'])
@jwt_required()
def create_staff():
    user = _get_current_user()
    if user.role != 'admin':
        return jsonify({'error': 'Admin access required'}), 403

    data = request.get_json()
    for f in ['name', 'email', 'password', 'role']:
        if not data.get(f):
            return jsonify({'error': f'{f} is required'}), 400

    if data['role'] not in ('guest', 'staff', 'admin'):
        return jsonify({'error': 'role must be guest, staff, or admin'}), 400

    if User.query.filter_by(email=data['email']).first():
        return jsonify({'error': 'Email already registered'}), 409

    new_user = User(
        name          = data['name'].strip(),
        email         = data['email'].strip().lower(),
        password_hash = generate_password_hash(data['password']),
        role          = data['role'],
    )
    db.session.add(new_user)
    db.session.commit()
    return jsonify(new_user.to_dict()), 201


@admin_bp.route('/users/<int:user_id>', methods=['PUT'])
@jwt_required()
def update_user(user_id):
    current = _get_current_user()
    if current.role != 'admin':
        return jsonify({'error': 'Admin access required'}), 403

    # FIXED: prevent admin from changing their own role
    if current.id == user_id and 'role' in request.get_json(silent=True or {}):
        data = request.get_json()
        if 'role' in data and data['role'] != current.role:
            return jsonify({'error': 'You cannot change your own role'}), 403

    target = User.query.get_or_404(user_id)
    data   = request.get_json()

    if 'role' in data:
        # Extra guard: block self role change
        if target.id == current.id and data['role'] != current.role:
            return jsonify({'error': 'You cannot change your own role'}), 403
        if data['role'] not in ('guest', 'staff', 'admin'):
            return jsonify({'error': 'Invalid role'}), 400
        target.role = data['role']

    if 'is_active' in data:
        if target.id == current.id:
            return jsonify({'error': 'You cannot deactivate your own account'}), 403
        target.is_active = bool(data['is_active'])

    if 'name' in data:
        target.name = data['name'].strip()

    db.session.commit()
    return jsonify(target.to_dict()), 200


@admin_bp.route('/config', methods=['GET'])
@jwt_required()
def get_config():
    user = _get_current_user()
    if user.role != 'admin':
        return jsonify({'error': 'Admin access required'}), 403
    configs = SystemConfig.query.all()
    return jsonify({c.key: c.value for c in configs}), 200


@admin_bp.route('/config', methods=['PUT'])
@jwt_required()
def update_config():
    user = _get_current_user()
    if user.role != 'admin':
        return jsonify({'error': 'Admin access required'}), 403

    data = request.get_json()
    allowed_keys = {
        'risk_threshold_low', 'risk_threshold_high',
        'hotel_name', 'hotel_email', 'hotel_phone',
    }

    for key, value in data.items():
        if key not in allowed_keys:
            continue
        cfg = SystemConfig.query.get(key)
        if cfg:
            cfg.value = str(value)
        else:
            db.session.add(SystemConfig(key=key, value=str(value)))

    db.session.commit()
    configs = SystemConfig.query.all()
    return jsonify({c.key: c.value for c in configs}), 200


@admin_bp.route('/reports/summary', methods=['GET'])
@jwt_required()
def summary_report():
    user = _get_current_user()
    if user.role not in ('staff', 'admin'):
        return jsonify({'error': 'Staff access required'}), 403

    total     = Booking.query.count()
    confirmed = Booking.query.filter_by(status='confirmed').count()
    pending   = Booking.query.filter_by(status='pending_review').count()
    rejected  = Booking.query.filter_by(status='rejected').count()
    cancelled = Booking.query.filter_by(status='cancelled').count()
    prepay    = Booking.query.filter_by(status='requires_prepayment').count()
    low_risk  = Booking.query.filter_by(risk_level='LOW').count()
    med_risk  = Booking.query.filter_by(risk_level='MEDIUM').count()
    high_risk = Booking.query.filter_by(risk_level='HIGH').count()

    return jsonify({
        'totals': {
            'total': total, 'confirmed': confirmed,
            'pending_review': pending, 'requires_prepayment': prepay,
            'rejected': rejected, 'cancelled': cancelled,
        },
        'risk_distribution': {
            'LOW': low_risk, 'MEDIUM': med_risk, 'HIGH': high_risk,
        },
    }), 200
