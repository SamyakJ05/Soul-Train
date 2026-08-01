from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd


SCORE_KEYS = ("sad", "chill", "happy", "hype")
MOOD_PROFILES = {
    # Each profile is a probability distribution matching the dataset's schema:
    # reflective/sad, calm/chill, joyful/happy, energetic/hype.
    "reflective": (0.78, 0.18, 0.03, 0.01),
    "peaceful": (0.02, 0.85, 0.12, 0.01),
    "joyful": (0.02, 0.12, 0.72, 0.14),
    "energized": (0.01, 0.04, 0.20, 0.75),
    "focused": (0.03, 0.48, 0.12, 0.37),
    "romantic": (0.12, 0.28, 0.55, 0.05),
    "dreamy": (0.16, 0.58, 0.22, 0.04),
    "confident": (0.02, 0.10, 0.38, 0.50),
    "cathartic": (0.38, 0.04, 0.08, 0.50),
    "euphoric": (0.01, 0.04, 0.48, 0.47),
    "cozy": (0.05, 0.62, 0.31, 0.02),
    "moody": (0.54, 0.24, 0.05, 0.17),
}
DATA_ARCHIVE = Path(__file__).with_name("fin_nogenre.zip")
ENRICHMENT_FILE = Path(__file__).with_name("data") / "spotify_tracks_enriched.csv.gz"
COLUMNS = [
    "name", "explicit", "release_date", "duration_ms", "id",
    *SCORE_KEYS,
]
GENRE_FAMILIES = {
    "pop": {"pop", "power-pop", "synth-pop", "indie-pop", "cantopop", "j-pop", "k-pop"},
    "rock": {"rock", "alt-rock", "hard-rock", "psych-rock", "punk-rock", "rock-n-roll", "grunge"},
    "indie": {"indie", "indie-pop", "alt-rock", "alternative", "singer-songwriter"},
    "electronic": {"electronic", "edm", "electro", "house", "deep-house", "chicago-house", "techno", "minimal-techno", "trance", "dubstep", "breakbeat", "drum-and-bass"},
    "hip-hop": {"hip-hop", "rap", "trip-hop"},
    "r-n-b": {"r-n-b", "soul", "funk", "neo-soul"},
    "jazz": {"jazz", "blues", "soul"},
    "classical": {"classical", "opera", "piano"},
    "metal": {"metal", "black-metal", "death-metal", "heavy-metal", "metalcore"},
    "folk": {"folk", "bluegrass", "singer-songwriter", "acoustic"},
    "country": {"country", "bluegrass", "honky-tonk"},
    "latin": {"latin", "latino", "salsa", "samba", "reggaeton", "brazil", "spanish"},
    "ambient": {"ambient", "chill", "new-age", "sleep", "study"},
}


@dataclass(frozen=True)
class JourneyOptions:
    start_mood: str
    end_mood: str
    track_count: int = 30
    curve: str = "smooth"
    discovery: int = 35
    era: str = "all"
    allow_explicit: bool = False
    genre: str = "any"
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
        if self.genre != "any" and self.genre not in GENRE_FAMILIES:
            raise ValueError("Choose a valid genre focus.")


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


def _normalize_distributions(values: np.ndarray) -> np.ndarray:
    values = np.clip(np.asarray(values, dtype=float), 0, None)
    totals = values.sum(axis=-1, keepdims=True)
    return np.divide(values, totals, out=np.zeros_like(values), where=totals > 0)


def _hellinger_distance(values: np.ndarray, target: np.ndarray) -> np.ndarray:
    """Probability-aware distance in [0, 1] for mood score distributions."""
    values = _normalize_distributions(values)
    target = _normalize_distributions(target)
    return np.linalg.norm(np.sqrt(values) - np.sqrt(target), axis=-1) / np.sqrt(2)


def _title_key(value) -> str:
    return " ".join(str(value).casefold().split())


def _candidate_pool_size(discovery: int, available_count: int, endpoint: bool) -> int:
    if endpoint:
        return 1
    return min(1 + round((discovery / 100) * 24), available_count)


def _load_catalog() -> pd.DataFrame:
    base = pd.read_csv(DATA_ARCHIVE, header=None, names=COLUMNS)
    if not ENRICHMENT_FILE.exists():
        base["genre"] = ""
        return base

    enriched = pd.read_csv(ENRICHMENT_FILE)
    metadata = enriched[["id", "genre", "artist", "popularity", "energy", "valence"]]
    base = base.merge(metadata, on="id", how="left")
    additions = enriched.loc[~enriched["id"].isin(base["id"])]
    return pd.concat([base, additions], ignore_index=True, sort=False)


