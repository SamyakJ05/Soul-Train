<p align="center">
  <img src="static/images/soul-train-mark-v2.png" alt="Soul Train logo" width="128">
</p>

<h1 align="center">Soul Train</h1>

<p align="center">
  Turn how you feel into what you hear next.
</p>

<p align="center">
  <a href="https://soul-train-rqyr.onrender.com/"><strong>Open Soul Train ↗</strong></a>
</p>

<p align="center">
  <img alt="Python" src="https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white">
  <img alt="Flask" src="https://img.shields.io/badge/Flask-3-000000?logo=flask&logoColor=white">
  <img alt="Spotify" src="https://img.shields.io/badge/Spotify-Web_API-1DB954?logo=spotify&logoColor=white">
  <img alt="PostgreSQL" src="https://img.shields.io/badge/PostgreSQL-Neon-4169E1?logo=postgresql&logoColor=white">
  <img alt="Deployment" src="https://img.shields.io/badge/Deployed_on-Render-46E3B7?logo=render&logoColor=111111">
  <a href="LICENSE"><img alt="License" src="https://img.shields.io/badge/License-GPL_v3-blue.svg"></a>
</p>

Soul Train is a Spotify playlist companion built around intention instead of
endless scrolling. Create a track-by-track emotional journey, bring forgotten
favorites back into rotation, review every selection, and save the finished
playlist directly to your Spotify account.

> The public deployment uses Render's free service and can take a short time to
> wake after a period of inactivity.

## Project history

Soul Train began as a collaborative group project for university. That original
work established the foundation of the application and remains an important part
of its history.

After the university project, **Samyak Jain** continued developing Soul Train as
its current maintainer. He added and expanded its features, improved the playlist
model and user experience, modernized and maintained the codebase, introduced the
hosted database and admin tooling, and deployed the application for public use.

Copyright in the project remains with its respective contributors.

## What you can do

| Experience | What it offers |
| --- | --- |
| **Mood Journey** | Move between two of 12 moods with controls for journey shape, discovery, era, genre, explicit content, length, name, and visibility. |
| **Library Mix** | Rediscover older tracks from up to 500 songs in your saved Spotify library. |
| **Playlist Studio** | Preview the result, pin favorites, replace or remove tracks, reorder the mix, and publish only when it feels right. |
| **Your Stats** | Explore top tracks, artists, genres, unique artists, and recent listening minutes across Spotify time ranges. |
| **Private Admin** | Review privacy-conscious usage totals and recent activity without collecting IP addresses, email addresses, tokens, or listening history. |

## How Mood Journey works

Soul Train represents every track as four normalized mood signals: reflective,
calm, joyful, and energetic. Each of the 12 user-facing moods is a target blend
of those signals.

1. The selected start and end moods define an emotional path.
2. Smooth, cinematic, or surprise curves determine how that path develops.
3. Hellinger distance scores tracks against each point on the path.
4. Adjacent-track continuity keeps the transition coherent.
5. Controlled candidate sampling uses the discovery setting to balance fit and
   variety.
6. Duplicate titles and previously selected tracks are excluded.

The default compact catalog contains 89,740 enriched tracks and occupies about
23 MiB in memory. A generated 30-track journey peaks at roughly 142 MiB total
process memory, allowing the model to run on a 512 MB Render instance. The full
1.2-million-track catalog remains available with `CATALOG_MODE=full` for hosts
with substantially more memory.

## Application flow

```text
Browser
  └─ Flask application
      ├─ Mood model ───────────── local enriched catalog
      ├─ Spotify OAuth/API ───── account, library, stats, playlists
      └─ Data store
          ├─ SQLite ───────────── local development
          └─ Neon PostgreSQL ─── hosted drafts and analytics
```

Spotify authorization happens on Spotify. Soul Train never receives the user's
Spotify password. Published playlists are created directly in the connected
account.

## Tech stack

- Flask and Gunicorn
- Spotify Web API through Spotipy
- pandas and NumPy for catalog processing and mood scoring
- SQLite for local development
- PostgreSQL through psycopg for hosted persistence
- Server-rendered Jinja templates with custom CSS and JavaScript
- Render for the web service and Neon for hosted PostgreSQL

## Run locally

### Requirements

- Python 3.12+
- A Spotify developer application
- Git

### Installation

```bash
git clone https://github.com/SamyakJ05/Soul-Train.git
cd Soul-Train
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements.txt
cp .env.example .env
```

Add your Spotify application credentials to `.env`:

```env
SPOTIPY_CLIENT_ID=your-client-id
SPOTIPY_CLIENT_SECRET=your-client-secret
SPOTIPY_REDIRECT_URI=http://127.0.0.1:5001/callback
FLASK_SECRET_KEY=replace-with-a-long-random-value
SESSION_COOKIE_SECURE=0
ADMIN_PASSWORD_HASH=
DATABASE_URL=
SOUL_TRAIN_DATABASE_PATH=instance/playlist_drafts.sqlite3
CATALOG_MODE=compact
```

Register this exact local redirect URI in the Spotify Developer Dashboard:

```text
http://127.0.0.1:5001/callback
```

Start the application:

```bash
python -m app
```

Then open <http://127.0.0.1:5001>.

## Configuration

