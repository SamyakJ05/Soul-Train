import unittest

from parse import make_playlist
from unsupervised import _track_windows


class PlaylistTests(unittest.TestCase):
    def test_rejects_unknown_mood_before_loading_data(self):
        with self.assertRaisesRegex(ValueError, "valid"):
            make_playlist("calm", "happy")

    def test_rejects_identical_moods(self):
        with self.assertRaisesRegex(ValueError, "different"):
            make_playlist("happy", "happy")

    def test_rejects_invalid_track_count(self):
        with self.assertRaisesRegex(ValueError, "between"):
            make_playlist("sad", "happy", 101)

    def test_track_windows_respect_spotify_limit(self):
        windows = list(_track_windows(list(range(205))))
        self.assertEqual([len(window) for window in windows], [100, 100, 5])


if __name__ == "__main__":
    unittest.main()
