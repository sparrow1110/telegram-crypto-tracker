from sqlalchemy import Column, BigInteger, String, DateTime, Boolean, Integer, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

Base = declarative_base()


class User(Base):
    __tablename__ = 'users'

    user_id = Column(BigInteger, primary_key=True)
    username = Column(String(255))
    first_name = Column(String(255))
    last_name = Column(String(255))
    join_date = Column(DateTime, default=datetime.utcnow)
    last_activity = Column(DateTime, default=datetime.utcnow)
    is_blocked = Column(Boolean, default=False)

    favorites = relationship('UserFavorite', backref='user', lazy='dynamic', cascade="all, delete-orphan")
    usage_stats = relationship('UsageStat', backref='user', lazy='dynamic', cascade="all, delete-orphan")


class UserFavorite(Base):
    __tablename__ = 'user_favorites'

    id = Column(Integer, primary_key=True)
    user_id = Column(BigInteger, ForeignKey('users.user_id'), nullable=False)
    crypto_symbol = Column(String(20), nullable=False)
    added_on = Column(DateTime, default=datetime.utcnow)

    __table_args__ = {'sqlite_autoincrement': True, 'extend_existing': True}


class UsageStat(Base):
    __tablename__ = 'usage_stats'

    id = Column(Integer, primary_key=True)
    user_id = Column(BigInteger, ForeignKey('users.user_id'), nullable=False)
    command = Column(String(100), nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)

    __table_args__ = {'sqlite_autoincrement': True, 'extend_existing': True}
