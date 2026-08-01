"""Local development entry point for ``python -m app``."""

import os

from . import app


app.run(port=5001, debug=os.getenv("FLASK_DEBUG") == "1")