def _filter_genre(songs: pd.DataFrame, genre: str) -> pd.DataFrame:
    if genre == "any":
        return songs
    if "genre" not in songs or not ENRICHMENT_FILE.exists():
        raise FileNotFoundError("Genre enrichment data is not installed.")
    accepted = GENRE_FAMILIES[genre]
    genre_sets = songs["genre"].fillna("").str.split("|")
    return songs.loc[genre_sets.map(lambda values: bool(set(values) & accepted))]


def generate_mood_journey(
    options: JourneyOptions,
    allowed_track_ids: set[str] | None = None,
    excluded_track_ids: set[str] | None = None,
) -> list[dict]:
    options.validate()
    if not DATA_ARCHIVE.exists():
        raise FileNotFoundError(f"Dataset archive not found: {DATA_ARCHIVE.name}")

    songs = _load_catalog()
    songs["id"] = songs["id"].astype(str)
    if allowed_track_ids is not None:
        songs = songs.loc[songs["id"].isin(allowed_track_ids)]
    if excluded_track_ids:
        songs = songs.loc[~songs["id"].isin(excluded_track_ids)]
    if not options.allow_explicit:
        songs = songs.loc[~songs["explicit"].astype(bool)]
    songs = _filter_genre(songs, options.genre)
    songs = _filter_era(songs, options.era).dropna(subset=["id", *SCORE_KEYS])
    if len(songs) < options.track_count:
        raise ValueError(
            "Not enough tracks match that combination. Try Any genre, another era, "
            "a shorter playlist, or allow explicit tracks."
        )

    rng = np.random.default_rng(options.seed)
    start_profile = _normalize_distributions(np.array(MOOD_PROFILES[options.start_mood]))
    end_profile = _normalize_distributions(np.array(MOOD_PROFILES[options.end_mood]))
    score_matrix = _normalize_distributions(songs[list(SCORE_KEYS)].to_numpy(dtype=float))
    titles = songs["name"].map(_title_key).to_numpy()
    available = np.ones(len(songs), dtype=bool)
    continuity_weight = {"smooth": 0.42, "cinematic": 0.32, "surprise": 0.16}[options.curve]

    selected = []
    previous_profile = None
    progress_points = _journey_progress(options.track_count, options.curve)
    for position, progress in enumerate(progress_points):
        target = start_profile * (1 - progress) + end_profile * progress
        scores = _hellinger_distance(score_matrix, target)
        if previous_profile is not None:
            scores += continuity_weight * _hellinger_distance(score_matrix, previous_profile)
        eligible = np.flatnonzero(available)
        if not len(eligible):
            break
        eligible_scores = scores[eligible]
        pool_size = _candidate_pool_size(
            options.discovery, len(eligible), position in {0, options.track_count - 1}
        )
        nearest = np.argpartition(eligible_scores, pool_size - 1)[:pool_size]
        nearest = nearest[np.argsort(eligible_scores[nearest])]
        if pool_size == 1:
            chosen_position = nearest[0]
        else:
            # Higher discovery widens the pool; exponential rank weighting still
            # favors strong matches and prevents randomness from overwhelming fit.
            temperature = 1.2 + (options.discovery / 100) * 4.0
            weights = np.exp(-np.arange(pool_size) / temperature)
            chosen_position = rng.choice(nearest, p=weights / weights.sum())
        chosen = eligible[chosen_position]
        selected.append(songs.iloc[chosen])
        previous_profile = score_matrix[chosen]
        available[titles == titles[chosen]] = False

    if len(selected) < options.track_count:
        raise RuntimeError("Could not build a full journey with those options.")
    return [
        {
            "id": str(row["id"]),
            "name": row["name"],
            "release_date": row["release_date"],
            "mood_scores": {key: float(row[key]) for key in SCORE_KEYS},
        }
        for row in selected
    ]


def make_playlist(start_mood: str, end_mood: str, track_count: int = 30) -> list[str]:
    """Backward-compatible helper returning selected Spotify track IDs."""
    options = JourneyOptions(start_mood, end_mood, track_count)
    return [track["id"] for track in generate_mood_journey(options)]
