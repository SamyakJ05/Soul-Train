from pathlib import Path
import tempfile
import unittest

from draft_store import create_draft, delete_draft, get_draft, save_draft


class DraftStoreTests(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary_directory.cleanup)
        self.database = Path(self.temporary_directory.name) / "drafts.sqlite3"

    def test_draft_is_scoped_to_owner_and_can_be_updated(self):
        draft_id = create_draft(self.database, "owner-a", {"name": "First"})
        self.assertIsNone(get_draft(self.database, draft_id, "owner-b"))
        self.assertTrue(save_draft(self.database, draft_id, "owner-a", {"name": "Updated"}))
        self.assertEqual(get_draft(self.database, draft_id, "owner-a")["name"], "Updated")

    def test_delete_only_removes_the_owners_draft(self):
        draft_id = create_draft(self.database, "owner-a", {"name": "First"})
        delete_draft(self.database, draft_id, "owner-b")
        self.assertIsNotNone(get_draft(self.database, draft_id, "owner-a"))
        delete_draft(self.database, draft_id, "owner-a")
        self.assertIsNone(get_draft(self.database, draft_id, "owner-a"))


if __name__ == "__main__":
    unittest.main()
