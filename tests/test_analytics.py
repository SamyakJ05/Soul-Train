from pathlib import Path
import tempfile
import unittest

from analytics_service import (
    VISITOR_SUMMARY_QUERY,
    analytics_summary,
    identify_visitor,
    record_event,
    record_visit,
)


class AnalyticsTests(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary_directory.cleanup)
        self.database = Path(self.temporary_directory.name) / "analytics.sqlite3"

    def test_counts_visitors_connected_users_and_product_events(self):
        record_visit(self.database, "browser-one")
        record_visit(self.database, "browser-one")
        record_visit(self.database, "browser-two")
        identify_visitor(self.database, "browser-one", "spotify-user", "Sam")
        identify_visitor(self.database, "browser-two", "spotify-user", "Sam")
        record_event(self.database, "browser-one", "draft_created")
        record_event(self.database, "browser-one", "playlist_published")
        record_event(self.database, "browser-two", "stats_viewed")

        summary = analytics_summary(self.database)

        self.assertEqual(summary["totals"]["unique_browsers"], 2)
        self.assertEqual(summary["totals"]["connected_users"], 1)
        self.assertEqual(summary["totals"]["page_views"], 3)
        self.assertEqual(summary["totals"]["drafts_created"], 1)
        self.assertEqual(summary["totals"]["playlists_published"], 1)
        self.assertEqual(len(summary["visitors"]), 1)
        self.assertEqual(summary["visitors"][0]["display_name"], "Sam")

    def test_rejects_unknown_event_names(self):
        with self.assertRaisesRegex(ValueError, "supported"):
            record_event(self.database, "browser", "unknown")

    def test_visitor_summary_uses_postgres_compatible_grouping(self):
        """The connected-user summary must satisfy PostgreSQL's strict GROUP BY."""
        normalized = " ".join(VISITOR_SUMMARY_QUERY.split())
        self.assertIn("GROUP BY spotify_id", normalized)
        self.assertIn("'browser:' || browser_id", normalized)


if __name__ == "__main__":
    unittest.main()
