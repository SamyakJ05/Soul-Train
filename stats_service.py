from collections import Counter


TIME_RANGES = {"short_term", "medium_term", "long_term"}


def listening_stats(spotify, time_range: str) -> dict:
    if time_range not in TIME_RANGES:
        time_range = "medium_term"
    tracks = spotify.current_user_top_tracks(limit=20, time_range=time_range).get("items", [])
    artists = spotify.current_user_top_artists(limit=20, time_range=time_range).get("items", [])

    genres = Counter(
        genre
        for artist in artists
        for genre in artist.get("genres", [])
    )
    artist_names = {
        artist.get("name")
        for track in tracks
        for artist in track.get("artists", [])
        if artist.get("name")
    }
    return {
        "time_range": time_range,
        "tracks": [_track_card(track, index + 1) for index, track in enumerate(tracks[:10])],
        "artists": [_artist_card(artist, index + 1) for index, artist in enumerate(artists[:10])],
        "top_genres": genres.most_common(6),
        "unique_artists": len(artist_names),
        "top_track_minutes": round(sum(track.get("duration_ms", 0) for track in tracks) / 60000),
    }


def _track_card(track, rank):
    album = track.get("album") or {}
    images = album.get("images") or []
    return {
        "rank": rank,
        "name": track.get("name", "Unknown track"),
        "artist": ", ".join(artist.get("name", "") for artist in track.get("artists", [])),
        "image": images[0].get("url") if images else None,
        "url": (track.get("external_urls") or {}).get("spotify", "#"),
    }


def _artist_card(artist, rank):
    images = artist.get("images") or []
    return {
        "rank": rank,
        "name": artist.get("name", "Unknown artist"),
        "image": images[0].get("url") if images else None,
        "url": (artist.get("external_urls") or {}).get("spotify", "#"),
    }
