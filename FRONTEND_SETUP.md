# Streamlit frontend setup — Windows / PowerShell

This frontend works with the existing **FastAPI + YOLOv8** backend in this repository. It does not require a separate model or database. The dashboard calls the API running on port 8000.

## What is included

- Single-image and batch uploads (up to 10 images, 10 MB each)
- Dynamic checklist selection from `GET /checklists`
- Original and annotated image comparison
- Pass / Needs Review results and reasons
- Item-by-item expected versus detected counts
- Raw YOLO labels, confidences, and bounding boxes
- Saved inspection history, searchable and filterable
- Summary statistics, chart of statuses, inspection trend, review reasons
- Download annotated images and all records as CSV
- Friendly errors when FastAPI is not running

## 1. Open the project folder in VS Code

For example:

```powershell
cd C:\Users\yesha\Downloads\ai-package-packing-verification
```

Make sure `backend/`, `frontend/`, `requirements.txt`, and `requirements-frontend.txt` are all in this same project folder.

## 2. Activate your existing environment

In PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

If your virtual environment is named `env` instead of `.venv`, run ` .\env\Scripts\Activate.ps1 `.

## 3. Install the additional frontend dependencies

```powershell
pip install -r requirements-frontend.txt
```

If backend dependencies are not already installed:

```powershell
pip install -r requirements.txt
```

## 4. Start backend — TERMINAL 1

Keep this terminal open:

```powershell
uvicorn backend.main:app --reload
```

Verify `http://127.0.0.1:8000/health` and `http://127.0.0.1:8000/docs` work.

## 5. Start frontend — TERMINAL 2

Open **another terminal** in the same project root, activate the same environment, and run:

```powershell
python -m streamlit run frontend/app.py
```

Your browser should open **http://localhost:8501**.

The sidebar should say **Connected to FastAPI**. If not, confirm both programs are running and that the FastAPI URL is `http://127.0.0.1:8000`.

## 6. Demonstrate the project

1. Select the checklist `demo_kit` (bottle, cup, book, cell phone; 1 of each).
2. Upload a staged package photo with visible objects.
3. Click **Run AI inspection**; the first inference can be slow if model weights are being downloaded.
4. Compare the original and annotated images.
5. Read the classification, confidence scores, expected/detected counts, and reasons for review.
6. Try **Batch images** and upload 2–3 photos.
7. Open **Inspection history** to view saved results.
8. Open **Analytics & export**, prepare the CSV, and download it.

If the model confuses a book with a laptop or a bottle with a vase, this is a **model limitation**, not a frontend bug. The system should flag such results for review rather than forcing a Pass.

## 7. Push files to your GitHub repo

```powershell
git status
git add frontend requirements-frontend.txt FRONTEND_SETUP.md .streamlit tests/test_frontend_api.py README.md
git commit -m "Add Streamlit package inspection dashboard"
git push origin main
```

If Git says the files have not changed or your branch has another name, inspect `git status` / `git branch` before retrying.

## Run tests

```powershell
python -m pytest -q
```

The new frontend HTTP adapter tests are isolated and require no YOLO downloads.

## Design and local-development notes

- This is a local academic prototype, **not a publicly secured production app**. Run the API locally; do not expose a public unauthenticated inspection service.
- Data are saved in the backend SQLite database and annotated images in `data/annotated`. The frontend displays them using the API.
- Saved history is capped to the most recent 100 records in this dashboard. Overall counters and CSV export include all saved inspections.
- The default API base URL is `http://127.0.0.1:8000`; you can edit it in the sidebar, or set the `API_BASE_URL` environment variable.
- Streamlit `.streamlit/config.toml` sets upload limits and a light visual theme.
- A Pass indicates the model's counted predictions match the checklist; it **does not guarantee** that a physical order is correct.
