from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd


SCORE_KEYS = ("sad", "chill", "happy", "hype")
MOOD_PROFILES = {
    "reflective": (0.90, 0.35, 0.05, 0.05),
    "peaceful": (0.05, 0.95, 0.25, 0.02),
    "joyful": (0.02, 0.20, 0.95, 0.35),
    "energized": (0.02, 0.05, 0.40, 0.98),
    "focused": (0.05, 0.72, 0.15, 0.45),
    "romantic": (0.20, 0.52, 0.75, 0.08),
    "dreamy": (0.25, 0.82, 0.38, 0.05),
    "confident": (0.02, 0.18, 0.70, 0.78),
    "cathartic": (0.72, 0.08, 0.18, 0.82),
    "euphoric": (0.00, 0.08, 1.00, 0.88),
    "cozy": (0.08, 0.88, 0.58, 0.02),
    "moody": (0.78, 0.42, 0.08, 0.28),
}
DATA_ARCHIVE = Path(__file__).with_name("fin_nogenre.zip")
COLUMNS = [
    "name", "explicit", "release_date", "duration_ms", "id",
    *SCORE_KEYS,
]


@dataclass(frozen=True)
class JourneyOptions:
    start_mood: str
    end_mood: str
    track_count: int = 30
    curve: str = "smooth"
    discovery: int = 35
    era: str = "all"
    allow_explicit: bool = False
    seed: int | None = None

    def validate(self):
        if self.start_mood not in MOOD_PROFILES or self.end_mood not in MOOD_PROFILES:
            raise ValueError("Choose a valid start and end mood.")
        if self.start_mood == self.end_mood:
            raise ValueError("Choose two different moods for a journey.")
        if not 10 <= self.track_count <= 100:
            raise ValueError("Playlist length must be between 10 and 100 tracks.")
        if self.curve not in {"smooth", "cinematic", "surprise"}:
            raise ValueError("Choose a valid journey shape.")
        if not 0 <= self.discovery <= 100:
            raise ValueError("Discovery must be between 0 and 100.")
        if self.era not in {"all", "pre-2000", "2000s", "2010s", "2020s"}:
            raise ValueError("Choose a valid era.")


def _journey_progress(count: int, curve: str) -> np.ndarray:
    progress = np.linspace(0, 1, count)
    if curve == "cinematic":
        return 3 * progress**2 - 2 * progress**3
    if curve == "surprise":
        return np.clip(progress + 0.12 * np.sin(progress * 5 * np.pi), 0, 1)
    return progress


def _filter_era(songs: pd.DataFrame, era: str) -> pd.DataFrame:
    if era == "all":
        return songs
    years = pd.to_datetime(songs["release_date"], errors="coerce").dt.year
    ranges = {
        "pre-2000": (0, 1999), "2000s": (2000, 2009),
        "2010s": (2010, 2019), "2020s": (2020, 2100),
    }
    low, high = ranges[era]
    return songs.loc[years.between(low, high)]


def generate_mood_journey(
    options: JourneyOptions, allowed_track_ids: set[str] | None = None
) -> list[dict]:
    options.validate()
    if not DATA_ARCHIVE.exists():
        raise FileNotFoundError(f"Dataset archive not found: {DATA_ARCHIVE.name}")

    songs = pd.read_csv(DATA_ARCHIVE, header=None, names=COLUMNS)
    songs["id"] = songs["id"].astype(str)
    if allowed_track_ids is not None:
        songs = songs.loc[songs["id"].isin(allowed_track_ids)]
    if not options.allow_explicit:
        songs = songs.loc[~songs["explicit"].astype(bool)]
    songs = _filter_era(songs, options.era).dropna(subset=["id", *SCORE_KEYS])
    if len(songs) < options.track_count:
        raise ValueError(
            "Not enough tracks match that combination. Try Any genre, another era, "
            "a shorter playlist, or allow explicit tracks."
        )

    # Keep strong mood candidates, but widen the pool as discovery increases.
    rng = np.random.default_rng(options.seed)
    songs = songs.assign(_jitter=rng.random(len(songs)) * (options.discovery / 100) * 0.18)

    start_profile = np.array(MOOD_PROFILES[options.start_mood])
    end_profile = np.array(MOOD_PROFILES[options.end_mood])
    score_matrix = songs[list(SCORE_KEYS)].to_numpy(dtype=float)

    selected = []
    used = set()
    for progress in _journey_progress(options.track_count, options.curve):
        target = start_profile * (1 - progress) + end_profile * progress
        distance = pd.Series(
            np.linalg.norm(score_matrix - target, axis=1) - songs["_jitter"].to_numpy(),
            index=songs.index,
        )
        available = distance.loc[~songs.index.isin(used)]
        if available.empty:
            break
        index = available.idxmin()
        used.add(index)
        selected.append(songs.loc[index])

    if len(selected) < options.track_count:
        raise RuntimeError("Could not build a full journey with those options.")
    return [
        {"id": str(row["id"]), "name": row["name"], "release_date": row["release_date"]}
        for row in selected
    ]


def make_playlist(start_mood: str, end_mood: str, track_count: int = 30) -> list[str]:
    """Backward-compatible helper returning selected Spotify track IDs."""
    options = JourneyOptions(start_mood, end_mood, track_count)
    return [track["id"] for track in generate_mood_journey(options)]
