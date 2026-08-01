"""Build a compact mood/genre enrichment catalog from the 114k-track dataset.

The source CSV is the dataset selected in the project brief:
https://www.kaggle.com/datasets/maharshipandya/-spotify-tracks-dataset

A deterministic ridge calibration is fitted only on track IDs shared with Soul
Train's existing labeled catalog. The generated file contains predictions for
previously unseen IDs plus genre and acoustic metadata for all unique source IDs.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data" / "spotify_tracks_114k.csv"
BASE = ROOT / "fin_nogenre.zip"
OUTPUT = ROOT / "data" / "spotify_tracks_enriched.csv.gz"
MANIFEST = ROOT / "data" / "spotify_tracks_enriched.manifest.json"
BASE_COLUMNS = [
    "name", "explicit", "release_date", "duration_ms", "id",
    "sad", "chill", "happy", "hype",
]
MOODS = ["sad", "chill", "happy", "hype"]
FEATURES = [
    "valence", "energy", "danceability", "acousticness", "instrumentalness",
    "liveness", "speechiness", "loudness", "tempo", "mode",
]


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _design_matrix(frame: pd.DataFrame) -> np.ndarray:
    values = frame[FEATURES].astype(float).to_numpy()
    values[:, 7] = np.clip((values[:, 7] + 60) / 65, 0, 1)  # loudness dB
    values[:, 8] = np.clip(values[:, 8] / 250, 0, 1)  # tempo BPM
    valence, energy = values[:, 0], values[:, 1]
    interactions = np.column_stack(
        [valence * energy, valence * (1 - energy), energy * values[:, 2], energy * (1 - values[:, 3])]
    )
    return np.column_stack([np.ones(len(values)), values, interactions])


def _fit_ridge(x: np.ndarray, y: np.ndarray, penalty: float = 2.0) -> np.ndarray:
    regularizer = np.eye(x.shape[1]) * penalty
    regularizer[0, 0] = 0
    return np.linalg.solve(x.T @ x + regularizer, x.T @ y)


def _probabilities(values: np.ndarray) -> np.ndarray:
    values = np.clip(values, 0.001, None)
    return values / values.sum(axis=1, keepdims=True)


def _quadrant_baseline(frame: pd.DataFrame) -> np.ndarray:
    valence = frame["valence"].to_numpy(dtype=float)
    arousal = (
        0.65 * frame["energy"].to_numpy(dtype=float)
        + 0.20 * frame["danceability"].to_numpy(dtype=float)
        + 0.15 * np.clip(frame["tempo"].to_numpy(dtype=float) / 250, 0, 1)
    )
    return _probabilities(
        np.column_stack(
            [(1 - valence) * (1 - arousal), valence * (1 - arousal), valence * arousal, (1 - valence) * arousal]
        )
    )


def _aggregate_source(source: pd.DataFrame) -> pd.DataFrame:
    source = source.drop(columns=["Unnamed: 0"], errors="ignore")
    source = source.dropna(subset=["track_id", "track_name"])
    numeric = ["popularity", "duration_ms", *FEATURES]
    aggregations = {column: "mean" for column in numeric}
    aggregations.update(
        {
            "track_name": "first", "artists": "first", "album_name": "first",
            "explicit": "max",
            "track_genre": lambda values: "|".join(sorted(set(values.dropna().astype(str)))),
        }
    )
    return source.groupby("track_id", as_index=False).agg(aggregations)


def main() -> None:
    if not SOURCE.exists():
        raise SystemExit(f"Missing source dataset: {SOURCE}")
    source = _aggregate_source(pd.read_csv(SOURCE))
    base = pd.read_csv(BASE, header=None, names=BASE_COLUMNS)
    overlap = source.merge(base[["id", *MOODS]], left_on="track_id", right_on="id", how="inner")
    overlap = overlap.dropna(subset=[*FEATURES, *MOODS])
    if len(overlap) < 1000:
        raise SystemExit(f"Only {len(overlap)} labeled overlaps; refusing to fit an unstable calibration")

    rng = np.random.default_rng(42)
    test_mask = rng.random(len(overlap)) < 0.2
    train, test = overlap.loc[~test_mask], overlap.loc[test_mask]
    weights = _fit_ridge(_design_matrix(train), train[MOODS].to_numpy(dtype=float))
    validation = _probabilities(_design_matrix(test) @ weights)
    truth = _probabilities(test[MOODS].to_numpy(dtype=float))
    validation_mae = float(np.abs(validation - truth).mean())
    baseline_mae = float(np.abs(_quadrant_baseline(test) - truth).mean())

    predicted = _probabilities(_design_matrix(source) @ weights)
    for index, mood in enumerate(MOODS):
        source[mood] = predicted[:, index]

    # Preserve the project's human/model labels wherever an exact Spotify ID is shared.
    known = base[["id", *MOODS]].rename(columns={"id": "track_id"})
    source = source.merge(known, on="track_id", how="left", suffixes=("", "_known"))
    for mood in MOODS:
        source[mood] = source[f"{mood}_known"].fillna(source[mood])
        source = source.drop(columns=f"{mood}_known")

    output = source.rename(
        columns={"track_id": "id", "track_name": "name", "track_genre": "genre", "artists": "artist"}
    )
    output["release_date"] = ""
    columns = [
        "name", "artist", "album_name", "explicit", "release_date", "duration_ms", "id",
        *MOODS, "genre", "popularity", *FEATURES,
    ]
    output[columns].to_csv(OUTPUT, index=False, compression="gzip")
    manifest = {
        "source": "https://www.kaggle.com/datasets/maharshipandya/-spotify-tracks-dataset",
        "download_mirror": "https://huggingface.co/datasets/maharshipandya/spotify-tracks-dataset",
        "source_sha256": _sha256(SOURCE),
        "source_rows": 114000,
        "unique_tracks": int(len(source)),
        "labeled_overlap": int(len(overlap)),
        "held_out_rows": int(test_mask.sum()),
        "held_out_mean_absolute_error": round(validation_mae, 6),
        "quadrant_baseline_mae": round(baseline_mae, 6),
        "error_reduction_vs_baseline_percent": round((1 - validation_mae / baseline_mae) * 100, 2),
        "method": "ridge calibration on exact Spotify track ID overlap; probability-normalized output",
        "license_note": "Mirror declares BSD; source data originated from Spotify Web API. Review platform terms before commercial use.",
    }
    MANIFEST.write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
