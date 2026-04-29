"""
Hotel Booking System — Flask Backend
"""

import os
import sys

# Load .env file if it exists (local development)
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'ml'))

from flask import Flask, jsonify, send_from_directory
from flask_jwt_extended import JWTManager
from flask_cors import CORS
from werkzeug.security import generate_password_hash

from models.models import db, User, Room, SystemConfig
from routes.auth     import auth_bp
from routes.rooms    import rooms_bp
from routes.bookings import bookings_bp
from routes.admin    import admin_bp

STATIC_FOLDER = os.path.join(os.path.dirname(__file__), 'static_build')


def create_app():
    app = Flask(__name__, static_folder=STATIC_FOLDER, static_url_path='')

    database_url = os.environ.get('DATABASE_URL', 'sqlite:///hotel.db')
    if database_url.startswith('postgres://'):
        database_url = database_url.replace('postgres://', 'postgresql://', 1)

    app.config['SQLALCHEMY_DATABASE_URI']        = database_url
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['JWT_SECRET_KEY']                 = os.environ.get('JWT_SECRET_KEY', 'grandvista2024secret')
    app.config['JWT_ACCESS_TOKEN_EXPIRES']       = False

    db.init_app(app)
    JWTManager(app)
    CORS(app, origins='*')

    app.register_blueprint(auth_bp)
    app.register_blueprint(rooms_bp)
    app.register_blueprint(bookings_bp)
    app.register_blueprint(admin_bp)

    @app.route('/api/health')
    def health():
        return jsonify({'status': 'ok', 'service': 'Hotel Booking System'}), 200

    @app.route('/', defaults={'path': ''})
    @app.route('/<path:path>')
    def serve_react(path):
        if path.startswith('api/'):
            return jsonify({'error': 'Not found'}), 404
        full = os.path.join(STATIC_FOLDER, path)
        if path and os.path.exists(full):
            return send_from_directory(STATIC_FOLDER, path)
        return send_from_directory(STATIC_FOLDER, 'index.html')

    with app.app_context():
        db.create_all()
        _seed()

    return app


def _seed():
    if not User.query.first():
        users = [
            User(name='Admin User',     email='admin@hotel.com',
                 password_hash=generate_password_hash('admin123'), role='admin'),
            User(name='Staff Alice',    email='staff@hotel.com',
                 password_hash=generate_password_hash('staff123'), role='staff'),
            User(name='Juan dela Cruz', email='guest@hotel.com',
                 password_hash=generate_password_hash('guest123'), role='guest'),
        ]
        db.session.add_all(users)
        db.session.commit()
        print('[seed] Users created.')

    if not Room.query.first():
        rooms = [
            Room(room_number='101', room_type='A', type_label='Standard Single',
                 price_per_night=1200, capacity=1, description='Cozy single room with garden view.'),
            Room(room_number='102', room_type='A', type_label='Standard Single',
                 price_per_night=1200, capacity=1, description='Cozy single room with garden view.'),
            Room(room_number='201', room_type='B', type_label='Standard Double',
                 price_per_night=1800, capacity=2, description='Comfortable double room with city view.'),
            Room(room_number='202', room_type='B', type_label='Standard Double',
                 price_per_night=1800, capacity=2, description='Comfortable double room with city view.'),
            Room(room_number='301', room_type='C', type_label='Deluxe Double',
                 price_per_night=2500, capacity=2, description='Spacious deluxe room with balcony and sea view.'),
            Room(room_number='302', room_type='D', type_label='Deluxe Twin',
                 price_per_night=2800, capacity=3, description='Deluxe twin beds, perfect for families.'),
            Room(room_number='401', room_type='E', type_label='Junior Suite',
                 price_per_night=4000, capacity=2, description='Junior suite with living area and premium amenities.'),
            Room(room_number='501', room_type='F', type_label='Executive Suite',
                 price_per_night=6500, capacity=2, description='Executive suite with panoramic view and butler service.'),
            Room(room_number='601', room_type='G', type_label='Presidential Suite',
                 price_per_night=12000, capacity=4, description='The ultimate luxury suite for VIP guests.'),
        ]
        db.session.add_all(rooms)
        db.session.commit()
        print('[seed] Rooms created.')

    if not SystemConfig.query.first():
        configs = [
            SystemConfig(key='risk_threshold_low',  value='40'),
            SystemConfig(key='risk_threshold_high', value='70'),
            SystemConfig(key='hotel_name',          value='Grand Vista Hotel'),
            SystemConfig(key='hotel_email',         value='reservations@grandvista.com'),
            SystemConfig(key='hotel_phone',         value='+63 88 123 4567'),
        ]
        db.session.add_all(configs)
        db.session.commit()
        print('[seed] Config created.')


# For gunicorn compatibility
app = create_app()

if __name__ == '__main__':
    app = create_app()
    print('\n' + '='*58)
    print('  Grand Vista Hotel System is running!')
    print('  Open in browser: http://localhost:5000')
    print()
    print('  Accounts:')
    print('    admin@hotel.com / admin123  (Admin)')
    print('    staff@hotel.com / staff123  (Staff)')
    print('    guest@hotel.com / guest123  (Guest)')
    print('='*58 + '\n')
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', debug=False, port=port)
