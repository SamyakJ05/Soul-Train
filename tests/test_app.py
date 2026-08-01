import unittest
from unittest.mock import Mock, patch

from app import app


class RouteTests(unittest.TestCase):
    def setUp(self):
        app.config.update(TESTING=True, SECRET_KEY="test")
        self.client = app.test_client()

    @patch("app.spotify_user", return_value=None)
    def test_pages_render(self, _spotify_user):
        for path in ("/", "/about", "/aboutus", "/create/mood", "/create/library", "/stats"):
            with self.subTest(path=path):
                self.assertEqual(self.client.get(path).status_code, 200)

    @patch("app.spotify_user", return_value=None)
    def test_legacy_routes_point_to_builder(self, _spotify_user):
        response = self.client.get("/mood%20gradient")
        self.assertEqual(response.status_code, 308)
        self.assertEqual(response.headers["Location"], "/create/mood")
        response = self.client.get("/playlistinspire")
        self.assertEqual(response.headers["Location"], "/create/library")

    @patch("app.spotify_is_configured", return_value=False)
    @patch("app.spotify_user", return_value=None)
    def test_unconfigured_connect_returns_to_builder(self, _user, _configured):
        response = self.client.get("/connect")
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], "/create/mood")

    @patch("app.build_mood_playlist")
    @patch("app.connected_spotify")
    @patch("app.spotify_user", return_value={"name": "Sam", "image": None})
    def test_create_saves_result_and_redirects(self, _user, connected, build):
        connected.return_value = Mock()
        build.return_value = (
            {"id": "abc", "name": "Focus lift", "external_urls": {"spotify": "https://open.spotify.com/playlist/abc"}},
            [{"id": "one"}, {"id": "two"}],
        )
        response = self.client.post("/create", data={"mode": "mood"})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], "/success")
        with self.client.session_transaction() as saved:
            self.assertEqual(saved["last_playlist"]["track_count"], 2)

    @patch("app.spotify_user", return_value=None)
    def test_create_prompts_disconnected_user_to_connect(self, _user):
        response = self.client.post("/create", data={"mode": "library"})
        self.assertEqual(response.headers["Location"], "/connect")

    @patch("app.listening_stats")
    @patch("app.connected_spotify")
    @patch("app.spotify_user", return_value={"name": "Sam", "image": None})
    def test_stats_page_uses_selected_range(self, _user, connected, listening_stats):
        listening_stats.return_value = {
            "time_range": "short_term", "tracks": [], "artists": [],
            "top_genres": [], "unique_artists": 0, "top_track_minutes": 0,
        }
        response = self.client.get("/stats?range=short_term")
        self.assertEqual(response.status_code, 200)
        listening_stats.assert_called_once_with(connected.return_value, "short_term")


if __name__ == "__main__":
    unittest.main()
