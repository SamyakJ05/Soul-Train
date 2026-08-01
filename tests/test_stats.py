import unittest
from unittest.mock import Mock

from app.stats_service import listening_stats


class StatsTests(unittest.TestCase):
    def test_summarizes_top_items(self):
        spotify = Mock()
        spotify.current_user_top_tracks.return_value = {"items": [{
            "name": "Track", "duration_ms": 180000,
            "artists": [{"name": "Artist"}], "album": {"images": []},
            "external_urls": {"spotify": "https://example.test/track"},
        }]}
        spotify.current_user_top_artists.return_value = {"items": [{
            "name": "Artist", "genres": ["indie", "dream pop"], "images": [],
            "external_urls": {"spotify": "https://example.test/artist"},
        }]}
        spotify.current_user_recently_played.return_value = {"items": [
            {"played_at": "2026-07-30T10:00:00Z", "track": {"duration_ms": 180000}},
            {"played_at": "2026-08-01T10:00:00Z", "track": {"duration_ms": 240000}},
        ]}
        result = listening_stats(spotify, "short_term")
        self.assertEqual(result["tracks"][0]["name"], "Track")
        self.assertEqual(result["top_genres"][0], ("indie", 1))
        self.assertEqual(result["unique_artists"], 1)
        self.assertEqual(result["top_track_minutes"], 3)
        self.assertEqual(result["recent_minutes"], 7)
        self.assertEqual(result["recent_plays"], 2)
        self.assertEqual(result["recent_window"], "Jul 30 – Aug 1")

    def test_invalid_range_falls_back_to_six_months(self):
        spotify = Mock()
        spotify.current_user_top_tracks.return_value = {"items": []}
        spotify.current_user_top_artists.return_value = {"items": []}
        spotify.current_user_recently_played.return_value = {"items": []}
        result = listening_stats(spotify, "forever")
        self.assertEqual(result["time_range"], "medium_term")


if __name__ == "__main__":
    unittest.main()
