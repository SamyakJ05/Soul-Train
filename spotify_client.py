import spotipy

from spotify_auth import spotify_oauth


def connected_spotify() -> spotipy.Spotify:
    auth = spotify_oauth()
    token = auth.validate_token(auth.cache_handler.get_cached_token())
    if not token:
        raise RuntimeError("Connect Spotify to create a playlist.")
    return spotipy.Spotify(auth_manager=auth)


def create_playlist(spotify, name, description, public, track_ids):
    """Use Spotify's current 2026 playlist endpoints."""
    playlist = spotify._post(
        "me/playlists",
        payload={"name": name, "description": description, "public": public},
    )
    uris = [track if track.startswith("spotify:") else f"spotify:track:{track}" for track in track_ids]
    for index in range(0, len(uris), 100):
        spotify._post(
            f"playlists/{playlist['id']}/items",
            payload={"uris": uris[index:index + 100]},
        )
    return playlist
