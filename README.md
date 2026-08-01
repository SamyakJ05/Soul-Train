# Soul Train

Soul Train is a Flask app that creates Spotify playlists from a guided mood journey or rediscovery of a user's saved tracks.

## Setup

1. Create a virtual environment and install `requirements.txt`.
2. Copy `.env.example` to `.env` and provide credentials from a Spotify developer app.
3. In the Spotify developer dashboard, register the exact redirect URI from `.env`.
4. Run `python app.py`; the app loads the `.env` file automatically.
5. Open <http://127.0.0.1:5001>.

The Spotify redirect URI configured in the developer dashboard must match
`SPOTIPY_REDIRECT_URI`. The mood dataset stays compressed as `fin_nogenre.zip` and
is read directly by pandas.

## Playlist modes

- **Mood journey:** track-by-track scoring between two mood targets, with smooth,
  cinematic, or surprise transitions and controls for discovery, era, explicit
  content, genre, length, visibility, and name. Twelve mood profiles are derived
  from the dataset's reflective, calm, joyful, and energetic scores. Profiles and
  tracks are normalized as probability distributions and compared with Hellinger
  distance; adjacent-track continuity and controlled top-candidate sampling keep
  the arc smooth without making every generated playlist identical.
- **Library rediscovery:** reads up to 500 saved Spotify tracks and gives older
  saves a better chance to return to the rotation.
- **Your Stats:** displays top tracks, artists, and genres over four weeks, six
  months, or long-term listening history. Existing users must reconnect once to
  approve the added `user-top-read` and `user-read-recently-played` permissions.
  Spotify does not expose a lifetime minutes total, so the dashboard clearly
  labels its minutes figure as an estimate across the latest 50 playback records.

Spotify tokens are kept in the signed browser session. For a public deployment,
set a strong `FLASK_SECRET_KEY`, use HTTPS, and replace the cookie session with a
server-side session store.

## Security

Credentials must never be committed. Any credentials previously stored in this
repository should be rotated in the Spotify developer dashboard because removing
them from the current files does not remove them from Git history.
