from pathlib import Path

# config.py lives in app/, so go up one more level to the project root.
DATA_DIR = Path(__file__).resolve().parent.parent / "data"
