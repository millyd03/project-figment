import spotipy
from spotipy.oauth2 import SpotifyOAuth
from config import settings
from database import SessionLocal, SpotifyToken
from typing import List, Dict, Optional
import random
from datetime import datetime, timedelta

class SpotifyRuleEngine:
    """
    Rule-based playlist curation engine for Spotify.
    Implements Followed-Only Filter, Tiered Artist Cap, and feature toggles.
    """

    def __init__(self):
        self.sp_oauth = SpotifyOAuth(
            client_id=settings.spotify_client_id,
            client_secret=settings.spotify_client_secret,
            redirect_uri="http://localhost:8002/callback",  # Updated port
            scope="user-follow-read playlist-modify-public user-top-read"
        )
        self.sp = None
        self._load_token()

    def _load_token(self):
        """Load token from database and create Spotify client"""
        db = SessionLocal()
        try:
            token_record = db.query(SpotifyToken).first()
            if token_record and token_record.expires_at:
                # Check if token is still valid
                if token_record.expires_at > datetime.utcnow():
                    token_info = {
                        'access_token': token_record.access_token,
                        'refresh_token': token_record.refresh_token,
                        'expires_at': token_record.expires_at.timestamp(),
                        'token_type': token_record.token_type,
                        'scope': token_record.scope
                    }
                    self.sp = spotipy.Spotify(auth=token_record.access_token)
                else:
                    # Try to refresh token
                    self._refresh_token(token_record.refresh_token)
            elif token_record:
                # Token without expiry, assume it's valid
                self.sp = spotipy.Spotify(auth=token_record.access_token)
        except Exception as e:
            print(f"Error loading token: {e}")
        finally:
            db.close()

    def _refresh_token(self, refresh_token):
        """Refresh the access token"""
        try:
            token_info = self.sp_oauth.refresh_access_token(refresh_token)
            self._save_token(token_info)
            self.sp = spotipy.Spotify(auth=token_info['access_token'])
        except Exception as e:
            print(f"Error refreshing token: {e}")

    def _save_token(self, token_info):
        """Save token to database"""
        db = SessionLocal()
        try:
            # Delete existing token
            db.query(SpotifyToken).delete()
            
            # Create new token record
            expires_at = None
            if 'expires_at' in token_info:
                expires_at = datetime.fromtimestamp(token_info['expires_at'])
            elif 'expires_in' in token_info:
                expires_at = datetime.utcnow() + timedelta(seconds=token_info['expires_in'])
            
            token_record = SpotifyToken(
                access_token=token_info['access_token'],
                refresh_token=token_info.get('refresh_token'),
                expires_at=expires_at,
                token_type=token_info.get('token_type', 'Bearer'),
                scope=token_info.get('scope')
            )
            db.add(token_record)
            db.commit()
        except Exception as e:
            print(f"Error saving token: {e}")
            db.rollback()
        finally:
            db.close()

    def is_authenticated(self):
        """Check if user is authenticated"""
        return self.sp is not None

    def get_followed_artists(self) -> Dict[str, int]:
        """
        Retrieve user's followed artists and their follower counts.
        Returns dict of artist_id: follower_count
        """
        if not self.is_authenticated():
            raise Exception("User not authenticated with Spotify")
        
        followed = {}
        results = self.sp.current_user_followed_artists(limit=50)
        while results:
            for artist in results['artists']['items']:
                followed[artist['id']] = artist['followers']['total']
            if results['artists']['cursors']['after']:
                results = self.sp.current_user_followed_artists(
                    after=results['artists']['cursors']['after'], limit=50
                )
            else:
                results = None
        return followed

    def get_tier_limit(self, follower_count: int) -> int:
        """
        Determine max tracks per artist based on follower count.
        """
        if follower_count <= 50000:
            return 1
        elif follower_count <= 500000:
            return 2
        elif follower_count <= 1000000:
            return 3
        elif follower_count <= 5000000:
            return 4
        elif follower_count <= 10000000:
            return 5
        else:
            return float('inf')  # No cap

    def apply_rules(self, tracks: List[Dict], followed_artists: Dict[str, int],
                   throwback: bool = False, fresh: bool = False,
                   tacno: bool = False, christmas: bool = False,
                   clean: bool = False) -> List[Dict]:
        """
        Apply all rules to filter and limit tracks.
        """
        # Followed-Only Filter
        filtered_tracks = [t for t in tracks if any(
            artist['id'] in followed_artists for artist in t.get('artists', [])
        )]

        # Feature Toggles
        if throwback:
            filtered_tracks = [t for t in filtered_tracks if t['album']['release_date'] < '2011-01-01']
        if fresh:
            # TODO: Implement sliding window for fresh
            pass
        if tacno:
            # TODO: Short-circuit to Covers playlist
            pass
        if christmas:
            # TODO: Short-circuit to Christmas playlist
            pass
        if clean:
            filtered_tracks = [t for t in filtered_tracks if not t.get('explicit', False)]

        # Tiered Artist Cap
        artist_counts = {}
        capped_tracks = []
        for track in filtered_tracks:
            for artist in track.get('artists', []):
                artist_id = artist['id']
                if artist_id in followed_artists:
                    current_count = artist_counts.get(artist_id, 0)
                    limit = self.get_tier_limit(followed_artists[artist_id])
                    if current_count < limit:
                        artist_counts[artist_id] = current_count + 1
                        capped_tracks.append(track)
                        break  # Only add once per track

        # Anti-Batching: Shuffle globally
        random.shuffle(capped_tracks)

        return capped_tracks

    def get_potential_tracks(self) -> List[Dict]:
        """
        Get potential tracks from followed artists' top tracks.
        """
        if not self.is_authenticated():
            raise Exception("User not authenticated with Spotify")
        
        followed_artists = self.get_followed_artists()
        tracks = []
        for artist_id in followed_artists.keys():
            try:
                top_tracks = self.sp.artist_top_tracks(artist_id, country='US')
                for track in top_tracks['tracks']:
                    tracks.append({
                        'id': track['id'],
                        'name': track['name'],
                        'artists': [{'id': artist['id'], 'name': artist['name']} for artist in track['artists']],
                        'album': {
                            'name': track['album']['name'],
                            'release_date': track['album']['release_date']
                        },
                        'uri': track['uri'],
                        'explicit': track['explicit']
                    })
            except Exception as e:
                print(f"Error getting tracks for artist {artist_id}: {e}")
        return tracks

    def create_playlist(self, name: str, tracks: List[Dict]) -> str:
        """
        Create a Spotify playlist with the given tracks.
        Returns playlist ID.
        """
        if not self.is_authenticated():
            raise Exception("User not authenticated with Spotify")
        
        try:
            user_id = self.sp.current_user()['id']
            playlist = self.sp.user_playlist_create(user_id, name, public=True)
            track_uris = [t['uri'] for t in tracks]
            self.sp.playlist_add_items(playlist['id'], track_uris)
            return playlist['id']
        except spotipy.exceptions.SpotifyException as e:
            if e.http_status == 401:  # Unauthorized, token might be expired
                # Try to refresh token
                db = SessionLocal()
                try:
                    token_record = db.query(SpotifyToken).first()
                    if token_record and token_record.refresh_token:
                        self._refresh_token(token_record.refresh_token)
                        # Retry the operation
                        user_id = self.sp.current_user()['id']
                        playlist = self.sp.user_playlist_create(user_id, name, public=True)
                        track_uris = [t['uri'] for t in tracks]
                        self.sp.playlist_add_items(playlist['id'], track_uris)
                        return playlist['id']
                except Exception as refresh_error:
                    print(f"Error refreshing token: {refresh_error}")
                finally:
                    db.close()
            raise e