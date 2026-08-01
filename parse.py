from pathlib import Path

import pandas as pd
import spotipy

from spotify_auth import spotify_oauth


MOODS = {"sad", "chill", "happy", "hype"}
DATA_ARCHIVE = Path(__file__).with_name("fin_nogenre.zip")
COLUMNS = [
    "Name", "Explicit", "ReleaseDate", "Duration", "id",
    "sad", "chill", "happy", "hype",
]


def make_playlist(start_mood: str, end_mood: str, track_count: int = 50) -> str:
    if start_mood not in MOODS or end_mood not in MOODS:
        raise ValueError("Choose a valid start and end mood.")
    if start_mood == end_mood:
        raise ValueError("Start and end moods must be different.")
    if not 1 <= track_count <= 100:
        raise ValueError("Track count must be between 1 and 100.")
    if not DATA_ARCHIVE.exists():
        raise FileNotFoundError(f"Dataset archive not found: {DATA_ARCHIVE.name}")

    songs = pd.read_csv(DATA_ARCHIVE, header=None, names=COLUMNS)
    songs = songs.loc[~songs["Explicit"].astype(bool)]
    candidates = songs.loc[songs[start_mood] + songs[end_mood] > 0.9]
    if candidates.empty:
        raise RuntimeError("No songs matched those moods. Try another combination.")

    midpoint = track_count // 2
    start = candidates.nlargest(max(midpoint, 1), start_mood).sort_values(start_mood)
    end = candidates.nlargest(track_count - len(start), end_mood).sort_values(
        end_mood, ascending=False
    )
    track_ids = (
        pd.concat([start, end])["id"].dropna().astype(str).drop_duplicates().tolist()
    )
    if not track_ids:
        raise RuntimeError("No playable tracks matched those moods.")

    spotify = spotipy.Spotify(auth_manager=spotify_oauth("playlist-modify-public"))
    user_id = spotify.current_user()["id"]
    playlist = spotify.user_playlist_create(
        user_id, f"Mood Gradient: {start_mood} to {end_mood}"
    )
    spotify.playlist_add_items(playlist["id"], track_ids)
    return playlist["id"]
