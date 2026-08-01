# Soul Train

Soul Train is a Flask app that creates Spotify playlists from mood scores or clusters from a user's liked tracks.

## Setup

1. Create a virtual environment and install `requirements.txt`.
2. Copy `.env.example` to `.env` and provide credentials from a Spotify developer app.
3. Export the `.env` values in your shell, then run `python app.py`.
4. Open <http://127.0.0.1:5001>.

The Spotify redirect URI configured in the developer dashboard must match
`SPOTIPY_REDIRECT_URI`. The mood dataset stays compressed as `fin_nogenre.zip` and
is read directly by pandas.

## Security

Credentials must never be committed. Any credentials previously stored in this
repository should be rotated in the Spotify developer dashboard because removing
them from the current files does not remove them from Git history.
