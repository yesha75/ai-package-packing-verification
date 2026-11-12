# COCO 2017 baseline evaluation

## Scope

Pretrained Ultralytics YOLOv8n (`yolov8n.pt`) evaluated on the COCO 2017 validation split for the four checklist classes: bottle, cup, cell phone, and book. This is a general object-detection benchmark result, **not package-verification accuracy**. No package-specific accuracy, false-pass, or false-flag result is inferred from it.

## Measured aggregate results

| Metric | Result |
|---|---:|
| Precision | 38.3% |
| Recall | 26.2% |
| mAP@0.5 | 24.4% |
| mAP@0.5:0.95 | 15.4% |

These values were returned by Ultralytics validation on the 5,000-image COCO 2017 validation split, filtering evaluation to COCO class IDs 39, 41, 67, and 73.

## Status and next work

- Pretrained detector integration, backend, frontend, and checklist rules: implemented.
- COCO baseline: measured and complete.
- Original staged-package images and manually verified ground truth: pending.
- Package-level accuracy, false-pass/false-flag rates, package-image mAP, and package-image processing time: pending until a held-out labeled package set exists.
- Fine-tuning: defer until package-image evaluation supports it; keep evaluation images separate from training data.

Do not describe 24.4% mAP@0.5 as package accuracy. Model-generated detections are not ground-truth annotations.
