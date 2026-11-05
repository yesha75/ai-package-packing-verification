"""Runtime settings for the local prototype."""
from pathlib import Path
import os
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")
DATA_DIR = Path(os.getenv("DATA_DIR", str(ROOT / "data"))).resolve()
DB_PATH = DATA_DIR / "inspections.sqlite3"
ANNOTATED_DIR = DATA_DIR / "annotated"
CHECKLIST_PATH = Path(os.getenv("CHECKLIST_PATH", str(ROOT / "config" / "checklists.json")))
MODEL_WEIGHTS = os.getenv("MODEL_WEIGHTS", "yolov8n.pt")
CONFIDENCE_THRESHOLD = float(os.getenv("CONFIDENCE_THRESHOLD", "0.50"))
LOW_CONFIDENCE_THRESHOLD = float(os.getenv("LOW_CONFIDENCE_THRESHOLD", "0.25"))
OVERLAP_IOU_THRESHOLD = float(os.getenv("OVERLAP_IOU_THRESHOLD", "0.65"))
MAX_FILE_BYTES = 10 * 1024 * 1024
MAX_BATCH_SIZE = 10

if not (0 < LOW_CONFIDENCE_THRESHOLD < CONFIDENCE_THRESHOLD <= 1):
    raise ValueError("Set 0 < LOW_CONFIDENCE_THRESHOLD < CONFIDENCE_THRESHOLD <= 1")
