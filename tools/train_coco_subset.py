"""Fine-tune the COCO-pretrained detector on the project's four COCO classes."""
from __future__ import annotations

import argparse
from pathlib import Path

from ultralytics import YOLO
from ultralytics.utils.checks import check_yaml

ROOT = Path(__file__).resolve().parents[1]
DATA = check_yaml("coco.yaml")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", default="yolov8n.pt", help="COCO-pretrained YOLOv8 checkpoint")
    parser.add_argument("--epochs", type=int, default=50)
    parser.add_argument("--imgsz", type=int, default=640)
    parser.add_argument("--device", default=None, help="Optional device, e.g. 0 or cpu")
    args = parser.parse_args()
    if args.epochs < 1 or args.imgsz < 32:
        parser.error("epochs must be positive and imgsz at least 32")

    model = YOLO(args.model)
    # COCO category IDs: bottle=39, cup=41, cell phone=67, book=73.
    # Preserve original class IDs so the model labels continue to match the backend.
    model.train(data=str(DATA), classes=[39, 41, 67, 73], epochs=args.epochs,
                imgsz=args.imgsz, device=args.device)


if __name__ == "__main__":
    main()
