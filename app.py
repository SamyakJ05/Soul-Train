import os
from pathlib import Path

from flask import Flask, flash, redirect, render_template, request, session, url_for
from dotenv import load_dotenv

load_dotenv(Path(__file__).with_name(".env"))

from playlist_service import build_library_mix, build_mood_playlist
from spotify_auth import (
    missing_spotify_configuration,
    new_oauth_state,
    spotify_is_configured,
    spotify_oauth,
)
from spotify_client import connected_spotify
from stats_service import listening_stats


app = Flask(__name__)
app.config.from_mapping(
    SECRET_KEY=os.getenv("FLASK_SECRET_KEY", "dev-change-me"),
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=os.getenv("FLASK_ENV") == "production",
)


def spotify_user():
    if not spotify_is_configured() or "spotify_token" not in session:
        return None
    try:
        spotify = connected_spotify()
        if session.get("spotify_profile"):
            return session["spotify_profile"]
        profile = spotify.current_user()
        session["spotify_profile"] = {
            "name": profile.get("display_name") or "Spotify listener",
            "image": _profile_image(profile),
        }
        return session["spotify_profile"]
    except Exception:
        return None


@app.context_processor
def inject_navigation_state():
    return {"spotify_user": spotify_user(), "spotify_configured": spotify_is_configured()}


@app.get("/")
def page():
    return render_template("page.html")


@app.get("/about")
@app.get("/aboutus")
def aboutus():
    return render_template("aboutus.html")


@app.get("/discover")
@app.get("/builder")
def discover():
    mode = request.args.get("mode", "mood")
    return redirect(url_for("library_builder" if mode == "library" else "mood_builder"))


@app.get("/create/mood")
def mood_builder():
    return render_template("builder.html", active_mode="mood")


@app.get("/create/library")
def library_builder():
    return render_template("builder.html", active_mode="library")


@app.get("/connect")
def connect():
    if not spotify_is_configured():
        missing = ", ".join(missing_spotify_configuration())
        flash(f"Spotify configuration is missing: {missing}.", "error")
        return redirect(url_for("mood_builder"))
    next_path = request.args.get("next")
    if next_path and next_path.startswith("/") and not next_path.startswith("//"):
        session["connect_next"] = next_path
    auth = spotify_oauth()
    return redirect(auth.get_authorize_url(state=new_oauth_state()))


@app.get("/callback")
def spotify_callback():
    if request.args.get("error"):
        flash("Spotify connection was cancelled. Nothing was changed.", "error")
        return redirect(url_for("discover"))
    if request.args.get("state") != session.pop("spotify_oauth_state", None):
        flash("That Spotify connection expired. Please try again.", "error")
        return redirect(url_for("discover"))
    code = request.args.get("code")
    if not code:
        flash("Spotify did not return an authorization code.", "error")
        return redirect(url_for("discover"))
    spotify_oauth().get_access_token(code, check_cache=False)
    flash("Spotify connected. Your next playlist will save directly to your account.", "success")
    return redirect(session.pop("connect_next", url_for("mood_builder")))


@app.post("/disconnect")
def disconnect():
    session.pop("spotify_token", None)
    session.pop("spotify_profile", None)
    flash("Spotify disconnected from this browser.", "success")
    return redirect(url_for("page"))


@app.get("/reconnect")
def reconnect():
    session.pop("spotify_token", None)
    session.pop("spotify_profile", None)
    return redirect(url_for("connect", next=request.args.get("next", "/create/mood")))


@app.post("/create")
def create():
    if not spotify_user():
        session["connect_next"] = _builder_url(request.form.get("mode"))
        flash("Connect Spotify first, then your playlist will be saved automatically.", "error")
        return redirect(url_for("connect"))
    try:
        spotify = connected_spotify()
        if request.form.get("mode") == "library":
            playlist, tracks = build_library_mix(spotify, request.form)
        else:
            playlist, tracks = build_mood_playlist(spotify, request.form)
    except (FileNotFoundError, RuntimeError, ValueError) as exc:
        flash(str(exc), "error")
        return redirect(_builder_url(request.form.get("mode")))
    except Exception:
        app.logger.exception("Spotify playlist creation failed")
        flash("Spotify could not create that playlist right now. Please reconnect and try again.", "error")
        return redirect(_builder_url(request.form.get("mode")))

    session["last_playlist"] = {
        "id": playlist["id"], "name": playlist["name"],
        "url": playlist.get("external_urls", {}).get("spotify", f"https://open.spotify.com/playlist/{playlist['id']}"),
        "track_count": len(tracks),
    }
    return redirect(url_for("success"))


@app.get("/success")
def success():
    playlist = session.get("last_playlist")
    if not playlist:
        return redirect(url_for("discover"))
    return render_template("success.html", playlist=playlist)


@app.get("/stats")
def stats():
    if not spotify_user():
        return render_template("stats.html", stats=None)
    try:
        data = listening_stats(connected_spotify(), request.args.get("range", "medium_term"))
    except Exception:
        app.logger.exception("Spotify statistics request failed")
        flash("Your Spotify stats could not be loaded. Reconnect if you recently approved new permissions.", "error")
        data = None
    return render_template("stats.html", stats=data)


@app.get("/mood-gradient")
@app.get("/mood gradient")
def legacy_mood_gradient():
    return redirect(url_for("mood_builder"), code=308)


@app.get("/playlistinspire")
def legacy_playlist_inspire():
    return redirect(url_for("library_builder"), code=308)


def _profile_image(profile):
    images = profile.get("images") or []
    return images[0].get("url") if images else None


def _builder_url(mode):
    return url_for("library_builder" if mode == "library" else "mood_builder")


if __name__ == "__main__":
    app.run(port=5001, debug=os.getenv("FLASK_DEBUG") == "1")
