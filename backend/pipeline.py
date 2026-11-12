"""Run inference, verify counts, render annotated image, persist results."""
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter
from uuid import uuid4
from PIL import Image, ImageDraw
from backend import config, database
from backend.detector import get_detector
from backend.rules import verify_package
from backend.schemas import Checklist, Detection, InspectionResponse


def draw_annotated(image: Image.Image, detections: list[Detection], target: Path) -> None:
    annotated = image.copy().convert("RGB")
    draw = ImageDraw.Draw(annotated)
    for det in detections:
        color = "#1C9C60" if det.confidence >= config.CONFIDENCE_THRESHOLD else "#DF8B15"
        draw.rectangle(det.bbox, outline=color, width=3)
        x, y, _, _ = det.bbox
        label = f"{det.label} {det.confidence:.2f}"
        text_box = draw.textbbox((x, max(0, y - 17)), label)
        draw.rectangle(text_box, fill="black")
        draw.text((x, max(0, y - 17)), label, fill="white")
    target.parent.mkdir(parents=True, exist_ok=True)
    annotated.save(target, format="JPEG", quality=92)


def inspect_image(image: Image.Image, filename: str, checklist: Checklist) -> InspectionResponse:
    started = perf_counter()
    detections = get_detector(config.model_weights_for_checklist(checklist.id)).detect(image)
    verification = verify_package(detections, checklist.items)
    inspection_id = uuid4().hex
    annotated_path = config.ANNOTATED_DIR / f"{inspection_id}.jpg"
    original_path = config.ORIGINAL_DIR / f"{inspection_id}.jpg"
    original_path.parent.mkdir(parents=True, exist_ok=True)
    image.convert("RGB").save(original_path, format="JPEG", quality=95)
    draw_annotated(image, detections, annotated_path)
    record = InspectionResponse(
        **verification.model_dump(), id=inspection_id, filename=filename,
        checklist_id=checklist.id,
        created_at=datetime.now(timezone.utc).isoformat(),
        processing_ms=round((perf_counter() - started) * 1000, 2),
        detections=detections,
        annotated_image_url=f"/inspections/{inspection_id}/image",
    )
    database.save_inspection(record.model_dump(), str(annotated_path), str(original_path))
    return record
