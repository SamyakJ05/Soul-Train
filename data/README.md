# Data sources

## Soul Train mood catalog

`fin_nogenre.zip` contains 1,204,025 Spotify track IDs scored across sad,
chill, happy, and hype. Its original provenance should be documented before a
public or commercial release.

## Spotify Tracks Dataset (114k)

Source: <https://www.kaggle.com/datasets/maharshipandya/-spotify-tracks-dataset>

The source adds artist, album, 114 genre classes, popularity, valence, energy,
danceability, acousticness, instrumentalness, liveness, speechiness, loudness,
tempo, key, and mode. The downloaded raw CSV is ignored by Git. Run:

```bash
python3 scripts/prepare_spotify_enrichment.py
```

The preparation script aggregates duplicate Spotify IDs, uses exact ID overlap
with the original mood catalog to calibrate acoustic features to four mood
probabilities, validates on a deterministic holdout, and writes the compact
`spotify_tracks_enriched.csv.gz` plus its provenance manifest.

The public mirror labels the dataset BSD. Because its fields were originally
collected through Spotify's API, review Spotify's current platform terms before
commercial deployment or model training.

## Sources evaluated but not bundled

- FMA metadata: useful CC BY 4.0 genre/features benchmark, but no reliable
  Spotify-ID crosswalk and a 342 MiB metadata archive.
- DEAM: 1,802 valence/arousal annotated songs, useful as an evaluation benchmark
  but not directly joinable to this catalog.
- MTG-Jamendo: strong genre and mood/theme labels, but restricted to
  non-commercial research without separate authorization.
