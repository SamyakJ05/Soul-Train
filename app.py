import os
import secrets
from pathlib import Path

from flask import Flask, flash, redirect, render_template, request, session, url_for
from dotenv import load_dotenv

load_dotenv(Path(__file__).with_name(".env"))

from draft_store import create_draft, delete_draft, get_draft, save_draft
from playlist_service import (
    prepare_library_draft,
    prepare_mood_draft,
    publish_draft,
    replace_draft_track,
)
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
    DRAFT_DATABASE=Path(app.instance_path) / "playlist_drafts.sqlite3",
)

PLAYLIST_FORM_FIELDS = {
    "mode", "start_mood", "end_mood", "track_count", "curve", "discovery",
    "era", "genre", "playlist_name", "private", "allow_explicit",
}


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
        session["pending_playlist_form"] = _serializable_playlist_form(request.form)
        session["connect_next"] = url_for("resume_create")
        flash("Connect Spotify first, then you’ll return to your playlist preview.", "error")
        return redirect(url_for("connect"))
    try:
        draft = _prepare_playlist_draft(request.form)
    except (FileNotFoundError, RuntimeError, ValueError) as exc:
        flash(str(exc), "error")
        return redirect(_builder_url(request.form.get("mode")))
    except Exception:
        app.logger.exception("Playlist preview generation failed")
        flash("Soul Train could not prepare that playlist right now. Please reconnect and try again.", "error")
        return redirect(_builder_url(request.form.get("mode")))

    _store_current_draft(draft)
    return redirect(url_for("studio"))


@app.get("/create/resume")
def resume_create():
    form = session.pop("pending_playlist_form", None)
    if not form:
        return redirect(url_for("discover"))
    if not spotify_user():
        flash("Spotify did not connect, so your playlist was not created.", "error")
        return redirect(_builder_url(form.get("mode")))
    try:
        draft = _prepare_playlist_draft(form)
    except (FileNotFoundError, RuntimeError, ValueError) as exc:
        flash(str(exc), "error")
        return redirect(_builder_url(form.get("mode")))
    except Exception:
        app.logger.exception("Playlist preview generation failed after Spotify connection")
        flash("Soul Train could not prepare that playlist right now. Please try again.", "error")
        return redirect(_builder_url(form.get("mode")))
    _store_current_draft(draft)
    return redirect(url_for("studio"))


@app.get("/studio")
def studio():
    draft = _current_draft()
    if not draft:
        flash("That playlist preview expired. Create a fresh one to continue.", "error")
        return redirect(url_for("discover"))
    total_minutes = round(
        sum(track.get("duration_ms", 0) for track in draft["tracks"]) / 60000
    )
    return render_template("studio.html", draft=draft, total_minutes=total_minutes)


@app.post("/studio/update")
def update_studio():
    draft = _current_draft()
    if not draft:
        flash("That playlist preview expired. Create a fresh one to continue.", "error")
        return redirect(url_for("discover"))
    index = 0
    try:
        index = int(request.form.get("index", "-1"))
        if not 0 <= index < len(draft["tracks"]):
            raise ValueError("Choose a valid track.")
        action = request.form.get("action")
        track = draft["tracks"][index]
        pinned = set(draft.get("pinned", []))
        if action == "pin":
            if track["id"] in pinned:
                pinned.remove(track["id"])
            else:
                pinned.add(track["id"])
            draft["pinned"] = list(pinned)
        elif action == "remove":
            if track["id"] in pinned:
                raise ValueError("Unpin that track before removing it.")
            if len(draft["tracks"]) <= 2:
                raise ValueError("Keep at least two tracks in the playlist.")
            draft["tracks"].pop(index)
        elif action == "replace":
            if track["id"] in pinned:
                raise ValueError("Unpin that track before replacing it.")
            if not spotify_user():
                raise RuntimeError("Reconnect Spotify before replacing a track.")
            draft["tracks"][index] = replace_draft_track(
                connected_spotify(), draft, index
            )
        elif action in {"up", "down"}:
            destination = index - 1 if action == "up" else index + 1
            if 0 <= destination < len(draft["tracks"]):
                draft["tracks"][index], draft["tracks"][destination] = (
                    draft["tracks"][destination], draft["tracks"][index]
                )
                index = destination
        else:
            raise ValueError("Choose a valid playlist action.")
        _save_current_draft(draft)
    except (RuntimeError, ValueError) as exc:
        flash(str(exc), "error")
    except Exception:
        app.logger.exception("Playlist draft update failed")
        flash("That track could not be updated right now. Please try again.", "error")
    return redirect(f"{url_for('studio')}#track-{max(index, 0) + 1}")


@app.post("/studio/details")
def update_studio_details():
    draft = _current_draft()
    if not draft:
        return redirect(url_for("discover"))
    name = request.form.get("playlist_name", "").strip()
    if not name:
        flash("Give your playlist a name before continuing.", "error")
    else:
        draft["name"] = name[:100]
        draft["public"] = request.form.get("private") != "on"
        _save_current_draft(draft)
        flash("Playlist details updated.", "success")
    return redirect(url_for("studio"))


@app.post("/studio/publish")
def publish_studio():
    draft = _current_draft()
    if not draft:
        flash("That playlist preview expired. Create a fresh one to continue.", "error")
        return redirect(url_for("discover"))
    if not spotify_user():
        session["connect_next"] = url_for("studio")
        flash("Reconnect Spotify to finish creating this playlist.", "error")
        return redirect(url_for("connect"))
    try:
        playlist = publish_draft(connected_spotify(), draft)
    except Exception:
        app.logger.exception("Spotify playlist publishing failed")
        flash("Spotify could not create that playlist right now. Please reconnect and try again.", "error")
        return redirect(url_for("studio"))
    session["last_playlist"] = {
        "id": playlist["id"],
        "name": playlist["name"],
        "url": playlist.get("external_urls", {}).get(
            "spotify", f"https://open.spotify.com/playlist/{playlist['id']}"
        ),
        "track_count": len(draft["tracks"]),
    }
    delete_draft(
        app.config["DRAFT_DATABASE"], session.pop("playlist_draft_id"), _draft_owner_id()
    )
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


def _serializable_playlist_form(form):
    return {
        key: form.get(key, "")
        for key in PLAYLIST_FORM_FIELDS
        if key in form
    }


def _prepare_playlist_draft(form):
    spotify = connected_spotify()
    if form.get("mode") == "library":
        return prepare_library_draft(spotify, form)
    return prepare_mood_draft(spotify, form)


def _store_current_draft(draft):
    previous_id = session.get("playlist_draft_id")
    owner_id = _draft_owner_id()
    if previous_id:
        delete_draft(app.config["DRAFT_DATABASE"], previous_id, owner_id)
    session["playlist_draft_id"] = create_draft(
        app.config["DRAFT_DATABASE"], owner_id, draft
    )


def _draft_owner_id():
    if "draft_owner_id" not in session:
        session["draft_owner_id"] = secrets.token_urlsafe(24)
    return session["draft_owner_id"]


def _current_draft():
    draft_id = session.get("playlist_draft_id")
    if not draft_id:
        return None
    return get_draft(app.config["DRAFT_DATABASE"], draft_id, _draft_owner_id())


def _save_current_draft(draft):
    return save_draft(
        app.config["DRAFT_DATABASE"],
        session["playlist_draft_id"],
        _draft_owner_id(),
        draft,
    )


if __name__ == "__main__":
    app.run(port=5001, debug=os.getenv("FLASK_DEBUG") == "1")
