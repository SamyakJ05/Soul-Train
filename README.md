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
- **Playlist Studio:** previews a generated playlist before it reaches Spotify.
  Users can pin tracks, replace or remove individual selections, adjust the order,
  rename the playlist, and confirm its visibility before publishing. Drafts are
  scoped to the current signed browser session, stored in SQLite under `instance/`,
  and expire after 24 hours.
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

## Admin analytics

The private `/admin` dashboard shows unique anonymous browsers, connected Spotify
users, page views, playlist drafts, published playlists, and recent activity. It
does not collect IP addresses, emails, Spotify tokens, or listening history.

Prefer a hashed password in `ADMIN_PASSWORD_HASH`. Generate one without placing
the password in shell history:

```sh
python3 -c "import getpass; from werkzeug.security import generate_password_hash; print(generate_password_hash(getpass.getpass('Admin password: ')))"
```

Copy the output into `.env` locally or the hosting provider's secret environment
variables. `ADMIN_PASSWORD` is supported as a simpler local fallback. Set
`SOUL_TRAIN_DATABASE_PATH` to a persistent disk location and
`SESSION_COOKIE_SECURE=1` in production.

## Deployment note

This repository is a stateful Flask/WSGI application. A normal Netlify static
deploy cannot run the Flask process, and local SQLite storage is not durable in a
serverless runtime. Deploy the complete app on a Python host with a persistent
disk, or keep a Netlify frontend and host the Flask API plus database separately.
Converting the backend to Netlify Functions would require a separate migration
and persistent storage such as Netlify Blobs or an external SQL database.
The included `Procfile` starts the backend with Gunicorn on compatible Python
hosting platforms.

## Security

Credentials must never be committed. Any credentials previously stored in this
repository should be rotated in the Spotify developer dashboard because removing
them from the current files does not remove them from Git history.
