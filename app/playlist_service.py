from dataclasses import asdict, replace
from datetime import datetime, timezone
import random

from .parse import JourneyOptions, generate_mood_journey
from .spotify_client import create_playlist


GENRES = {
    "any", "pop", "rock", "indie", "electronic", "hip-hop", "r-n-b",
    "jazz", "classical", "metal", "folk", "country", "latin", "ambient",
}


def prepare_mood_draft(spotify, form):
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
    generated = generate_mood_journey(options)
    name = form.get("playlist_name", "").strip() or (
        f"{options.start_mood.title()} → {options.end_mood.title()}"
    )
    genre_detail = f" · {genre} focus" if genre != "any" else ""
    description = (
        f"A {options.curve} mood journey made by Soul Train. "
        f"{options.track_count} tracks · {options.discovery}% discovery{genre_detail}."
    )
    return {
        "mode": "mood",
        "name": name[:100],
        "description": description[:300],
        "public": form.get("private") != "on",
        "options": asdict(options),
        "tracks": _enrich_generated_tracks(spotify, generated),
        "pinned": [],
    }


def prepare_library_draft(spotify, form):
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
    tracks = [
        _track_card(item["track"])
        for item in chosen
        if item.get("track") and item["track"].get("id")
    ]
    name = form.get("playlist_name", "").strip() or "Forgotten favorites"
    return {
        "mode": "library",
        "name": name[:100],
        "description": "Saved songs worth hearing again · made by Soul Train",
        "public": form.get("private") != "on",
        "options": {"track_count": count},
        "tracks": tracks,
        "pinned": [],
    }


def publish_draft(spotify, draft):
    return create_playlist(
        spotify,
        draft["name"][:100],
        draft["description"][:300],
        bool(draft["public"]),
        [track["id"] for track in draft["tracks"]],
    )


def replace_draft_track(spotify, draft, index):
    """Return a replacement card that is not already present in the draft."""
    if not 0 <= index < len(draft["tracks"]):
        raise ValueError("Choose a valid track to replace.")
    excluded_ids = {track["id"] for track in draft["tracks"]}
    excluded_titles = {track["name"].casefold() for track in draft["tracks"]}
    if draft["mode"] == "mood":
        options = JourneyOptions(**draft["options"])
        options = replace(options, seed=random.randrange(1, 2**31))
        candidates = generate_mood_journey(options, excluded_track_ids=excluded_ids)
        ordered = candidates[index:] + candidates[:index]
        generated = next(
            (track for track in ordered if track["name"].casefold() not in excluded_titles),
            ordered[0],
        )
        return _enrich_generated_tracks(spotify, [generated])[0]
    return _library_replacement(spotify, excluded_ids, excluded_titles)


def build_mood_playlist(spotify, form):
    """Backward-compatible immediate publishing helper."""
    draft = prepare_mood_draft(spotify, form)
    return publish_draft(spotify, draft), draft["tracks"]


def build_library_mix(spotify, form):
    """Backward-compatible immediate publishing helper."""
    draft = prepare_library_draft(spotify, form)
    return publish_draft(spotify, draft), draft["tracks"]


def _enrich_generated_tracks(spotify, generated):
    details = {}
    ids = [track["id"] for track in generated]
    for offset in range(0, len(ids), 50):
        response = spotify.tracks(ids[offset:offset + 50])
        for track in response.get("tracks", []):
            if track and track.get("id"):
                details[track["id"]] = track
    return [
        _track_card(details.get(track["id"], {}), fallback=track)
        for track in generated
    ]


def _library_replacement(spotify, excluded_ids, excluded_titles):
    items, offset = [], 0
    while len(items) < 500:
        page = spotify.current_user_saved_tracks(limit=50, offset=offset)
        items.extend(page.get("items", []))
        if not page.get("next"):
            break
        offset += 50
    candidates = [
        item for item in items
        if item.get("track")
        and item["track"].get("id") not in excluded_ids
        and item["track"].get("name", "").casefold() not in excluded_titles
    ]
    if not candidates:
        raise ValueError("There are no more saved tracks available to swap in.")
    candidates.sort(key=lambda item: item.get("added_at", ""))
    pool = candidates[:min(25, len(candidates))]
    return _track_card(random.choice(pool)["track"])


def _track_card(track, fallback=None):
    fallback = fallback or {}
    album = track.get("album") or {}
    images = album.get("images") or []
    artists = track.get("artists") or []
    return {
        "id": str(track.get("id") or fallback.get("id", "")),
        "name": track.get("name") or fallback.get("name", "Unknown track"),
        "artist": ", ".join(artist.get("name", "") for artist in artists) or fallback.get("artist", ""),
        "album": album.get("name", ""),
        "image": images[0].get("url") if images else None,
        "duration_ms": int(track.get("duration_ms") or fallback.get("duration_ms") or 0),
        "explicit": bool(track.get("explicit", fallback.get("explicit", False))),
        "url": (track.get("external_urls") or {}).get("spotify", ""),
        "release_date": album.get("release_date") or fallback.get("release_date", ""),
        "mood_scores": fallback.get("mood_scores", {}),
    }


def _integer(value, label):
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{label} must be a whole number.") from exc
