from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session
from database import get_db, UserSubscription, SessionState, SessionLocal
from spotify_rule_engine import SpotifyRuleEngine
from disney_engine import DisneyIntelligenceEngine
from llm_gateway import get_llm_response, get_agent_insight
from notifications import send_nudge
from pydantic import BaseModel
from typing import List, Dict, Optional
from apscheduler.schedulers.background import BackgroundScheduler
from contextlib import asynccontextmanager
import json
import os
from pathlib import Path
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

# Initialize engines early
spotify_engine = SpotifyRuleEngine()
disney_engine = DisneyIntelligenceEngine()

# Background scheduler for polls
scheduler = BackgroundScheduler()

def poll_wait_times():
    """Background job to poll and store wait times for all parks every 5 minutes."""
    try:
        parks = ['MagicKingdomWaltDisneyWorld', 'EpcotWaltDisneyWorld']
        for park in parks:
            disney_engine.store_wait_times(park)
        
        # Check for nudges and send notifications
        db = SessionLocal()
        try:
            # Get all active sessions (sessions updated within last 30 minutes)
            from datetime import datetime, timedelta
            thirty_mins_ago = datetime.utcnow() - timedelta(minutes=30)
            
            active_sessions = db.query(SessionState).filter(
                SessionState.last_updated >= thirty_mins_ago
            ).all()
            
            for session in active_sessions:
                # Parse the location from the session
                try:
                    location_parts = session.current_location.split(',')
                    user_location = (float(location_parts[0]), float(location_parts[1]))
                    
                    # Check for nudges for this session's park
                    for park in parks:
                        nudges = disney_engine.check_nudges(park, user_location)
                        
                        # Send notifications for each nudge
                        for nudge in nudges:
                            send_nudge(nudge, session.user_id)
                except Exception as e:
                    print(f"Error processing nudges for session {session.id}: {e}")
        finally:
            db.close()
    except Exception as e:
        print(f"Error in wait time polling: {e}")

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage app startup and shutdown."""
    # Startup
    scheduler.add_job(poll_wait_times, 'interval', minutes=5, id='wait_time_poller')
    scheduler.start()
    print("Background scheduler started for wait time polling")
    yield
    # Shutdown
    scheduler.shutdown()
    print("Background scheduler stopped")

app = FastAPI(
    title="Project FIGMENT",
    description="A personal agentic hub for Disney and Spotify.",
    version="0.1.0",
    lifespan=lifespan
)

# Initialize Google ADK
# vertexai.init(project="your-project-id", location="us-central1")  # TODO: Configure with actual project

# Mount static files (frontend assets, icons, screenshots)
frontend_dir = Path(__file__).parent.resolve() / "frontend"
assets_dir = frontend_dir / "static"

if frontend_dir.exists():
    try:
        app.mount("/static", StaticFiles(directory=str(assets_dir) if assets_dir.exists() else str(frontend_dir)), name="static")
    except Exception as e:
        print(f"Warning: Could not mount static files: {e}")

@app.get("/manifest.json")
def get_manifest():
    """Serve the PWA manifest."""
    manifest_path = frontend_dir / "manifest.json"
    if manifest_path.exists():
        return FileResponse(str(manifest_path), media_type="application/manifest+json")
    print(f"DEBUG: Manifest not found at {manifest_path}")
    return {"error": f"Manifest not found at {manifest_path}"}, 404

@app.get("/service-worker.js")
def get_service_worker():
    """Serve the service worker."""
    sw_path = frontend_dir / "service-worker.js"
    if sw_path.exists():
        return FileResponse(str(sw_path), media_type="application/javascript")
    return {"error": "Service worker not found"}, 404

class PlaylistRequest(BaseModel):
    name: str
    throwback: Optional[bool] = False
    fresh: Optional[bool] = False
    tacno: Optional[bool] = False
    christmas: Optional[bool] = False
    clean: Optional[bool] = False

class NextActionRequest(BaseModel):
    park_id: str
    user_location: List[float]  # [lat, lon]
    party_composition: Dict  # TODO: Define schema

class AgentRequest(BaseModel):
    park_id: str
    user_location: List[float]
    party_composition: Dict
    playlist_context: Optional[str] = None

class PushSubscriptionRequest(BaseModel):
    endpoint: str
    auth: str
    p256dh: str
    user_id: Optional[str] = "default_user"

@app.get("/")
def read_root():
    """Root endpoint to confirm the server is running."""
    return {"message": "Welcome to Project FIGMENT"}

@app.get("/auth/spotify")
def auth_spotify():
    """
    Redirect to Spotify authorization.
    """
    auth_url = spotify_engine.sp_oauth.get_authorize_url()
    return {"auth_url": auth_url}

@app.get("/auth/status")
def auth_status():
    """
    Check Spotify authentication status.
    """
    return {"authenticated": spotify_engine.is_authenticated()}

@app.post("/create_playlist")
def create_playlist(request: PlaylistRequest, db: Session = Depends(get_db)):
    """
    Create a Spotify playlist based on rules and toggles.
    """
    try:
        tracks = spotify_engine.get_potential_tracks()
        followed = spotify_engine.get_followed_artists()
        filtered_tracks = spotify_engine.apply_rules(tracks, followed, **request.dict())
        playlist_id = spotify_engine.create_playlist(request.name, filtered_tracks)
        return {"playlist_id": playlist_id, "tracks_count": len(filtered_tracks)}
    except Exception as e:
        return {"error": str(e)}

@app.post("/get_next_action")
def get_next_action(request: NextActionRequest, db: Session = Depends(get_db)):
    """
    Get Disney park recommendations and check for nudges.
    """
    recommendations = disney_engine.get_recommendations(
        request.park_id, tuple(request.user_location), request.party_composition
    )
    nudges = disney_engine.check_nudges(
        request.park_id, tuple(request.user_location)
    )
    return {"recommendations": recommendations, "nudges": nudges}

@app.post("/agent/next_action")
def get_agent_next_action(request: AgentRequest, db: Session = Depends(get_db)):
    """
    Get Disney recommendations plus an LLM-informed agent strategy.
    """
    recommendations = disney_engine.get_recommendations(
        request.park_id, tuple(request.user_location), request.party_composition
    )
    nudges = disney_engine.check_nudges(
        request.park_id, tuple(request.user_location)
    )
    playlist_context = request.playlist_context or ""
    agent_advice = get_agent_insight(recommendations, nudges, playlist_context)
    return {
        "recommendations": recommendations,
        "nudges": nudges,
        "agent_advice": agent_advice
    }

@app.post("/subscribe")
def subscribe_to_notifications(request: PushSubscriptionRequest, db: Session = Depends(get_db)):
    """
    Register a user's device for push notifications.
    Requires endpoint, auth, and p256dh from ServiceWorker.
    """
    try:
        # Store subscription in database
        subscription_data = {
            "endpoint": request.endpoint,
            "keys": {
                "auth": request.auth,
                "p256dh": request.p256dh
            }
        }
        
        # Check if subscription already exists for this user
        existing = db.query(UserSubscription).filter(
            UserSubscription.user_id == request.user_id,
            UserSubscription.subscription_data == json.dumps(subscription_data)
        ).first()
        
        if not existing:
            subscription = UserSubscription(
                user_id=request.user_id,
                subscription_data=json.dumps(subscription_data)
            )
            db.add(subscription)
            db.commit()
        
        return {"status": "subscribed", "message": "Device registered for notifications"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002, log_level="info")