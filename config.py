import os

# If set to true (string 'true' case-insensitive), the app will attempt real KiteConnect calls.
KITE_ENABLE_REAL = os.environ.get("KITE_ENABLE_REAL", "false").lower() == "true"

# SQLite DB path
BASE_DIR = os.path.dirname(__file__)
DATABASE_URL = os.environ.get("DATABASE_URL") or f"sqlite:///{os.path.join(BASE_DIR, 'db.sqlite3')}"
