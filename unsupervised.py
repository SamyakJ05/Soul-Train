from pandas import read_csv
from sklearn.cluster import KMeans
import matplotlib.pyplot as plt
from sklearn.manifold import TSNE
import numpy as np
def playtwist():
    NUM_CLUSTERS = 5
    TRACK_ADD_LIMIT = 100
    COLORS = ['#e52165', '#0d1137', '#077b8a', '#5c3c92', '#1b6535']
    COLOR_MAP = {0: COLORS[0], 1: COLORS[1], 2: COLORS[2], 3: COLORS[3], 4: COLORS[4]}
    FEATURE_KEYS = ['danceability', 'energy', 'key', 'loudness', 'mode', 'speechiness', 'acousticness', 'instrumentalness',
                    'liveness', 'valence', 'tempo']

    df = read_csv('liked_tracks_1669386403.csv')

    kmeans = KMeans(n_clusters=NUM_CLUSTERS, random_state=0)
    df['cluster'] = kmeans.fit_predict(df[FEATURE_KEYS])
    df['color'] = df.cluster.map(COLOR_MAP)

    tsne = TSNE(n_components=2, random_state=0)
    np.set_printoptions(suppress=True)
    Y = tsne.fit_transform(df[FEATURE_KEYS].values)
    df['x_coords'] = Y[:, 0]
    df['y_coords'] = Y[:, 1]
    plt.scatter(df.x_coords, df.y_coords, c=df.color, alpha=0.6, s=10)
    plt.show()

    import spotipy
    from spotipy.oauth2 import SpotifyOAuth

    client_id = "c91fd423291d43589c9f088704523cb8"
    client_secret = "e238259638cf4d54acb1e7d165fd7d50"
    redirect_uri = 'http://localhost:9001/callback'

    sp = spotipy.Spotify(auth_manager=SpotifyOAuth(client_id=client_id,
                                                   client_secret=client_secret,
                                                   redirect_uri=redirect_uri,
                                                   scope="playlist-modify-public"))

    user_id = sp.current_user()['id']

    g = df.groupby('cluster')


    def get_windowed_track_ids(track_ids, limit):
        for i in range(0, len(track_ids), limit):
            track_window = track_ids[i:i + limit]
            yield track_window


    for cluster in range(NUM_CLUSTERS):
        _cluster_name = f'auto_cluster_{cluster}'
        playlist_id = sp.user_playlist_create(user_id, _cluster_name)['id']
        print(f'Created playlist {_cluster_name}')
        for _tracks in get_windowed_track_ids(list(g.get_group(cluster)['id']), TRACK_ADD_LIMIT):
            sp.playlist_add_items(playlist_id, _tracks)
            print(f'Added {len(_tracks)} tracks to playlist {_cluster_name}')
    return playlist_id