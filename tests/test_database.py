import unittest

from database import _postgres_placeholders, is_postgres


class DatabaseCompatibilityTests(unittest.TestCase):
    def test_recognizes_neon_postgres_urls(self):
        self.assertTrue(is_postgres("postgresql://user@example.neon.tech/app"))
        self.assertTrue(is_postgres("postgres://user@example.neon.tech/app"))
        self.assertFalse(is_postgres("instance/app.sqlite3"))

    def test_converts_qmark_placeholders_for_psycopg(self):
        self.assertEqual(
            _postgres_placeholders("SELECT * FROM visitors WHERE browser_id = ?"),
            "SELECT * FROM visitors WHERE browser_id = %s",
        )


if __name__ == "__main__":
    unittest.main()
