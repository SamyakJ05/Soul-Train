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


def genre_track_ids(spotify, genre: str, needed: int) -> set[str]:
    """Fetch a genre candidate pool using Spotify Search's current 10-item pages."""
    found = set()
    offset = 0
    target = min(max(needed * 3, 60), 300)
    while len(found) < target and offset <= 1000:
        results = spotify.search(q=f"genre:{genre}", type="track", limit=10, offset=offset)
        page = results.get("tracks", {})
        items = page.get("items", [])
        found.update(str(track["id"]) for track in items if track.get("id"))
        if not items or not page.get("next"):
            break
        offset += 10
    return found
