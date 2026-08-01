"""Admin password verification helpers."""

import hmac
import os

from werkzeug.security import check_password_hash


def admin_password_configured() -> bool:
    return bool(os.getenv("ADMIN_PASSWORD_HASH") or os.getenv("ADMIN_PASSWORD"))


def verify_admin_password(candidate: str) -> bool:
    configured_hash = os.getenv("ADMIN_PASSWORD_HASH", "").strip()
    if configured_hash:
        try:
            return check_password_hash(configured_hash, candidate)
        except (TypeError, ValueError):
            return False
    configured_password = os.getenv("ADMIN_PASSWORD", "")
    return bool(configured_password) and hmac.compare_digest(configured_password, candidate)
