import unittest
from unittest.mock import patch

from app import app


class RouteTests(unittest.TestCase):
    def setUp(self):
        app.config.update(TESTING=True, SECRET_KEY="test")
        self.client = app.test_client()

    def test_pages_render(self):
        for path in ("/", "/aboutus", "/discover", "/genre", "/mood-gradient", "/playlistinspire"):
            with self.subTest(path=path):
                self.assertEqual(self.client.get(path).status_code, 200)

    def test_legacy_mood_url_redirects(self):
        response = self.client.get("/mood%20gradient")
        self.assertEqual(response.status_code, 308)
        self.assertEqual(response.headers["Location"], "/mood-gradient")

    @patch("parse.make_playlist", return_value="playlist-id")
    def test_mood_form_redirects_to_created_playlist(self, make_playlist):
        response = self.client.post(
            "/mood-gradient",
            data={"mood1": "sad", "mood2": "happy", "track_count": "25"},
        )
        make_playlist.assert_called_once_with("sad", "happy", 25)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            response.headers["Location"],
            "https://open.spotify.com/playlist/playlist-id",
        )

    def test_invalid_track_count_is_reported(self):
        response = self.client.post(
            "/mood-gradient",
            data={"mood1": "sad", "mood2": "happy", "track_count": "many"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Track count must be a whole number", response.data)


if __name__ == "__main__":
    unittest.main()
