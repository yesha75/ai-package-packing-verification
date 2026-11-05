# AI-Based Package Packing Verification System

A decision-support prototype that inspects **static images of one package type** and compares visible objects against an expected packing checklist. It uses **YOLOv8 + FastAPI + Python verification rules + SQLite**. Designed for a future Streamlit dashboard.

> **Important:** A `Pass` means the detected objects match the checklist under the configured thresholds; it is **not proof** that a package is correct. Occluded, missed, or visually similar items can cause errors. Human inspection is still needed.

## 1. Requirements

Python **3.11** is recommended. Use a new virtual environment, not a Jetson-specific PyTorch setup. Internet access is needed on the first YOLO run to download the default `yolov8n.pt` weights.

## 2. Setup

Open a terminal **in this project folder** and run:

**Windows (PowerShell):**

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
Copy-Item .env.example .env
```

If PowerShell blocks activation, use Command Prompt and `.venv\Scripts\activate.bat`, or run `.venv\Scripts\python.exe` directly.

**macOS/Linux:**

```bash
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
cp .env.example .env
```

## 3. Start API

```bash
uvicorn backend.main:app --reload
```

Open **http://127.0.0.1:8000/docs**. In the Swagger UI:

1. `GET /checklists` – find `demo_kit`.
2. `POST /inspect` – select `demo_kit` and upload a PNG/JPEG/WEBP.
3. Review status, reasons, detected counts, boxes and annotated image URL.
4. `GET /summary`, `GET /inspections`, `GET /inspections/export.csv`.
5. `POST /inspect/batch` for 1–10 images at once.

Alternatively, upload with curl:

```bash
curl -X POST http://127.0.0.1:8000/inspect -F "checklist_id=demo_kit" -F "file=@sample_package.jpg"
```

## 4. Demo checklist and model

`config/checklists.json` expects **one bottle, one cup, one book, one cell phone**. These are object categories from COCO pretrained YOLO. You may physically stage these 4 objects in a shallow box and photograph them from above. For a useful experiment, make *correct*, *missing*, *unexpected*, *extra quantity*, *occluded*, and *low-light* images.

`MODEL_WEIGHTS=yolov8n.pt` gives a **generic baseline only**. It is **not trained specifically on packed parcels**. A pretrained model may miss objects or confuse similar classes. When you train a model for your actual 3–5 item classes, copy it to `weights/best.pt` and set `MODEL_WEIGHTS=weights/best.pt` in `.env` (run the API from project root). Keep the JSON checklist labels identical to model class names.

## 5. Explainable decision rules

- Confident detections (`>=0.50`) count toward the expected quantity for each class.
- Too few items → `Needs Review` (missing).
- Detected classes absent from checklist → `Needs Review` (unexpected).
- Too many items of a supported class → `Needs Review` (excess quantity).
- Low-confidence detections (`0.25`–`<0.50`) or high overlap IoU (`>=0.65`) → `Needs Review` for uncertainty.
- Otherwise → `Pass`.

These thresholds are configurable in `.env`; calibrate with a labeled validation set before treating them as reliable. High IoU is only a rough ambiguity indicator, **not a robust occlusion detector**. A completely invisible item cannot be recognized by a detector; the missing-item rule still flags the shortage when expected.

## 6. Test

```bash
python -m pytest -q
```

API tests replace YOLO with a fake detector, so model weights are not required for tests.

## 7. GitHub setup

Create an empty GitHub repo `ai-package-packing-verification` with no README or `.gitignore` (these files are already included). Run:

```bash
git init
git add .
git commit -m "Initial FastAPI package inspection backend"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/ai-package-packing-verification.git
git push -u origin main
```

Never commit `.env`, private sample images, collected data, or model weights without permission and applicable licenses.

## 8. Next phases

1. Capture and label example package images, with correct/missing/extra labels and bounding boxes.
2. Evaluate baseline precision, recall, mAP on held-out images, or fine-tune YOLO with a new `data.yaml`.
3. Evaluate package-level verification accuracy and false-flag rate with **manually verified** ground truth.
4. Build a Streamlit UI consuming the API (`/inspect`, `/checklists`, `/summary`, `/inspections/export.csv`).
5. Improve uncertainty checks (duplicate boxes, glare/blur, class-specific threshold calibration).

## Known prototype limits

- CPU inference may be slow; GPU acceleration is optional.
- SQLite and local image storage are suitable for a local single-user project, not hardened production.
- No login/authentication or deployment security; run locally, do not expose the API publicly.
- Package type is fixed in the initial JSON checklist, as in the proposal.
- Counts are detection counts, not verified physical inventory; overlapping items can be double counted or missed.

## Files

- `backend/detector.py`: YOLO inference and box extraction
- `backend/rules.py`: checklist comparison and uncertainty
- `backend/pipeline.py`: inference + annotation + saving
- `backend/database.py`: SQLite history and summary
- `backend/main.py`: FastAPI API endpoints and upload validation
- `backend/schemas.py`: typed payloads
- `backend/checklists.py`: editable checklists
- `tests/`: isolated unit and API tests
