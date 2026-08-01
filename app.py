import os

from flask import Flask, flash, redirect, render_template, request


app = Flask(__name__)
app.config.from_mapping(SECRET_KEY=os.getenv("FLASK_SECRET_KEY", "dev"))


@app.get("/")
def page():
    return render_template("page.html")


@app.get("/aboutus")
def aboutus():
    return render_template("aboutus.html")


@app.get("/discover")
def discover():
    return render_template("discover.html")


@app.get("/genre")
def genre():
    return render_template("genre.html")


@app.route("/mood-gradient", methods=["GET", "POST"])
def my_form():
    if request.method == "POST":
        from parse import make_playlist

        try:
            try:
                track_count = int(request.form.get("track_count", "50"))
            except ValueError as exc:
                raise ValueError("Track count must be a whole number.") from exc
            playlist_id = make_playlist(
                request.form.get("mood1", ""),
                request.form.get("mood2", ""),
                track_count,
            )
        except (FileNotFoundError, RuntimeError, ValueError) as exc:
            flash(str(exc), "error")
        else:
            return redirect(f"https://open.spotify.com/playlist/{playlist_id}")
    return render_template("mood gradient.html")


@app.get("/mood gradient")
def legacy_mood_gradient():
    return redirect("/mood-gradient", code=308)


@app.route("/playlistinspire", methods=["GET", "POST"])
def my_form2():
    if request.method == "POST":
        from unsupervised import playtwist

        try:
            playlist_id = playtwist()
        except (FileNotFoundError, RuntimeError, ValueError) as exc:
            flash(str(exc), "error")
        else:
            return redirect(f"https://open.spotify.com/playlist/{playlist_id}")
    return render_template("playlistinspire.html")


if __name__ == "__main__":
    app.run(port=5001)
