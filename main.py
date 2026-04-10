from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session
from database import get_db
from spotify_rule_engine import SpotifyRuleEngine
from disney_engine import DisneyIntelligenceEngine
from llm_gateway import get_llm_response
from pydantic import BaseModel
from typing import List, Dict, Optional

app = FastAPI(
    title="Project FIGMENT",
    description="A personal agentic hub for Disney and Spotify.",
    version="0.1.0",
)

# Initialize Google ADK
# vertexai.init(project="your-project-id", location="us-central1")  # TODO: Configure with actual project

# Initialize engines
spotify_engine = SpotifyRuleEngine()
disney_engine = DisneyIntelligenceEngine()

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