import spotipy
from spotipy.oauth2 import SpotifyOAuth
from pandas import DataFrame
from time import time

FEATURE_KEYS = ['danceability', 'energy', 'key', 'loudness', 'mode', 'speechiness', 'acousticness', 'instrumentalness',
                'liveness', 'valence', 'tempo']
OFFSET = 0
SAVED_TRACKS_LIMIT = 50
FEATURE_LIMIT = 100

client_id = "c91fd423291d43589c9f088704523cb8"
client_secret = "e238259638cf4d54acb1e7d165fd7d50"
redirect_uri = 'http://localhost:9001/callback'

sp = spotipy.Spotify(auth_manager=SpotifyOAuth(client_id=client_id,
                                               client_secret=client_secret,
                                               redirect_uri=redirect_uri,
                                               scope="user-library-read"))

liked_tracks = list()
print('')

while (True):
    paged_tracks = sp.current_user_saved_tracks(offset=OFFSET, limit=SAVED_TRACKS_LIMIT)
    liked_tracks.extend([{'name': el['track']['name'], 'id': el['track']['id']} for el in paged_tracks['items']])
    print(f'Fetched {len(liked_tracks)} tracks')
    OFFSET += SAVED_TRACKS_LIMIT
    if paged_tracks['next'] is None:
        break


def get_windowed_track_ids(liked_tracks, limit):
    for i in range(0, len(liked_tracks), limit):
        track_window = liked_tracks[i:i + limit]
        yield track_window, [t['id'] for t in track_window]


track_feature_list = list()
print('')

for track_window, track_window_ids in get_windowed_track_ids(liked_tracks, FEATURE_LIMIT):
    track_features = sp.audio_features(tracks=track_window_ids)
    for index, _track in enumerate(track_window):
        _track.update({k: v for k, v in track_features[index].items() if k in FEATURE_KEYS})
        track_feature_list.append(_track)
    print(f'Fetched features for {len(track_feature_list)} tracks')

df = DataFrame.from_dict(track_feature_list)
filename = f'liked_tracks_{int(time())}.csv'
df.to_csv(filename, index=False)
print('')
print(f'Saved features to {filename}')
