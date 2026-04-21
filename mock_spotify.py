from typing import List, Dict, Optional
from datetime import datetime, timedelta


class MockSpotifyRuleEngine:
    def __init__(self):
        self._rate_limited_until = None
        self.active_profile = {'id': 1, 'profile_name': 'mock', 'spotify_user_id': 'mock_user'}

    def is_authenticated(self):
        return True

    def get_active_profile_summary(self):
        return self.active_profile

    def get_profiles(self):
        return [self.active_profile]

    def get_potential_tracks(self) -> List[Dict]:
        # Return a couple of deterministic mock tracks
        return [
            {
                'id': 'track1',
                'name': 'Mock Song 1',
                'artists': [{'id': 'artist1', 'name': 'Mock Artist'}],
                'album': {'name': 'Mock Album', 'release_date': '2000-01-01'},
                'uri': 'spotify:track:mock1',
                'explicit': False
            },
            {
                'id': 'track2',
                'name': 'Mock Song 2',
                'artists': [{'id': 'artist2', 'name': 'Mock Artist 2'}],
                'album': {'name': 'Mock Album 2', 'release_date': '2020-01-01'},
                'uri': 'spotify:track:mock2',
                'explicit': False
            }
        ]

    def get_followed_artists(self) -> Dict[str, int]:
        return {'artist1': 1000, 'artist2': 200000}

    def apply_rules(self, tracks, followed_artists, **kwargs):
        # Simple filter: only include tracks whose first artist in followed_artists
        out = []
        for t in tracks:
            for a in t.get('artists', []):
                if a['id'] in followed_artists:
                    out.append(t)
                    break
        return out

    def create_playlist(self, name: str, tracks: List[Dict]) -> str:
        # Return a fake playlist id
        return f"mock_playlist_{int(datetime.utcnow().timestamp())}"

    def activate_profile(self, profile_id: int) -> bool:
        return True

    def refresh_active_profile(self) -> bool:
        return True
