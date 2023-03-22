from flask import Flask, request, render_template, redirect
import pandas as pd
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from parse import make_playlist
from unsupervised import playtwist

app = Flask(__name__)


@app.route('/')
def page():
    return render_template('page.html')


@app.route('/aboutus')
def aboutus():
    return render_template('aboutus.html')


@app.route('/discover')
def discover():
    return render_template('discover.html')

@app.route('/genre')
def genre():
    return render_template('genre.html')


@app.route('/mood gradient')
def my_form():
    my_form_post()
    return render_template('mood gradient.html')

@app.route('/playlistinspire')
def my_form2():
    my_form_post2()
    return render_template('playlistinspire.html')


@app.route('/mood gradient', methods=['POST', 'GET'])
def my_form_post():
    if request.method == 'POST':
        mood1 = request.form['mood1']
        mood2 = request.form['mood2']
        pid = make_playlist(mood1, mood2)
        return redirect(f'https://open.spotify.com/playlist/{pid}')

@app.route('/playlistinspire', methods=['POST', 'GET'])
def my_form_post2():
    if request.method == 'POST':
        pid2 = playtwist()
        return redirect(f'https://open.spotify.com/playlist/{pid2}')

if __name__ == "__main__":
    app.run(debug=True, port=5001)
