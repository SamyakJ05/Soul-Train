from pathlib import Path

import pandas as pd
import spotipy
from sklearn.cluster import KMeans

from spotify_auth import spotify_oauth


NUM_CLUSTERS = 5
TRACK_ADD_LIMIT = 100
FEATURE_KEYS = [
    "danceability", "energy", "key", "loudness", "mode", "speechiness",
    "acousticness", "instrumentalness", "liveness", "valence", "tempo",
]
TRACKS_FILE = Path(__file__).with_name("liked_tracks_1669386403.csv")


def _track_windows(track_ids, limit=TRACK_ADD_LIMIT):
    for index in range(0, len(track_ids), limit):
        yield track_ids[index:index + limit]


def playtwist() -> str:
    if not TRACKS_FILE.exists():
        raise FileNotFoundError(f"Liked-tracks file not found: {TRACKS_FILE.name}")

    tracks = pd.read_csv(TRACKS_FILE).dropna(subset=FEATURE_KEYS + ["id"])
    if len(tracks) < NUM_CLUSTERS:
        raise ValueError(f"At least {NUM_CLUSTERS} tracks with audio features are required.")

    model = KMeans(n_clusters=NUM_CLUSTERS, random_state=0, n_init="auto")
    tracks["cluster"] = model.fit_predict(tracks[FEATURE_KEYS])

    spotify = spotipy.Spotify(auth_manager=spotify_oauth("playlist-modify-public"))
    user_id = spotify.current_user()["id"]
    playlist_ids = []
    for cluster, group in tracks.groupby("cluster"):
        playlist = spotify.user_playlist_create(user_id, f"Playtwist {cluster + 1}")
        playlist_ids.append(playlist["id"])
        for window in _track_windows(group["id"].astype(str).tolist()):
            spotify.playlist_add_items(playlist["id"], window)

    return playlist_ids[0]
