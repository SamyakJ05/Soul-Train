import unittest
from unittest.mock import Mock, patch

import numpy as np
import pandas as pd

from app.parse import (
    COLUMNS,
    MOOD_PROFILES,
    JourneyOptions,
    _candidate_pool_size,
    _hellinger_distance,
    _hellinger_distance_from_roots,
    _journey_progress,
    _load_catalog,
    _read_catalog,
    generate_mood_journey,
)
from app.playlist_service import _integer
from app.spotify_client import create_playlist


class JourneyTests(unittest.TestCase):
    def test_validates_mood_and_length(self):
        with self.assertRaisesRegex(ValueError, "different"):
            JourneyOptions("joyful", "joyful").validate()
        with self.assertRaisesRegex(ValueError, "between"):
            JourneyOptions("reflective", "joyful", track_count=9).validate()

    def test_smooth_curve_moves_forward(self):
        progress = _journey_progress(10, "smooth")
        self.assertTrue(np.all(np.diff(progress) > 0))
        self.assertEqual((progress[0], progress[-1]), (0, 1))

    def test_cinematic_curve_eases_at_the_ends(self):
        progress = _journey_progress(10, "cinematic")
        self.assertLess(progress[1] - progress[0], progress[5] - progress[4])

    def test_profiles_share_the_dataset_probability_scale(self):
        for name, profile in MOOD_PROFILES.items():
            with self.subTest(name=name):
                self.assertAlmostEqual(sum(profile), 1.0)

    def test_probability_distance_is_bounded_and_symmetric(self):
        calm = np.array([0.05, 0.85, 0.09, 0.01])
        hype = np.array([0.01, 0.02, 0.17, 0.80])
        self.assertAlmostEqual(float(_hellinger_distance(calm, calm)), 0.0)
        self.assertAlmostEqual(
            float(_hellinger_distance(calm, hype)),
            float(_hellinger_distance(hype, calm)),
        )
        self.assertLessEqual(float(_hellinger_distance(calm, hype)), 1.0)

    def test_fast_distance_matches_general_distance(self):
        values = np.array([
            [0.05, 0.85, 0.09, 0.01],
            [0.01, 0.02, 0.17, 0.80],
        ], dtype=np.float32)
        target = np.array([0.02, 0.12, 0.72, 0.14], dtype=np.float32)
        expected = _hellinger_distance(values, target)
        actual = _hellinger_distance_from_roots(np.sqrt(values), np.sqrt(target))
        np.testing.assert_allclose(actual, expected, atol=1e-6)

    def test_compact_catalog_loads_only_model_columns_and_is_cached(self):
        frame = pd.DataFrame(columns=[*COLUMNS, "genre"])
        archive = Mock()
        enrichment = Mock()
        enrichment.exists.return_value = True
        _read_catalog.cache_clear()
        with (
            patch.dict("os.environ", {"CATALOG_MODE": "compact"}),
            patch("app.parse.DATA_ARCHIVE", archive),
            patch("app.parse.ENRICHMENT_FILE", enrichment),
            patch("app.parse.pd.read_csv", return_value=frame) as read_csv,
        ):
            self.assertIs(_load_catalog(), _load_catalog())
        self.assertEqual(read_csv.call_count, 1)
        self.assertIn("usecols", read_csv.call_args.kwargs)

    def test_discovery_widens_ranked_pool_but_endpoints_stay_precise(self):
        self.assertEqual(_candidate_pool_size(0, 100, False), 1)
        self.assertEqual(_candidate_pool_size(100, 100, False), 25)
        self.assertEqual(_candidate_pool_size(100, 100, True), 1)

    def test_journey_has_strong_endpoints_and_no_duplicate_titles(self):
        start = np.array(MOOD_PROFILES["peaceful"])
        end = np.array(MOOD_PROFILES["energized"])
        rows = []
        for index, progress in enumerate(np.linspace(0, 1, 24)):
            scores = start * (1 - progress) + end * progress
            name = "Same title" if index in {10, 11} else f"Track {index}"
            rows.append([
                name, False, "2020-01-01", 180000, f"id-{index}", *scores,
            ])
        frame = pd.DataFrame(rows, columns=COLUMNS)
        archive = Mock()
        archive.exists.return_value = True
        enrichment = Mock()
        enrichment.exists.return_value = False
        with (
            patch("app.parse.DATA_ARCHIVE", archive),
            patch("app.parse.ENRICHMENT_FILE", enrichment),
            patch("app.parse.pd.read_csv", return_value=frame),
        ):
            tracks = generate_mood_journey(
                JourneyOptions("peaceful", "energized", 10, discovery=0, seed=3)
            )
        self.assertEqual(len(tracks), 10)
        self.assertEqual(len({track["name"].casefold() for track in tracks}), 10)
        first = np.array(list(tracks[0]["mood_scores"].values()))
        last = np.array(list(tracks[-1]["mood_scores"].values()))
        self.assertLess(_hellinger_distance(first, start), _hellinger_distance(first, end))
        self.assertLess(_hellinger_distance(last, end), _hellinger_distance(last, start))

    def test_journey_can_exclude_tracks_already_in_a_draft(self):
        rows = []
        for index, progress in enumerate(np.linspace(0, 1, 15)):
            scores = np.array(MOOD_PROFILES["peaceful"]) * (1 - progress) + np.array(MOOD_PROFILES["energized"]) * progress
            rows.append([f"Track {index}", False, "2020-01-01", 180000, f"id-{index}", *scores])
        frame = pd.DataFrame(rows, columns=COLUMNS)
        archive = Mock()
        archive.exists.return_value = True
        enrichment = Mock()
        enrichment.exists.return_value = False
        with (
            patch("app.parse.DATA_ARCHIVE", archive),
            patch("app.parse.ENRICHMENT_FILE", enrichment),
            patch("app.parse.pd.read_csv", return_value=frame),
        ):
            tracks = generate_mood_journey(
                JourneyOptions("peaceful", "energized", 10, discovery=0),
                excluded_track_ids={"id-0", "id-1"},
            )
        self.assertFalse({"id-0", "id-1"} & {track["id"] for track in tracks})

    def test_integer_has_friendly_error(self):
        with self.assertRaisesRegex(ValueError, "whole number"):
            _integer("many", "Length")


class SpotifyWriteTests(unittest.TestCase):
    def test_uses_current_playlist_endpoints_and_batches_items(self):
        spotify = Mock()
        spotify._post.side_effect = [
            {"id": "playlist", "name": "Test", "external_urls": {}}, {}, {},
        ]
        playlist = create_playlist(
            spotify, "Test", "Description", False, [str(i) for i in range(101)]
        )
        self.assertEqual(playlist["id"], "playlist")
        self.assertEqual(spotify._post.call_args_list[0].args[0], "me/playlists")
        self.assertEqual(spotify._post.call_args_list[1].args[0], "playlists/playlist/items")
        self.assertEqual(len(spotify._post.call_args_list[1].kwargs["payload"]["uris"]), 100)
        self.assertEqual(len(spotify._post.call_args_list[2].kwargs["payload"]["uris"]), 1)

if __name__ == "__main__":
    unittest.main()
