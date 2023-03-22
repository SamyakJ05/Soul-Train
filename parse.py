import pandas as pd
import spotipy
from spotipy.oauth2 import SpotifyOAuth


# from flask import Flask, request, render_template
#
# app = Flask(__name__)
#
#
# @app.route('/')
# def my_form():
#     return render_template('mood gradient.html')
#
#
# @app.route('/', methods=['POST'])
# def my_form_post():
#     mood1 = request.form['mood1']
#     mood2 = request.form['mood2']
#     return mood1, mood2
#
#
# if __name__ == "__main__":
#     app.run(debug=True, port=5001)
def make_playlist(m1, m2):
    pd.set_option('display.max_columns', 10)
    pd.set_option('display.max_rows', 10000)

    client_id = "c91fd423291d43589c9f088704523cb8"
    client_secret = "e238259638cf4d54acb1e7d165fd7d50"
    redirect_uri = 'http://localhost:9001/callback'

    mood2, mood1 = m1, m2
    songs = pd.read_csv('fin_nogenre.csv', header=None)
    songs.columns = ["Name", "Explicit", "ReleaseDate", "Duration", "id", "sad", "chill", "happy", "hype"]
    songs2 = songs.sample(frac=0.001).reset_index()
    songs2 = songs2.loc[songs2['Explicit'] == False]
    songs2.to_csv('songs2.csv', index=False)
    new_songs = pd.read_csv('songs2.csv')
    new_songs = new_songs.loc[new_songs[mood1] + new_songs[mood2] > 0.9]
    happy_songs = new_songs[(new_songs[mood1] >= 0.5)]
    sad_songs = new_songs[(new_songs[mood2] >= 0.5)]
    happy = happy_songs.sample(frac=0.3).sort_values(mood1).reset_index()
    sad = sad_songs.sample(frac=0.3).sort_values(mood2, ascending=False).reset_index()
    # new_songs = new_songs.sort_values(["happy", "sad"], ascending=[1, 0])[["Name", "id", "sad", "happy"]]
    playlist_songs = []
    song_names = []
    # print(happy_songs)
    # print(sad_songs)

    for index, row in sad.iterrows():
        playlist_songs.append(row['id'])
        song_names.append(row['Name'])
        # print(index, row['Name'], row['id'], row['sad'], row['happy'])
        if len(playlist_songs) == 50:
            break
    for index, row in happy.iterrows():
        playlist_songs.append(row['id'])
        song_names.append(row['Name'])
        # print(index, row['Name'], row['id'], row['sad'], row['happy'])
        if len(playlist_songs) == 100:
            break

    print(playlist_songs)
    print(song_names)
    sp = spotipy.Spotify(auth_manager=SpotifyOAuth(client_id=client_id,
                                                   client_secret=client_secret,
                                                   redirect_uri=redirect_uri,
                                                   scope="playlist-modify-public"))

    user_id = sp.current_user()['id']
    playlist_id = sp.user_playlist_create(user_id, f"Mood Gradient: {mood1} to {mood2}")['id']
    sp.playlist_add_items(playlist_id, playlist_songs)
    return playlist_id


# for i in range(len(sad_songs.index)):
#     playlist_songs.append(sad_songs['id'].str.get(i))
#     i += random.randint(1, 2)
#     if len(playlist_songs) == 50:
#         break
# for i in range(len(happy_songs.index)):
#     playlist_songs.append(sad_songs['id'].str.get(i))
#     i += random.randint(1, 2)
#     if len(playlist_songs) == 50:
#         break
