from sqlalchemy import create_engine, Column, Integer, String, Boolean, Float, DateTime, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
import datetime

DATABASE_URL = "sqlite:///./figment.db"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

class UserConfig(Base):
    __tablename__ = "user_configs"

    id = Column(Integer, primary_key=True, index=True)
    key = Column(String, unique=True, index=True)
    value = Column(String)

class SpotifyToken(Base):
    __tablename__ = "spotify_tokens"

    id = Column(Integer, primary_key=True, index=True)
    access_token = Column(String)
    refresh_token = Column(String, nullable=True)
    expires_at = Column(DateTime, nullable=True)
    token_type = Column(String, default="Bearer")
    scope = Column(String, nullable=True)

class MustDoRide(Base):
    __tablename__ = "must_do_rides"

    id = Column(Integer, primary_key=True, index=True)
    ride_name = Column(String)
    park = Column(String)
    priority = Column(Float, default=1.0)
    added_at = Column(DateTime, default=datetime.datetime.utcnow)

class SessionState(Base):
    __tablename__ = "session_states"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, default="default_user")  # For single user
    current_location = Column(String)  # GPS coordinates
    party_composition = Column(String)  # JSON string of party members
    last_updated = Column(DateTime, default=datetime.datetime.utcnow)

class PartyMember(Base):
    __tablename__ = "party_members"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("session_states.id"), nullable=True)
    name = Column(String)
    height_inches = Column(Float)  # Height in inches
    age = Column(Integer)
    motion_sensitive = Column(Boolean, default=False)  # For spinning/motion rides
    added_at = Column(DateTime, default=datetime.datetime.utcnow)

class WaitTimeHistory(Base):
    __tablename__ = "wait_time_history"

    id = Column(Integer, primary_key=True, index=True)
    ride_id = Column(String)  # themeparks.wiki ride ID
    ride_name = Column(String)
    park_id = Column(String)
    wait_time = Column(Integer)  # Minutes
    status = Column(String)  # OPERATING, CLOSED, etc
    recorded_at = Column(DateTime, default=datetime.datetime.utcnow)

class UserSubscription(Base):
    __tablename__ = "user_subscriptions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, default="default_user")
    subscription_data = Column(String)  # JSON: Firebase push token
    subscribed_at = Column(DateTime, default=datetime.datetime.utcnow)
    is_active = Column(Boolean, default=True)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Create tables
Base.metadata.create_all(bind=engine)