from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd


MOODS = ("sad", "chill", "happy", "hype")
DATA_ARCHIVE = Path(__file__).with_name("fin_nogenre.zip")
COLUMNS = [
    "name", "explicit", "release_date", "duration_ms", "id",
    "sad", "chill", "happy", "hype",
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
        if self.start_mood not in MOODS or self.end_mood not in MOODS:
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


def generate_mood_journey(options: JourneyOptions) -> list[dict]:
    options.validate()
    if not DATA_ARCHIVE.exists():
        raise FileNotFoundError(f"Dataset archive not found: {DATA_ARCHIVE.name}")

    songs = pd.read_csv(DATA_ARCHIVE, header=None, names=COLUMNS)
    if not options.allow_explicit:
        songs = songs.loc[~songs["explicit"].astype(bool)]
    songs = _filter_era(songs, options.era).dropna(subset=["id", *MOODS])
    if len(songs) < options.track_count:
        raise ValueError("Not enough tracks match those filters. Try another era or allow explicit tracks.")

    # Keep strong mood candidates, but widen the pool as discovery increases.
    relevance_floor = 0.62 - (options.discovery / 100) * 0.27
    songs = songs.loc[songs[[options.start_mood, options.end_mood]].max(axis=1) >= relevance_floor]
    rng = np.random.default_rng(options.seed)
    songs = songs.assign(_jitter=rng.random(len(songs)) * (options.discovery / 100) * 0.18)

    selected = []
    used = set()
    for progress in _journey_progress(options.track_count, options.curve):
        target_start, target_end = 1 - progress, progress
        distance = (
            (songs[options.start_mood] - target_start).abs()
            + (songs[options.end_mood] - target_end).abs()
            - songs["_jitter"]
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