| Variable | Required | Purpose |
| --- | --- | --- |
| `SPOTIPY_CLIENT_ID` | Yes | Spotify application client ID. |
| `SPOTIPY_CLIENT_SECRET` | Yes | Spotify application client secret. |
| `SPOTIPY_REDIRECT_URI` | Yes | Exact Spotify OAuth callback registered in the developer dashboard. |
| `FLASK_SECRET_KEY` | Yes in production | Signs browser sessions and OAuth state. |
| `SESSION_COOKIE_SECURE` | Production | Set to `1` when the site uses HTTPS. |
| `ADMIN_PASSWORD_HASH` | Recommended | Werkzeug hash used to protect `/admin`. |
| `ADMIN_PASSWORD` | Local fallback | Plain-text development fallback; avoid in production. |
| `DATABASE_URL` | Hosted deployments | PostgreSQL URL; takes precedence over local SQLite. |
| `SOUL_TRAIN_DATABASE_PATH` | Local or persistent disk | SQLite database path when `DATABASE_URL` is absent. |
| `CATALOG_MODE` | Optional | `compact` by default; `full` requires significantly more RAM. |

Generate production secrets without placing the values directly in shell
history:

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(48))"
python3 -c "import getpass; from werkzeug.security import generate_password_hash; print(generate_password_hash(getpass.getpass('Admin password: ')))"
```

## Spotify permissions

Soul Train requests only the scopes used by its features:

- Modify public and private playlists
- Read saved-library tracks
- Read the connected user's basic private profile
- Read top tracks and artists
- Read recently played tracks

Spotify does not provide a lifetime listening-minutes total. The minutes shown
in Your Stats are clearly labeled estimates derived from the latest available
playback records.

## Data

The mood model combines two local sources:

- `fin_nogenre.zip`: 1,204,025 Spotify track IDs with sad, chill, happy, and hype
  probabilities.
- `data/spotify_tracks_enriched.csv.gz`: a compact enriched catalog derived from
  the [Spotify Tracks Dataset on Kaggle](https://www.kaggle.com/datasets/maharshipandya/-spotify-tracks-dataset),
  adding genre and acoustic metadata.

The enrichment pipeline is documented in [data/README.md](data/README.md) and can
be rebuilt with:

```bash
python3 scripts/prepare_spotify_enrichment.py
```

Review the source datasets and Spotify's current platform terms before commercial
distribution or model training.

## Tests

Run the complete test suite:

```bash
python3 -m unittest discover -q
```

The tests cover routes, Spotify OAuth state, playlist creation, mood scoring,
playlist drafts, listening statistics, admin authentication, analytics, and
SQLite/PostgreSQL compatibility.

## Deploy with Render and Neon

The live deployment is available at
[soul-train-rqyr.onrender.com](https://soul-train-rqyr.onrender.com/).

### Neon

1. Create a Neon project.
2. Open **Connect**, enable connection pooling, and copy the connection string.
3. Store it only in Render as `DATABASE_URL`. Never commit it.

### Render

Create a Python web service from this repository with:

```text
Build command:
pip install -r requirements.txt

Start command:
gunicorn app:app --workers 1 --threads 4 --timeout 120 --bind 0.0.0.0:$PORT

Health check:
/healthz
```

Required production values include:

```env
SPOTIPY_REDIRECT_URI=https://soul-train-rqyr.onrender.com/callback
SESSION_COOKIE_SECURE=1
CATALOG_MODE=compact
DATABASE_URL=your-pooled-neon-connection-string
```

Register the same HTTPS callback in the Spotify Developer Dashboard. Database
tables are created automatically on first use; no pre-deploy migration command is
required.

## Project structure

```text
app/                         Flask application package
  __init__.py                Routes, configuration, and Gunicorn application
  __main__.py                Local `python -m app` entry point
  parse.py                   Mood profiles, catalog loading, and journey scoring
  playlist_service.py        Playlist preparation, editing, and publishing flow
  spotify_auth.py            Spotify OAuth and session token handling
  spotify_client.py          Spotify API helpers
  stats_service.py           Listening-statistics aggregation
  analytics_service.py       Privacy-conscious product analytics
  draft_store.py             Expiring Playlist Studio drafts
  database.py                SQLite/PostgreSQL connection compatibility
  admin_auth.py              Admin password verification
templates/                   Server-rendered interface
static/                      Styles, JavaScript, fonts, and brand assets
data/                        Enriched catalog and provenance documentation
scripts/                     Dataset preparation utilities
tests/                       Automated test suite
```

## License

Soul Train is free software licensed under the
[GNU General Public License v3.0 only](LICENSE) (`GPL-3.0-only`). You may use,
study, modify, and redistribute the software under the terms of that license.
Distributed derivative works must make their corresponding source available and
remain under GPL v3-compatible terms.

The license applies to the project code. Bundled datasets, Spotify content,
third-party APIs, fonts, and other third-party materials remain subject to their
own licenses and terms.

## Privacy and security

- Credentials and database URLs belong in `.env` or hosting-provider secrets,
  never in Git.
- Spotify tokens remain in signed, HTTP-only browser sessions.
- OAuth requests use state validation.
- Production cookies are secure and use `SameSite=Lax`.
- Admin responses disable caching and search indexing.
- First-party analytics avoid IP addresses, emails, Spotify tokens, and listening
  history.

If a credential is ever committed or shared, rotate it immediately. Removing a
secret from the latest file does not remove it from Git history.
