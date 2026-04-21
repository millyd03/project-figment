from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db, UserSubscription, SessionState, SessionLocal
from spotify_rule_engine import SpotifyRuleEngine
try:
    # Optional mock used in tests
    from mock_spotify import MockSpotifyRuleEngine
except Exception:
    MockSpotifyRuleEngine = None
from auth_store import auth_store
from disney_engine import DisneyIntelligenceEngine
from llm_gateway import get_llm_response, get_agent_insight
from notifications import send_nudge
from pydantic import BaseModel
from typing import List, Dict, Optional
from apscheduler.schedulers.background import BackgroundScheduler
from contextlib import asynccontextmanager
import json
import os
import requests
import hashlib
import base64
import secrets
import time
from pathlib import Path
from urllib.parse import urlencode
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, HTMLResponse
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
from multiprocessing import Process, Queue

# Initialize engines early
spotify_engine = SpotifyRuleEngine()
disney_engine = DisneyIntelligenceEngine()

# Background scheduler for polls
scheduler = BackgroundScheduler()

def poll_wait_times():
    """Background job to poll and store wait times for all parks every 5 minutes."""
    try:
        parks = ['Disneyland', 'DisneysCaliforniaAdventure', 'MagicKingdomWaltDisneyWorld', 'EpcotWaltDisneyWorld', 'DisneysHollywoodStudios', 'DisneysAnimalKingdom']
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


