from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

from app import app
from analytics_service import analytics_summary, identify_visitor, record_event, record_visit
from draft_store import create_draft, get_draft


class RouteTests(unittest.TestCase):
    def setUp(self):
        app.config.update(TESTING=True, SECRET_KEY="test", TRACK_USAGE=False)
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary_directory.cleanup)
        app.config["DRAFT_DATABASE"] = Path(self.temporary_directory.name) / "drafts.sqlite3"
        app.config["ANALYTICS_DATABASE"] = app.config["DRAFT_DATABASE"]
        self.client = app.test_client()

    def draft(self):
        return {
            "mode": "mood",
            "name": "Focus lift",
            "description": "A test journey",
            "public": True,
            "options": {
                "start_mood": "peaceful", "end_mood": "energized",
                "track_count": 3, "curve": "smooth", "discovery": 35,
                "era": "all", "allow_explicit": False, "genre": "any",
                "seed": None,
            },
            "tracks": [
                {"id": value, "name": f"Track {value}", "artist": "Artist", "album": "Album", "image": None, "duration_ms": 180000, "explicit": False, "url": "", "release_date": "2020", "mood_scores": {}}
                for value in ("one", "two", "three")
            ],
            "pinned": [],
        }

    def save_draft_for_client(self, draft=None):
        owner_id = "test-owner"
        draft_id = create_draft(app.config["DRAFT_DATABASE"], owner_id, draft or self.draft())
        with self.client.session_transaction() as saved:
            saved["draft_owner_id"] = owner_id
            saved["playlist_draft_id"] = draft_id
        return draft_id

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

    @patch("app.prepare_mood_draft")
    @patch("app.connected_spotify")
    @patch("app.spotify_user", return_value={"name": "Sam", "image": None})
    def test_create_prepares_preview_and_redirects_to_studio(self, _user, connected, prepare):
        connected.return_value = Mock()
        prepare.return_value = self.draft()
        response = self.client.post("/create", data={"mode": "mood"})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], "/studio")
        with self.client.session_transaction() as saved:
            self.assertIn("playlist_draft_id", saved)
        studio = self.client.get("/studio")
        self.assertEqual(studio.status_code, 200)
        self.assertIn(b"Review the journey", studio.data)

    @patch("app.spotify_user", return_value=None)
    def test_create_prompts_disconnected_user_to_connect(self, _user):
        response = self.client.post(
            "/create", data={"mode": "library", "track_count": "25"}
        )
        self.assertEqual(response.headers["Location"], "/connect")
        with self.client.session_transaction() as saved:
            self.assertEqual(saved["connect_next"], "/create/resume")
            self.assertEqual(saved["pending_playlist_form"]["track_count"], "25")

    @patch("app.prepare_library_draft")
    @patch("app.connected_spotify")
    @patch("app.spotify_user", return_value={"name": "Sam", "image": None})
    def test_resumes_pending_playlist_after_connecting(self, _user, connected, prepare):
        draft = self.draft()
        draft["mode"] = "library"
        prepare.return_value = draft
        connected.return_value = Mock()
        with self.client.session_transaction() as saved:
            saved["pending_playlist_form"] = {"mode": "library", "track_count": "25"}
        response = self.client.get("/create/resume")
        self.assertEqual(response.headers["Location"], "/studio")
        prepare.assert_called_once()

    @patch("app.publish_draft")
    @patch("app.connected_spotify")
    @patch("app.spotify_user", return_value={"name": "Sam", "image": None})
    def test_publishes_reviewed_draft_and_preserves_success_flow(self, _user, connected, publish):
        draft_id = self.save_draft_for_client()
        connected.return_value = Mock()
        publish.return_value = {
            "id": "abc", "name": "Focus lift",
            "external_urls": {"spotify": "https://open.spotify.com/playlist/abc"},
        }
        response = self.client.post("/studio/publish")
        self.assertEqual(response.headers["Location"], "/success")
        with self.client.session_transaction() as saved:
            self.assertEqual(saved["last_playlist"]["track_count"], 3)
            self.assertNotIn("playlist_draft_id", saved)
        self.assertIsNone(get_draft(app.config["DRAFT_DATABASE"], draft_id, "test-owner"))

    def test_studio_can_pin_reorder_and_remove_tracks(self):
        draft_id = self.save_draft_for_client()
        self.client.post("/studio/update", data={"index": "0", "action": "pin"})
        self.client.post("/studio/update", data={"index": "0", "action": "down"})
        self.client.post("/studio/update", data={"index": "2", "action": "remove"})
        updated = get_draft(app.config["DRAFT_DATABASE"], draft_id, "test-owner")
        self.assertEqual([track["id"] for track in updated["tracks"]], ["two", "one"])
        self.assertEqual(updated["pinned"], ["one"])

    @patch("app.replace_draft_track")
    @patch("app.connected_spotify")
    @patch("app.spotify_user", return_value={"name": "Sam", "image": None})
    def test_studio_replaces_one_track_without_publishing(self, _user, connected, replace):
        draft_id = self.save_draft_for_client()
        connected.return_value = Mock()
        replacement = dict(self.draft()["tracks"][0], id="new", name="New track")
        replace.return_value = replacement
        response = self.client.post(
            "/studio/update", data={"index": "1", "action": "replace"}
        )
        self.assertEqual(response.headers["Location"], "/studio#track-2")
        updated = get_draft(app.config["DRAFT_DATABASE"], draft_id, "test-owner")
        self.assertEqual(updated["tracks"][1]["id"], "new")

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

    def test_admin_login_and_dashboard_are_private(self):
        record_visit(app.config["ANALYTICS_DATABASE"], "browser")
        identify_visitor(
            app.config["ANALYTICS_DATABASE"], "browser", "spotify-user", "Sam"
        )
        record_event(app.config["ANALYTICS_DATABASE"], "browser", "playlist_published")
        with patch.dict(
            "os.environ", {"ADMIN_PASSWORD": "correct horse", "ADMIN_PASSWORD_HASH": ""}
        ):
            denied = self.client.post("/admin/login", data={"password": "wrong"})
            self.assertEqual(denied.status_code, 200)
            response = self.client.post(
                "/admin/login", data={"password": "correct horse"}
            )
            self.assertEqual(response.headers["Location"], "/admin")
            dashboard = self.client.get("/admin")
        self.assertEqual(dashboard.status_code, 200)
        self.assertIn(b"Usage overview", dashboard.data)
        self.assertIn(b"Sam", dashboard.data)
        self.assertEqual(dashboard.headers["Cache-Control"], "no-store, private")
        self.assertEqual(dashboard.headers["X-Robots-Tag"], "noindex, nofollow")

    def test_admin_dashboard_redirects_without_login(self):
        response = self.client.get("/admin")
        self.assertEqual(response.headers["Location"], "/admin/login")

    def test_admin_login_locks_after_five_failed_attempts(self):
        with patch.dict(
            "os.environ", {"ADMIN_PASSWORD": "correct horse", "ADMIN_PASSWORD_HASH": ""}
        ):
            for _ in range(5):
                response = self.client.post(
                    "/admin/login", data={"password": "wrong"}
                )
            self.assertIn(b"locked for five minutes", response.data)
            blocked = self.client.post(
                "/admin/login", data={"password": "correct horse"}
            )
        self.assertEqual(blocked.status_code, 200)
        self.assertNotIn("/admin", blocked.headers.get("Location", ""))

    @patch("app.spotify_user", return_value=None)
    def test_public_page_views_are_counted_without_ip_data(self, _user):
        app.config["TRACK_USAGE"] = True
        try:
            self.client.get("/")
            self.client.get("/about")
        finally:
            app.config["TRACK_USAGE"] = False
        summary = analytics_summary(app.config["ANALYTICS_DATABASE"])
        self.assertEqual(summary["totals"]["unique_browsers"], 1)
        self.assertEqual(summary["totals"]["page_views"], 2)


if __name__ == "__main__":
    unittest.main()
