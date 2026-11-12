"""YOLO adapter. Keep model initialization lazy so API tests need no downloaded weights."""
from functools import lru_cache
import numpy as np
from PIL import Image
from backend import config
from backend.schemas import Detection


class YOLODetector:
    def __init__(self, weights: str):
        from ultralytics import YOLO
        self.model = YOLO(weights)  # downloads yolov8n.pt on first run if needed

    def detect(self, image: Image.Image) -> list[Detection]:
        # Ultralytics expects OpenCV-style BGR when given a numpy image.
        bgr = np.asarray(image.convert("RGB"))[:, :, ::-1].copy()
        result = self.model.predict(
            source=bgr, conf=config.LOW_CONFIDENCE_THRESHOLD, verbose=False
        )[0]
        detections = []
        if result.boxes is None:
            return detections
        for box in result.boxes:
            cls_id = int(box.cls.item())
            detections.append(Detection(
                label=str(result.names[cls_id]),
                confidence=round(float(box.conf.item()), 4),
                bbox=tuple(int(round(n)) for n in box.xyxy[0].tolist()),
            ))
        return detections


@lru_cache(maxsize=2)
def get_detector(weights: str | None = None) -> YOLODetector:
    return YOLODetector(weights or config.MODEL_WEIGHTS)
