# Packing-scene detector evaluation

## Dataset and training

Zenodo `packingdata` (DOI 10.5281/zenodo.7904630), filtered to can, cup, plate, bowl, and apple. The publisher split was preserved: 952 training images and 239 held-out test images (1,167 selected-class instances). The final checkpoint completed one epoch over all 952 training images. Earlier pilot checkpoints are retained for comparison.

## Held-out results

| Model | Precision | Recall | mAP@0.5 | mAP@0.5:0.95 |
|---|---:|---:|---:|---:|
| 3-epoch pilot, 10% training data | 0.954 | 0.766 | 0.828 | 0.704 |
| Expanded, 1 completed epoch, 50% training data | 0.833 | 0.921 | 0.845 | 0.758 |
| Full-split fine-tune, 1 epoch, 100% training data | 0.960 | 0.980 | 0.961 | 0.834 |

Full-split model by class: can P=0.994 R=0.950 mAP50=0.970; cup P=0.973 R=0.972 mAP50=0.986; plate P=0.987 R=1.000 mAP50=0.995; bowl P=0.848 R=1.000 mAP50=0.877; apple P=0.998 R=0.977 mAP50=0.975. Bowl precision is the weakest class and warrants review of false positives.

The live FastAPI endpoint was checked with sample image 878 and `packing_sample_878`: it returned `Pass` with can x1, cup x2, apple x1, bowl x1. This sample is part of the held-out set and was used for debugging, so neither this sample result nor the test metrics are a pristine independent final evaluation.

## Limits

This measures object detection on annotated box scenes, not package-level correctness. The dataset has no expected checklist/correctness labels, so package accuracy, false-pass and false-flag rates cannot be calculated. The full-split checkpoint is used only for checklist `packing_sample_878`; the app's `demo_kit` still uses COCO-pretrained YOLOv8n. The held-out test set informed iteration and is not a pristine final benchmark. A fresh independent test set and manually verified package-level labels are needed for final claims.
