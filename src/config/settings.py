from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]
SRC_DIR = BASE_DIR / "src"
QUERIES_DIR = SRC_DIR / "queries"
ASSETS_DIR = BASE_DIR / "assets"
DATA_DIR = BASE_DIR / "data"

DEFAULT_YEAR = 2025
DEFAULT_CLIENT_WINDOW = 15
