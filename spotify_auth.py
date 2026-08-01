import os

from spotipy.oauth2 import SpotifyOAuth


def spotify_oauth(scope: str) -> SpotifyOAuth:
    missing = [
        name
        for name in ("SPOTIPY_CLIENT_ID", "SPOTIPY_CLIENT_SECRET", "SPOTIPY_REDIRECT_URI")
        if not os.getenv(name)
    ]
    if missing:
        raise RuntimeError(f"Missing Spotify configuration: {', '.join(missing)}")
    return SpotifyOAuth(scope=scope)
