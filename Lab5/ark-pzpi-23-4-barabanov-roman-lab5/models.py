import uuid
from datetime import datetime
from sqlalchemy import Column, String, Boolean, ForeignKey, Integer, DateTime, Text
from sqlalchemy.orm import relationship
from database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    role = Column(String, default="user")
    created_at = Column(DateTime, default=datetime.utcnow)

    polls = relationship("Poll", back_populates="owner")


class Poll(Base):
    __tablename__ = "polls"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    title = Column(String, index=True)
    description = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)
    room_id = Column(String, index=True)
    owner_id = Column(String, ForeignKey("users.id"))
    created_at = Column(DateTime, default=datetime.utcnow)

    owner = relationship("User", back_populates="polls")
    options = relationship("Option", back_populates="poll", cascade="all, delete")
    votes = relationship("Vote", back_populates="poll", cascade="all, delete")


class Option(Base):
    __tablename__ = "options"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    poll_id = Column(String, ForeignKey("polls.id"))
    text = Column(String)
    vote_count = Column(Integer, default=0)

    poll = relationship("Poll", back_populates="options")
    votes = relationship("Vote", back_populates="option")


class Device(Base):
    __tablename__ = "devices"

    id = Column(String, primary_key=True)
    device_type = Column(String, default="button")
    room_id = Column(String, nullable=True)
    battery_level = Column(Integer, default=100)
    last_seen = Column(DateTime, default=datetime.utcnow)

    votes = relationship("Vote", back_populates="device")


class Vote(Base):
    __tablename__ = "votes"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    poll_id = Column(String, ForeignKey("polls.id"))
    option_id = Column(String, ForeignKey("options.id"))
    device_id = Column(String, ForeignKey("devices.id"))
    source = Column(String, default="iot")
    created_at = Column(DateTime, default=datetime.utcnow)

    poll = relationship("Poll", back_populates="votes")
    option = relationship("Option", back_populates="votes")
    device = relationship("Device", back_populates="votes")


class SystemLog(Base):
    __tablename__ = "system_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_email = Column(String)
    action = Column(String)
    details = Column(String)
    timestamp = Column(DateTime, default=datetime.utcnow)