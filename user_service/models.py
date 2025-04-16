from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class User(db.Model):
    __tablename__ = 'users'

    user_id = db.Column(db.BigInteger, primary_key=True)
    username = db.Column(db.String(255))
    first_name = db.Column(db.String(255))
    last_name = db.Column(db.String(255))
    join_date = db.Column(db.DateTime, default=datetime.utcnow)
    last_activity = db.Column(db.DateTime, default=datetime.utcnow)
    is_blocked = db.Column(db.Boolean, default=False)

    favorites = db.relationship('UserFavorite', backref='user', lazy=True, cascade="all, delete-orphan")
    usage_stats = db.relationship('UsageStat', backref='user', lazy=True, cascade="all, delete-orphan")

class UserFavorite(db.Model):
    __tablename__ = 'user_favorites'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.BigInteger, db.ForeignKey('users.user_id'), nullable=False)
    crypto_symbol = db.Column(db.String(20), nullable=False)
    added_on = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint('user_id', 'crypto_symbol', name='unique_user_crypto'),
    )

class UsageStat(db.Model):
    __tablename__ = 'usage_stats'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.BigInteger, db.ForeignKey('users.user_id'), nullable=False)
    command = db.Column(db.String(100), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)