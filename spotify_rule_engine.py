import spotipy
import requests
from config import settings
from database import SessionLocal, SpotifyToken
from typing import List, Dict, Optional
import random
from datetime import datetime, timedelta
from crypto import encrypt_value, decrypt_value, is_enabled

class SpotifyRuleEngine:
    """
    Rule-based playlist curation engine for Spotify.
    Implements Followed-Only Filter, Tiered Artist Cap, and profile-aware token management.
    """

    def __init__(self):
        self.client_id = settings.spotify_client_id
        self.client_secret = settings.spotify_client_secret
        self.redirect_uri = settings.spotify_redirect_uri
        self.scopes = "user-follow-read playlist-modify-public user-top-read"
        self.token_url = "https://accounts.spotify.com/api/token"
        self.sp = None
        self.active_profile = None
        self.active_profile_id = None
        self._load_active_profile()
        self._rate_limited_until = None

    def _load_active_profile(self):
        db = SessionLocal()
        try:
            token_record = db.query(SpotifyToken).filter(SpotifyToken.is_active == True).first()
            if not token_record:
                token_record = db.query(SpotifyToken).first()
            if token_record:
                self._activate_profile(token_record)
                # Decrypt refresh token into memory (if encrypted)
                if token_record.refresh_token and is_enabled():
                    try:
                        token_record._decrypted_refresh_token = decrypt_value(token_record.refresh_token)
                    except Exception:
                        token_record._decrypted_refresh_token = token_record.refresh_token
                else:
                    token_record._decrypted_refresh_token = token_record.refresh_token

                if self._is_token_expired():
                    self._refresh_active_profile()
            else:
                self.sp = None
                self.active_profile = None
                self.active_profile_id = None
        except Exception as e:
            print(f"Error loading active profile: {e}")
        finally:
            db.close()

    def _activate_profile(self, token_record: SpotifyToken):
        self.active_profile = token_record
        self.active_profile_id = token_record.id
        self.sp = spotipy.Spotify(auth=token_record.access_token) if token_record.access_token else None

    def _is_token_expired(self) -> bool:
        if not self.active_profile or not self.active_profile.expires_at:
            return False
        return self.active_profile.expires_at <= datetime.utcnow() + timedelta(seconds=60)

    def _ensure_valid_token(self) -> bool:
        if not self.active_profile:
            return False
        if self._is_token_expired():
            return self._refresh_active_profile()
        return self.sp is not None

    # Public wrapper to ensure token validity for external callers
    def ensure_valid_token(self) -> bool:
        return self._ensure_valid_token()

    def _refresh_active_profile(self) -> bool:
        if not self.active_profile or not self.active_profile.refresh_token:
            return False
        refresh_token = getattr(self.active_profile, '_decrypted_refresh_token', None) or self.active_profile.refresh_token
        return self._refresh_token(refresh_token, profile_id=self.active_profile.id)

    # Public helper to trigger a refresh for the active profile
    def refresh_active_profile(self) -> bool:
        return self._refresh_active_profile()

    def _request_token(self, *, code: Optional[str] = None, code_verifier: Optional[str] = None, refresh_token: Optional[str] = None) -> Dict:
        if code is None and refresh_token is None:
            raise ValueError("Either code or refresh_token must be provided")

        data = {"client_id": self.client_id}
        if code is not None:
            data.update({
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": self.redirect_uri,
                "code_verifier": code_verifier,
            })
        else:
            data.update({
                "grant_type": "refresh_token",
                "refresh_token": refresh_token,
            })

        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        response = requests.post(self.token_url, data=data, headers=headers)
        response.raise_for_status()
        return response.json()

    def _refresh_token(self, refresh_token: str, profile_id: Optional[int] = None) -> bool:
        try:
            token_info = self._request_token(refresh_token=refresh_token)
            self._save_token(token_info, profile_id=profile_id, activate=True)
            return True
        except Exception as e:
            self._log_spotify_error("refresh_token", e)
            # If we were rate limited, set a cooldown to avoid repeated calls
            msg = str(e).lower()
            if 'rate' in msg or '429' in msg:
                try:
                    self._rate_limited_until = datetime.utcnow() + timedelta(seconds=60)
                    print(f"Spotify rate-limited; pausing calls until {self._rate_limited_until.isoformat()}")
                except Exception:
                    pass
            self.sp = None
            return False

    def _save_token(self,
                    token_info: Dict,
                    profile_id: Optional[int] = None,
                    profile_name: Optional[str] = None,
                    profile_key: Optional[str] = None,
                    spotify_user_id: Optional[str] = None,
                    display_name: Optional[str] = None,
                    activate: bool = True):
        db = SessionLocal()
        try:
            if profile_id:
                token_record = db.query(SpotifyToken).filter(SpotifyToken.id == profile_id).first()
            elif spotify_user_id:
                token_record = db.query(SpotifyToken).filter(SpotifyToken.spotify_user_id == spotify_user_id).first()
            else:
                token_record = None

            if activate:
                db.query(SpotifyToken).update({SpotifyToken.is_active: False})

            if not token_record:
                token_record = SpotifyToken()

            token_record.profile_name = profile_name or token_record.profile_name or display_name or spotify_user_id or "Spotify Profile"
            token_record.profile_key = profile_key or token_record.profile_key or spotify_user_id or str(datetime.utcnow().timestamp())
            token_record.spotify_user_id = spotify_user_id or token_record.spotify_user_id
            token_record.display_name = display_name or token_record.display_name or token_record.profile_name
            token_record.access_token = token_info['access_token']
            raw_refresh = token_info.get('refresh_token') or token_record.refresh_token
            if raw_refresh and is_enabled():
                try:
                    token_record.refresh_token = encrypt_value(raw_refresh)
                except Exception:
                    token_record.refresh_token = raw_refresh
            else:
                token_record.refresh_token = raw_refresh
            expires_at = None
            if 'expires_at' in token_info:
                expires_at = datetime.fromtimestamp(token_info['expires_at'])
            elif 'expires_in' in token_info:
                expires_at = datetime.utcnow() + timedelta(seconds=token_info['expires_in'])
            token_record.expires_at = expires_at
            token_record.token_type = token_info.get('token_type', 'Bearer')
            token_record.scope = token_info.get('scope', token_record.scope)
            token_record.is_active = activate
            token_record.updated_at = datetime.utcnow()
            if not token_record.created_at:
                token_record.created_at = datetime.utcnow()

            db.add(token_record)
            db.commit()
            db.refresh(token_record)
            self._activate_profile(token_record)
            # Store decrypted refresh token on the active_profile in memory
            if token_record.refresh_token and is_enabled():
                try:
                    token_record._decrypted_refresh_token = decrypt_value(token_record.refresh_token)
                except Exception:
                    token_record._decrypted_refresh_token = token_record.refresh_token
            else:
                token_record._decrypted_refresh_token = token_record.refresh_token
        except Exception as e:
            print(f"Error saving token: {e}")
            db.rollback()
            self.sp = None
            self.active_profile = None
            self.active_profile_id = None
        finally:
            db.close()

    def create_profile(self, token_info: Dict, desired_name: Optional[str] = None, state: Optional[str] = None, profile_id: Optional[int] = None):
        spotify_client = spotipy.Spotify(auth=token_info['access_token'])
        user = spotify_client.current_user()
        spotify_user_id = user.get('id')
        display_name = user.get('display_name') or spotify_user_id
        chosen_name = desired_name or (state if state and not state.isdigit() else None) or display_name
        self._save_token(
            token_info,
            profile_id=profile_id,
            profile_name=chosen_name,
            profile_key=spotify_user_id,
            spotify_user_id=spotify_user_id,
            display_name=display_name,
            activate=True
        )
        return self.active_profile

    def is_authenticated(self):
        """Check if user is authenticated"""
        return self._ensure_valid_token()

    def get_active_profile_summary(self) -> Optional[Dict]:
        if not self.active_profile:
            return None
        return {
            'id': self.active_profile.id,
            'profile_name': self.active_profile.profile_name,
            'profile_key': self.active_profile.profile_key,
            'spotify_user_id': self.active_profile.spotify_user_id,
            'display_name': self.active_profile.display_name,
            'expires_at': self.active_profile.expires_at.isoformat() if self.active_profile.expires_at else None,
            'is_active': self.active_profile.is_active
        }

    def get_profiles(self) -> List[Dict]:
        db = SessionLocal()
        try:
            profiles = db.query(SpotifyToken).all()
            return [
                {
                    'id': profile.id,
                    'profile_name': profile.profile_name,
                    'profile_key': profile.profile_key,
                    'spotify_user_id': profile.spotify_user_id,
                    'display_name': profile.display_name,
                    'expires_at': profile.expires_at.isoformat() if profile.expires_at else None,
                    'is_active': profile.is_active
                }
                for profile in profiles
            ]
        finally:
            db.close()

    def activate_profile(self, profile_id: int) -> bool:
        db = SessionLocal()
        try:
            profile = db.query(SpotifyToken).filter(SpotifyToken.id == profile_id).first()
            if not profile:
                return False
            db.query(SpotifyToken).update({SpotifyToken.is_active: False})
            profile.is_active = True
            db.add(profile)
            db.commit()
            self._activate_profile(profile)
            if self._is_token_expired():
                return self._refresh_active_profile()
            return True
        except Exception as e:
            print(f"Error activating profile: {e}")
            return False

    def get_followed_artists(self) -> Dict[str, int]:
        """
        Retrieve user's followed artists and their follower counts.
        Returns dict of artist_id: follower_count
        """
        # Fail-safe: if not authenticated, return empty mapping so callers can continue
        if not self.is_authenticated():
            print("Warning: Spotify not authenticated when fetching followed artists; returning empty list")
            return {}

        # If we're currently rate-limited, return empty mapping immediately
        if self._rate_limited_until and datetime.utcnow() < self._rate_limited_until:
            print(f"Skipping followed artists fetch due to recent rate limit; until {self._rate_limited_until.isoformat()}")
            return {}

        followed = {}
        try:
            results = self.sp.current_user_followed_artists(limit=50)
            while results:
                for artist in results['artists']['items']:
                    followed[artist['id']] = artist['followers']['total']
                if results['artists']['cursors'].get('after'):
                    results = self.sp.current_user_followed_artists(
                        after=results['artists']['cursors']['after'], limit=50
                    )
                else:
                    results = None
        except Exception as e:
            self._log_spotify_error("get_followed_artists", e)
            msg = str(e).lower()
            if 'rate' in msg or '429' in msg:
                try:
                    self._rate_limited_until = datetime.utcnow() + timedelta(seconds=60)
                    print(f"Spotify rate-limited; pausing calls until {self._rate_limited_until.isoformat()}")
                except Exception:
                    pass
            return {}
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
                   clean: bool = False, **kwargs) -> List[Dict]:
        """
        Apply all rules to filter and limit tracks.
        """
        filtered_tracks = [t for t in tracks if any(
            artist['id'] in followed_artists for artist in t.get('artists', [])
        )]

        if throwback:
            filtered_tracks = [t for t in filtered_tracks if t['album']['release_date'] < '2011-01-01']
        if fresh:
            pass
        if tacno:
            pass
        if christmas:
            pass
        if clean:
            filtered_tracks = [t for t in filtered_tracks if not t.get('explicit', False)]

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
                        break

        random.shuffle(capped_tracks)
        return capped_tracks

    def get_potential_tracks(self) -> List[Dict]:
        """
        Get potential tracks from followed artists' top tracks.
        """
        # Fail-safe: if not authenticated, return empty list so callers can continue
        if not self.is_authenticated():
            print("Warning: Spotify not authenticated when fetching potential tracks; returning empty list")
            return []

        # Respect recent rate-limit state
        if self._rate_limited_until and datetime.utcnow() < self._rate_limited_until:
            print(f"Skipping potential tracks fetch due to recent rate limit; until {self._rate_limited_until.isoformat()}")
            return []

        followed_artists = self.get_followed_artists()
        if not followed_artists:
            return []

        tracks = []
        for artist_id in list(followed_artists.keys()):
            try:
                top_tracks = self.sp.artist_top_tracks(artist_id, country='US')
                for track in top_tracks.get('tracks', []):
                    tracks.append({
                        'id': track.get('id'),
                        'name': track.get('name'),
                        'artists': [{'id': artist.get('id'), 'name': artist.get('name')} for artist in track.get('artists', [])],
                        'album': {
                            'name': track.get('album', {}).get('name'),
                            'release_date': track.get('album', {}).get('release_date')
                        },
                        'uri': track.get('uri'),
                        'explicit': track.get('explicit', False)
                    })
            except Exception as e:
                self._log_spotify_error(f"artist_top_tracks:{artist_id}", e)
                msg = str(e).lower()
                if 'rate' in msg or '429' in msg:
                    try:
                        self._rate_limited_until = datetime.utcnow() + timedelta(seconds=60)
                        print(f"Spotify rate-limited; pausing calls until {self._rate_limited_until.isoformat()}")
                        # Stop trying further artists during rate-limit
                        break
                    except Exception:
                        pass
                # Otherwise continue to next artist
                continue
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
            if e.http_status == 401:
                if self._refresh_active_profile():
                    user_id = self.sp.current_user()['id']
                    playlist = self.sp.user_playlist_create(user_id, name, public=True)
                    track_uris = [t['uri'] for t in tracks]
                    self.sp.playlist_add_items(playlist['id'], track_uris)
                    return playlist['id']
            self._log_spotify_error('create_playlist', e)
            raise e

    def _log_spotify_error(self, context: str, exc: Exception):
        """Log Spotify-related exceptions with as much detail as possible (status, text)."""
        try:
            # requests HTTP errors often have .response
            resp = getattr(exc, 'response', None)
            if resp is not None:
                try:
                    body = resp.text
                except Exception:
                    body = str(resp)
                print(f"Spotify error [{context}] status={getattr(resp, 'status_code', 'n/a')} body={body}")
                return
        except Exception:
            pass
        try:
            # spotipy exceptions may have http_status
            status = getattr(exc, 'http_status', None)
            msg = getattr(exc, 'msg', None) or str(exc)
            if status is not None:
                print(f"Spotify error [{context}] status={status} msg={msg}")
                return
        except Exception:
            pass
        print(f"Spotify error [{context}]: {exc}")
