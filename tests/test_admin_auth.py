import os
import unittest
from unittest.mock import patch

from werkzeug.security import generate_password_hash

from admin_auth import admin_password_configured, verify_admin_password


class AdminAuthTests(unittest.TestCase):
    def test_prefers_secure_password_hash(self):
        password_hash = generate_password_hash("correct horse")
        with patch.dict(
            os.environ,
            {"ADMIN_PASSWORD_HASH": password_hash, "ADMIN_PASSWORD": "fallback"},
        ):
            self.assertTrue(admin_password_configured())
            self.assertTrue(verify_admin_password("correct horse"))
            self.assertFalse(verify_admin_password("fallback"))

    def test_supports_plain_environment_password_as_fallback(self):
        with patch.dict(
            os.environ, {"ADMIN_PASSWORD_HASH": "", "ADMIN_PASSWORD": "local-only"}
        ):
            self.assertTrue(verify_admin_password("local-only"))
            self.assertFalse(verify_admin_password("wrong"))


if __name__ == "__main__":
    unittest.main()
