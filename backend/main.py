"""FastAPI entry point. Run: uvicorn backend.main:app --reload"""
from contextlib import asynccontextmanager
import csv
from io import BytesIO, StringIO
from pathlib import Path
from PIL import Image, ImageOps, UnidentifiedImageError
from fastapi import FastAPI, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse, StreamingResponse
from backend import config, database
from backend.checklists import get_checklist, list_checklists
from backend.pipeline import inspect_image
from backend.schemas import Checklist, InspectionResponse

Image.MAX_IMAGE_PIXELS = 12_000_000


@asynccontextmanager
async def lifespan(_app: FastAPI):
    database.init_db()
    yield


app = FastAPI(title="Package Packing Verification API", version="0.1.0", lifespan=lifespan)


async def read_image(file: UploadFile) -> Image.Image:
    if not file.filename:
        raise HTTPException(400, "Missing filename")
    # Read up to the limit + 1 so over-limit inputs can be rejected before decoding.
    raw = await file.read(config.MAX_FILE_BYTES + 1)
    if len(raw) > config.MAX_FILE_BYTES:
        raise HTTPException(413, "Maximum image size is 10 MB")
    try:
        with Image.open(BytesIO(raw)) as check:
            if check.format not in ("JPEG", "PNG", "WEBP"):
                raise ValueError("Only JPEG, PNG and WEBP are supported")
            check.verify()
        with Image.open(BytesIO(raw)) as decoded:
            image = ImageOps.exif_transpose(decoded).convert("RGB")
            image.load()
            return image
    except (OSError, ValueError, UnidentifiedImageError, Image.DecompressionBombError) as exc:
        raise HTTPException(400, f"Invalid image: {exc}") from exc


@app.get("/health")
def health():
    models_by_checklist = {}
    for checklist in list_checklists():
        try:
            models_by_checklist[checklist.id] = Path(
                config.model_weights_for_checklist(checklist.id)
            ).name
        except FileNotFoundError:
            models_by_checklist[checklist.id] = "unavailable (checkpoint not installed)"
    return {
        "status": "ok",
        "model_weights": config.MODEL_WEIGHTS,
        "models_by_checklist": models_by_checklist,
    }


@app.get("/checklists", response_model=list[Checklist])
def checklists():
    return list_checklists()


def resolve_checklist(checklist_id: str) -> Checklist:
    checklist = get_checklist(checklist_id)
    if checklist is None:
        raise HTTPException(404, "Unknown checklist ID")
    return checklist


@app.post("/inspect", response_model=InspectionResponse)
async def inspect(file: UploadFile = File(...), checklist_id: str = Form(...)):
    checklist = resolve_checklist(checklist_id)
    try:
        config.model_weights_for_checklist(checklist.id)
    except FileNotFoundError as exc:
        raise HTTPException(503, str(exc)) from exc
    image = await read_image(file)
    return inspect_image(image, file.filename or "unnamed", checklist)


@app.post("/inspect/batch", response_model=list[InspectionResponse])
async def inspect_batch(files: list[UploadFile] = File(...), checklist_id: str = Form(...)):
    checklist = resolve_checklist(checklist_id)
    if not 1 <= len(files) <= config.MAX_BATCH_SIZE:
        raise HTTPException(400, f"Submit 1–{config.MAX_BATCH_SIZE} images per request")
    try:
        config.model_weights_for_checklist(checklist.id)
    except FileNotFoundError as exc:
        raise HTTPException(503, str(exc)) from exc
    # Validate all images before processing any, to avoid partial results from bad input.
    images = [await read_image(file) for file in files]
    return [inspect_image(image, file.filename or "unnamed", checklist)
            for image, file in zip(images, files)]


@app.get("/inspections", response_model=list[InspectionResponse])
def inspections(limit: int = Query(50, ge=1, le=500)):
    return database.list_inspections(limit)


@app.get("/summary")
def summary():
    return database.get_summary()


@app.get("/inspections/export.csv")
def export_csv():
    records = database.list_inspections(1000000)
    output = StringIO()
    fieldnames = ["id", "created_at", "filename", "checklist_id", "status", "reasons",
                  "detected_counts", "missing", "unexpected", "excess", "uncertain", "processing_ms"]
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()
    for record in records:
        writer.writerow({key: str(record.get(key, "")) for key in fieldnames})
    output.seek(0)
    return StreamingResponse(iter([output.getvalue()]), media_type="text/csv",
                             headers={"Content-Disposition": "attachment; filename=inspection_results.csv"})


@app.get("/inspections/{inspection_id}", response_model=InspectionResponse)
def inspection(inspection_id: str):
    saved = database.get_inspection(inspection_id)
    if saved is None:
        raise HTTPException(404, "Inspection not found")
    return saved[0]


@app.get("/inspections/{inspection_id}/image")
def annotated_image(inspection_id: str):
    saved = database.get_inspection(inspection_id)
    if saved is None:
        raise HTTPException(404, "Inspection not found")
    path = Path(saved[1])
    if not path.is_file():
        raise HTTPException(404, "Annotated image not found")
    return FileResponse(path, media_type="image/jpeg")


@app.get("/inspections/{inspection_id}/original")
def original_image(inspection_id: str):
    saved = database.get_inspection(inspection_id)
    if saved is None:
        raise HTTPException(404, "Inspection not found")
    path = Path(saved[2]) if saved[2] else None
    if path is None or not path.is_file():
        raise HTTPException(404, "Original image is not available for this inspection")
    return FileResponse(path, media_type="image/jpeg")
