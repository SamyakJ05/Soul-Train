from datetime import datetime, timezone
import random

from parse import JourneyOptions, generate_mood_journey
from spotify_client import create_playlist


GENRES = {
    "any", "pop", "rock", "indie", "electronic", "hip-hop", "r-n-b",
    "jazz", "classical", "metal", "folk", "country", "latin", "ambient",
}


def build_mood_playlist(spotify, form):
    options = JourneyOptions(
        start_mood=form.get("start_mood", ""),
        end_mood=form.get("end_mood", ""),
        track_count=_integer(form.get("track_count", "30"), "Playlist length"),
        curve=form.get("curve", "smooth"),
        discovery=_integer(form.get("discovery", "35"), "Discovery"),
        era=form.get("era", "all"),
        allow_explicit=form.get("allow_explicit") == "on",
        genre=form.get("genre", "any"),
    )
    genre = form.get("genre", "any")
    if genre not in GENRES:
        raise ValueError("Choose a valid genre focus.")
    tracks = generate_mood_journey(options)
    name = form.get("playlist_name", "").strip() or (
        f"{options.start_mood.title()} → {options.end_mood.title()}"
    )
    genre_detail = f" · {genre} focus" if genre != "any" else ""
    description = (
        f"A {options.curve} mood journey made by Soul Train. "
        f"{options.track_count} tracks · {options.discovery}% discovery{genre_detail}."
    )
    playlist = create_playlist(
        spotify, name[:100], description[:300], form.get("private") != "on",
        [track["id"] for track in tracks],
    )
    return playlist, tracks


def build_library_mix(spotify, form):
    count = _integer(form.get("track_count", "30"), "Playlist length")
    if not 10 <= count <= 100:
        raise ValueError("Playlist length must be between 10 and 100 tracks.")
    pages, offset = [], 0
    while len(pages) < 500:
        page = spotify.current_user_saved_tracks(limit=50, offset=offset)
        pages.extend(page.get("items", []))
        if not page.get("next"):
            break
        offset += 50
    if len(pages) < count:
        raise ValueError(f"Your library needs at least {count} available tracks for this mix.")

    now = datetime.now(timezone.utc)
    # Older saves get a higher rediscovery weight; a small random term keeps mixes fresh.
    def score(item):
        added = datetime.fromisoformat(item["added_at"].replace("Z", "+00:00"))
        age = max((now - added).days, 0)
        return age + random.random() * 365

    chosen = sorted(pages, key=score, reverse=True)[:count]
    tracks = [item["track"] for item in chosen if item.get("track") and item["track"].get("id")]
    name = form.get("playlist_name", "").strip() or "Forgotten favorites"
    playlist = create_playlist(
        spotify, name[:100], "Saved songs worth hearing again · made by Soul Train", 
        form.get("private") != "on", [track["id"] for track in tracks],
    )
    return playlist, tracks


def _integer(value, label):
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{label} must be a whole number.") from exc
