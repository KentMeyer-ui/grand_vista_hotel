from datetime import datetime
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


class User(db.Model):
    __tablename__ = 'users'

    id            = db.Column(db.Integer, primary_key=True)
    name          = db.Column(db.String(120), nullable=False)
    email         = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    role          = db.Column(db.String(20), nullable=False, default='guest')
    created_at    = db.Column(db.DateTime, default=datetime.utcnow)
    is_active     = db.Column(db.Boolean, default=True)

    bookings = db.relationship('Booking', backref='guest', lazy=True,
                               foreign_keys='Booking.guest_id')

    def to_dict(self):
        return {
            'id':         self.id,
            'name':       self.name,
            'email':      self.email,
            'role':       self.role,
            'created_at': self.created_at.isoformat(),
            'is_active':  self.is_active,
        }


class Room(db.Model):
    __tablename__ = 'rooms'

    id              = db.Column(db.Integer, primary_key=True)
    room_number     = db.Column(db.String(10), unique=True, nullable=False)
    room_type       = db.Column(db.String(1), nullable=False)
    type_label      = db.Column(db.String(50), nullable=False)
    price_per_night = db.Column(db.Float, nullable=False)
    capacity        = db.Column(db.Integer, nullable=False, default=2)
    description     = db.Column(db.String(300))
    image_url       = db.Column(db.String(1000), default='')
    is_available    = db.Column(db.Boolean, default=True)

    bookings = db.relationship('Booking', backref='room', lazy=True)

    def to_dict(self):
        return {
            'id':              self.id,
            'room_number':     self.room_number,
            'room_type':       self.room_type,
            'type_label':      self.type_label,
            'price_per_night': self.price_per_night,
            'capacity':        self.capacity,
            'description':     self.description,
            'image_url':       self.image_url or '',
            'is_available':    self.is_available,
        }


class Booking(db.Model):
    __tablename__ = 'bookings'

    id                   = db.Column(db.Integer, primary_key=True)
    guest_id             = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    room_id              = db.Column(db.Integer, db.ForeignKey('rooms.id'), nullable=False)
    check_in             = db.Column(db.Date, nullable=False)
    check_out            = db.Column(db.Date, nullable=False)
    adults               = db.Column(db.Integer, nullable=False, default=1)
    special_requests     = db.Column(db.String(500), default='')
    num_special_requests = db.Column(db.Integer, default=0)
    pay_now              = db.Column(db.Boolean, nullable=False, default=False)

    risk_score       = db.Column(db.Integer)
    risk_level       = db.Column(db.String(10))
    risk_probability = db.Column(db.Float)

    # Statuses:
    # pending_review       → HIGH risk, waiting for staff
    # confirmed            → approved, guest expected
    # requires_prepayment  → staff requests payment first
    # rejected             → staff rejected it
    # cancelled            → guest cancelled
    # checked_in           → guest arrived and checked in
    # checked_out          → guest has left
    # no_show              → guest never arrived
    status         = db.Column(db.String(30), nullable=False, default='pending')
    created_at     = db.Column(db.DateTime, default=datetime.utcnow)
    reviewed_at    = db.Column(db.DateTime)
    reviewed_by_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    staff_notes    = db.Column(db.String(500))
    checked_in_at  = db.Column(db.DateTime)   # when guest actually arrived
    checked_out_at = db.Column(db.DateTime)   # when guest actually left

    def total_nights(self):
        return (self.check_out - self.check_in).days

    def to_dict(self):
        return {
            'id':               self.id,
            'guest_id':         self.guest_id,
            'guest_name':       self.guest.name if self.guest else None,
            'guest_email':      self.guest.email if self.guest else None,
            'room_id':          self.room_id,
            'room_number':      self.room.room_number if self.room else None,
            'room_type':        self.room.room_type if self.room else None,
            'type_label':       self.room.type_label if self.room else None,
            'price_per_night':  self.room.price_per_night if self.room else None,
            'image_url':        self.room.image_url if self.room else '',
            'check_in':         self.check_in.isoformat(),
            'check_out':        self.check_out.isoformat(),
            'total_nights':     self.total_nights(),
            'adults':           self.adults,
            'special_requests': self.special_requests,
            'pay_now':          self.pay_now,
            'risk_score':       self.risk_score,
            'risk_level':       self.risk_level,
            'risk_probability': self.risk_probability,
            'status':           self.status,
            'created_at':       self.created_at.isoformat(),
            'reviewed_at':      self.reviewed_at.isoformat() if self.reviewed_at else None,
            'staff_notes':      self.staff_notes,
            'checked_in_at':    self.checked_in_at.isoformat() if self.checked_in_at else None,
            'checked_out_at':   self.checked_out_at.isoformat() if self.checked_out_at else None,
        }


class SystemConfig(db.Model):
    __tablename__ = 'system_config'

    key   = db.Column(db.String(80), primary_key=True)
    value = db.Column(db.String(300), nullable=False)

    def to_dict(self):
        return {'key': self.key, 'value': self.value}
