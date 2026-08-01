import unittest
from unittest.mock import Mock

import numpy as np

from parse import JourneyOptions, _journey_progress
from playlist_service import _integer
from spotify_client import create_playlist


class JourneyTests(unittest.TestCase):
    def test_validates_mood_and_length(self):
        with self.assertRaisesRegex(ValueError, "different"):
            JourneyOptions("happy", "happy").validate()
        with self.assertRaisesRegex(ValueError, "between"):
            JourneyOptions("sad", "happy", track_count=9).validate()

    def test_smooth_curve_moves_forward(self):
        progress = _journey_progress(10, "smooth")
        self.assertTrue(np.all(np.diff(progress) > 0))
        self.assertEqual((progress[0], progress[-1]), (0, 1))

    def test_cinematic_curve_eases_at_the_ends(self):
        progress = _journey_progress(10, "cinematic")
        self.assertLess(progress[1] - progress[0], progress[5] - progress[4])

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
