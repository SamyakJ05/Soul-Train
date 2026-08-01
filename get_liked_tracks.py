from time import time

import pandas as pd
import spotipy

from spotify_auth import spotify_oauth


FEATURE_KEYS = [
    "danceability", "energy", "key", "loudness", "mode", "speechiness",
    "acousticness", "instrumentalness", "liveness", "valence", "tempo",
]


def _windows(items, limit):
    for index in range(0, len(items), limit):
        yield items[index:index + limit]


def main():
    spotify = spotipy.Spotify(auth_manager=spotify_oauth("user-library-read"))
    tracks = []
    offset = 0
    while True:
        page = spotify.current_user_saved_tracks(offset=offset, limit=50)
        tracks.extend(
            {"name": item["track"]["name"], "id": item["track"]["id"]}
            for item in page["items"]
        )
        if page["next"] is None:
            break
        offset += 50

    enriched = []
    for window in _windows(tracks, 100):
        features = spotify.audio_features([track["id"] for track in window])
        for track, feature in zip(window, features):
            if feature:
                track.update({key: feature[key] for key in FEATURE_KEYS})
                enriched.append(track)

    filename = f"liked_tracks_{int(time())}.csv"
    pd.DataFrame(enriched).to_csv(filename, index=False)
    print(f"Saved features for {len(enriched)} tracks to {filename}")


if __name__ == "__main__":
    main()
