import os
import secrets

from flask import session
from spotipy.cache_handler import CacheHandler
from spotipy.oauth2 import SpotifyOAuth


SCOPES = " ".join(
    [
        "playlist-modify-public",
        "playlist-modify-private",
        "user-library-read",
        "user-read-private",
        "user-top-read",
    ]
)
SPOTIFY_ENV_KEYS = (
    "SPOTIPY_CLIENT_ID",
    "SPOTIPY_CLIENT_SECRET",
    "SPOTIPY_REDIRECT_URI",
)


class SessionCacheHandler(CacheHandler):
    """Store each visitor's Spotify token in their signed Flask session."""

    def get_cached_token(self):
        return session.get("spotify_token")

    def save_token_to_cache(self, token_info):
        session["spotify_token"] = token_info
        session.modified = True


def missing_spotify_configuration() -> list[str]:
    return [name for name in SPOTIFY_ENV_KEYS if not os.getenv(name)]


def spotify_is_configured() -> bool:
    return not missing_spotify_configuration()


def spotify_oauth() -> SpotifyOAuth:
    if not spotify_is_configured():
        raise RuntimeError("Spotify connection is not configured yet.")
    return SpotifyOAuth(
        scope=SCOPES,
        cache_handler=SessionCacheHandler(),
        open_browser=False,
        show_dialog=False,
    )


def new_oauth_state() -> str:
    state = secrets.token_urlsafe(24)
    session["spotify_oauth_state"] = state
    return state
