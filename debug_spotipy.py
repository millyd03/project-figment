import spotipy
from spotipy import oauth2
import inspect
print('spotipy version', spotipy.__version__)
print('has SpotifyPKCE', hasattr(oauth2, 'SpotifyPKCE'))
print('has SpotifyOAuth', hasattr(oauth2, 'SpotifyOAuth'))
print('SpotifyOAuth sig', inspect.signature(oauth2.SpotifyOAuth))
print('SpotifyPKCE sig', inspect.signature(oauth2.SpotifyPKCE) if hasattr(oauth2, 'SpotifyPKCE') else 'None')