def _spotify_proc_worker(q, name: str, opts: dict):
    """Top-level worker for multiprocessing to perform Spotify operations.
    Puts (True, result) or (False, error_str) into the provided queue.
    """
    try:
        from datetime import datetime
        if getattr(spotify_engine, '_rate_limited_until', None) and spotify_engine._rate_limited_until > datetime.utcnow():
            q.put((True, {"error": "Spotify rate-limited; try again later"}))
            return
        tracks = spotify_engine.get_potential_tracks()
        followed = spotify_engine.get_followed_artists()
        filtered_tracks = spotify_engine.apply_rules(tracks, followed, **opts)
        if not filtered_tracks:
            q.put((True, {"error": "No tracks available"}))
            return
        playlist_id = spotify_engine.create_playlist(name, filtered_tracks)
        q.put((True, {"playlist_id": playlist_id, "tracks_count": len(filtered_tracks)}))
    except Exception as e:
        q.put((False, str(e)))

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage app startup and shutdown."""
    # Startup
    scheduler.add_job(poll_wait_times, 'interval', minutes=5, id='wait_time_poller')
    scheduler.start()
    print("Background scheduler started for wait time polling")
    # Try to rehydrate Spotify token silently on startup (uses DB + refresh token)
    try:
        print("Attempting to rehydrate Spotify profile on startup")
        # spotify_engine._load_active_profile() already called in constructor, but ensure refresh
        if spotify_engine.active_profile and spotify_engine._is_token_expired():
            refreshed = spotify_engine._refresh_active_profile()
            print(f"Spotify token refresh attempted on startup: {refreshed}")
    except Exception as e:
        print(f"Error during Spotify startup rehydration: {e}")
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

PKCE_MAX_AGE = 600


def _cleanup_pkce_state():
    # Delegate to auth_store implementation
    auth_store.cleanup()


def _generate_pkce_pair():
    code_verifier = secrets.token_urlsafe(64)
    code_challenge = base64.urlsafe_b64encode(hashlib.sha256(code_verifier.encode()).digest()).decode().rstrip("=")
    return code_verifier, code_challenge


def _exchange_code_for_token(code: str, code_verifier: str) -> Dict:
    payload = {
        "client_id": spotify_engine.client_id,
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": spotify_engine.redirect_uri,
        "code_verifier": code_verifier,
    }
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    response = requests.post("https://accounts.spotify.com/api/token", data=payload, headers=headers)
    if response.status_code != 200:
        raise HTTPException(status_code=response.status_code, detail=response.text)
    return response.json()

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

class ProfileSelectRequest(BaseModel):
    profile_id: int

@app.get("/")
def read_root():
    """Root endpoint to confirm the server is running."""
    return {"message": "Welcome to Project FIGMENT"}

@app.get("/auth/spotify")
def auth_spotify(profile_name: Optional[str] = None, profile_id: Optional[int] = None):
    """
    Get Spotify authorization URL for a new or existing profile using PKCE.
    """
    _cleanup_pkce_state()
    state = secrets.token_urlsafe(16)
    code_verifier, code_challenge = _generate_pkce_pair()

    auth_store.put_state(state, {
        "verifier": code_verifier,
        "profile_id": profile_id,
        "profile_name": profile_name,
    }, ttl=PKCE_MAX_AGE)

    auth_params = {
        "client_id": spotify_engine.client_id,
        "response_type": "code",
        "redirect_uri": spotify_engine.redirect_uri,
        "scope": spotify_engine.scopes,
        "state": state,
        "code_challenge_method": "S256",
        "code_challenge": code_challenge,
    }
    auth_url = "https://accounts.spotify.com/authorize?" + urlencode(auth_params)
    return {"auth_url": auth_url}


@app.get("/callback")
def auth_callback(code: str, state: Optional[str] = None):
    """
    Handle Spotify OAuth callback and save the profile.
    """
    if not state or not auth_store.has_state(state):
        raise HTTPException(status_code=400, detail="Invalid or expired state")

    stored = auth_store.pop_state(state)
    if not stored:
        raise HTTPException(status_code=400, detail="Invalid or expired state")
    code_verifier = stored.get("verifier")
    profile_id = stored.get("profile_id")
    profile_name = stored.get("profile_name")

    try:
        token_info = _exchange_code_for_token(code, code_verifier)
        if profile_id:
            spotify_engine.create_profile(token_info, profile_id=profile_id)
        else:
            spotify_engine.create_profile(token_info, desired_name=profile_name)

        html = """
            <html>
                <body style='background:#121212;color:#fff;font-family:sans-serif;display:flex;flex-direction:column;align-items:center;justify-content:center;height:100vh;'>
                    <h1>Spotify connected successfully.</h1>
                    <p>You can close this window and return to the FIGMENT app.</p>
                </body>
            </html>
        """
        return HTMLResponse(content=html)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/auth/status")
def auth_status():
    """
    Check Spotify authentication status.
    """
    return {
        "authenticated": spotify_engine.is_authenticated(),
        "active_profile": spotify_engine.get_active_profile_summary(),
        "profiles": spotify_engine.get_profiles(),
        "rate_limited_until": getattr(spotify_engine, '_rate_limited_until', None).isoformat() if getattr(spotify_engine, '_rate_limited_until', None) else None
    }


@app.post("/_test/enable_mock_spotify")
def enable_mock_spotify():
    """Test-only: swap in a mock Spotify engine to avoid external calls."""
    global spotify_engine
    if MockSpotifyRuleEngine is None:
        raise HTTPException(status_code=500, detail="MockSpotifyRuleEngine not available")
    spotify_engine = MockSpotifyRuleEngine()
    return {"mock_enabled": True}

@app.get("/auth/profiles")
def auth_profiles():
    """
    List saved Spotify profiles.
    """
    return {"profiles": spotify_engine.get_profiles()}

@app.post("/auth/profile/select")
def auth_profile_select(request: ProfileSelectRequest):
    """
    Activate a different saved Spotify profile.
    """
    active = spotify_engine.activate_profile(request.profile_id)
    return {"selected": active, "active_profile": spotify_engine.get_active_profile_summary()}

@app.post("/create_playlist")
def create_playlist(request: PlaylistRequest, db: Session = Depends(get_db)):
    """
    Create a Spotify playlist based on rules and toggles.
    """
    try:
        # Run Spotify-heavy operations in a short-thread so we can timebox remote calls
        def do_create():
            from datetime import datetime
            if getattr(spotify_engine, '_rate_limited_until', None) and spotify_engine._rate_limited_until > datetime.utcnow():
                return {"error": "Spotify rate-limited; try again later"}
            tracks = spotify_engine.get_potential_tracks()
            followed = spotify_engine.get_followed_artists()
            filtered_tracks = spotify_engine.apply_rules(tracks, followed, **request.dict(exclude={'name'}))
            if not filtered_tracks:
                return {"error": "No tracks available"}
            playlist_id = spotify_engine.create_playlist(request.name, filtered_tracks)
            return {"playlist_id": playlist_id, "tracks_count": len(filtered_tracks)}

        # Use a separate process to run blocking Spotify calls so we can reliably
        # terminate them on timeout (works on Windows). The worker must be a
        # top-level function to be picklable on Windows; we pass only simple
        # args (name and options dict).
        try:
            return do_create()
        except Exception as e:
            return {"error": str(e)}
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
    from config import settings
    from urllib.parse import urlparse

    parsed = urlparse(settings.spotify_redirect_uri)
    port = parsed.port or 8002
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")