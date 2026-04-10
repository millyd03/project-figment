from sqlalchemy import create_engine, Column, Integer, String, Boolean, Float, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
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

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Create tables
Base.metadata.create_all(bind=engine)