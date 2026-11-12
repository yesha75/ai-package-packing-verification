"""Runtime settings for the local prototype."""
from pathlib import Path
import os
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")
DATA_DIR = Path(os.getenv("DATA_DIR", str(ROOT / "data"))).resolve()
DB_PATH = DATA_DIR / "inspections.sqlite3"
ANNOTATED_DIR = DATA_DIR / "annotated"
ORIGINAL_DIR = DATA_DIR / "originals"
CHECKLIST_PATH = Path(os.getenv("CHECKLIST_PATH", str(ROOT / "config" / "checklists.json")))
MODEL_WEIGHTS = os.getenv("MODEL_WEIGHTS", "yolov8n.pt")
PACKING_MODEL_WEIGHTS = str(
    ROOT / "runs" / "detect" / "evaluation" / "packingdata_yolo_5class" / "full_train_1ep" / "weights" / "best.pt"
)


def model_weights_for_checklist(checklist_id: str) -> str:
    """Select a detector aligned with the requested checklist classes."""
    if checklist_id == "packing_sample_878":
        if not Path(PACKING_MODEL_WEIGHTS).is_file():
            raise FileNotFoundError(
                "Packing-scene model checkpoint is unavailable. Install a compatible "
                "five-class model at runs/detect/evaluation/packingdata_yolo_5class/"
                "full_train_1ep/weights/best.pt."
            )
        return PACKING_MODEL_WEIGHTS
    return MODEL_WEIGHTS
CONFIDENCE_THRESHOLD = float(os.getenv("CONFIDENCE_THRESHOLD", "0.50"))
LOW_CONFIDENCE_THRESHOLD = float(os.getenv("LOW_CONFIDENCE_THRESHOLD", "0.25"))
OVERLAP_IOU_THRESHOLD = float(os.getenv("OVERLAP_IOU_THRESHOLD", "0.65"))
MAX_FILE_BYTES = 10 * 1024 * 1024
MAX_BATCH_SIZE = 10

if not (0 < LOW_CONFIDENCE_THRESHOLD < CONFIDENCE_THRESHOLD <= 1):
    raise ValueError("Set 0 < LOW_CONFIDENCE_THRESHOLD < CONFIDENCE_THRESHOLD <= 1")
