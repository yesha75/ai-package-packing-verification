# Proposal requirement review

This review compares the repository with `AI_Based_Package_Packing_Verification_Proposal.pdf` in the project owner's Downloads folder. It records only implementation or evaluation evidence available in the repository and local API.

| Proposal requirement | Status | Evidence / remaining work |
|---|---|---|
| Decision-support prototype with human inspection retained | Implemented | UI warns that Pass is not a guarantee and recommends human review. |
| Static images, one package type, about 3–5 item categories | Mostly implemented | `demo_kit` has four COCO categories. `packing_sample_878` is a separate five-class dataset experiment, not a validated second production package. |
| Public/staged labeled images associated with a checklist | Partial | COCO validation and Zenodo box-scene annotations exist locally. They are object-detection datasets, not package-level expected-versus-actual labels. The Zenodo rights metadata has no license value; the dataset is excluded from Git. |
| Pretrained YOLO first; optional fine-tuning | Implemented | `demo_kit` uses `yolov8n.pt`; a locally available fine-tuned checkpoint serves the packing-scene experiment. The checkpoint is excluded from Git. |
| Configurable confidence filtering and checklist comparison | Implemented | Confidence thresholds are in `.env`; rules cover missing, unexpected, excess, low-confidence, and overlap cases. |
| Streamlit single/batch upload, annotations, status/reasons, summary, CSV export | Implemented | Present in `frontend/app.py` and FastAPI endpoints. API tests cover single and batch flows. |
| Object detection evaluation on held-out labels: precision, recall, mAP | Partial | COCO four-class baseline is measured. The five-class Zenodo test split is measured, but it informed development and is not an untouched final benchmark. These are detection metrics, not package accuracy. |
| Package accuracy and false-flag rate using manually reviewed labels | Pending | The existing ground-truth CSV has 12 rows, but actual quantities, unexpected items, correctness labels, and verifier names are blank. The referenced image files are absent. The local API has all 12 inspection records, but each original-image endpoint returns 404. |
| Processing time per image | Implemented, package summary pending | Each inspection stores `processing_ms`; a labeled package-level evaluation is not possible until the missing labels are restored. |
| Test on unseen images and prepare a demonstration | Partial | Sample 878 passed a live functionality check, but it was used during development. A fresh independent package set is not available. |

## Ground-truth preflight

The 12 template entries are not ground truth yet. Their `actual_*`, `actual_unexpected_classes`, `package_correct_actual`, and `verified_by` cells are empty. None of the listed image filenames exists under `evaluation/`, and the original uploads for the recorded inspection IDs are unavailable from the local API. Do not treat expected quantities, predictions, or the sample 878 checklist as actual labels.

Run `python tools/evaluate_packages.py --preflight` after restoring images and completing manual labels. To calculate package-level accuracy, false-pass rate, false-flag rate, and mean processing time, save the API's `GET /inspections/export.csv` as `evaluation/results/inspection_results.csv`, then run `python tools/evaluate_packages.py`. The evaluator stops without writing scores when labels or matching inspection records are incomplete.

## Submission notes

- The repository does not contain a course title or identifying class name; object-category labels are necessary application data.
- A clean clone can run `demo_kit` after installing dependencies and downloading the default YOLO weights. `packing_sample_878` requires a compatible checkpoint that is intentionally not included; the API reports it as unavailable instead of silently using the wrong detector.
- Dataset images, local model weights, inspection database, and training runs are excluded from Git.
