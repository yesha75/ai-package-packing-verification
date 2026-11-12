"""Evaluate package decisions against manually verified ground truth.

The tool refuses to calculate metrics while labels are incomplete or inconsistent.
It consumes the editable ground-truth template and the API's inspection CSV export.
"""
from __future__ import annotations

import argparse
import csv
import math
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TRUTH = ROOT / "evaluation" / "ground_truth_template.csv"
DEFAULT_PREDICTIONS = ROOT / "evaluation" / "results" / "inspection_results.csv"
DEFAULT_REPORT = ROOT / "evaluation" / "results" / "package_evaluation.md"


def read_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames:
            raise ValueError(f"CSV has no header: {path}")
        return reader.fieldnames, list(reader)


def parse_count(value: str, field: str) -> int:
    try:
        count = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field} must be a non-negative integer, got {value!r}") from exc
    if count < 0:
        raise ValueError(f"{field} must be a non-negative integer, got {value!r}")
    return count


def parse_truth(value: str, field: str) -> bool:
    normalized = (value or "").strip().lower()
    if normalized in {"true", "yes", "1", "pass", "correct"}:
        return True
    if normalized in {"false", "no", "0", "needs review", "incorrect"}:
        return False
    raise ValueError(f"{field} must be an explicit true/false value, got {value!r}")


def has_unexpected(value: str) -> bool:
    return (value or "").strip().lower() not in {"", "none", "n/a", "[]", "null"}


def label_row(row: dict[str, str], expected_fields: list[str]) -> bool:
    """Validate one manually labeled row and return its independently recorded truth."""
    inspection_id = (row.get("inspection_id") or "").strip() or "<missing inspection_id>"
    if not (row.get("image_filename") or "").strip():
        raise ValueError(f"inspection {inspection_id}: image_filename is blank")
    if not (row.get("checklist_id") or "").strip():
        raise ValueError(f"inspection {inspection_id}: checklist_id is blank")
    values: dict[str, int] = {}
    for expected_field in expected_fields:
        item = expected_field.removeprefix("expected_")
        actual_field = f"actual_{item}"
        values[item] = parse_count(row[expected_field], expected_field)
        if not (row.get(actual_field) or "").strip():
            raise ValueError(f"inspection {inspection_id}: {actual_field} is blank")
        actual_count = parse_count(row[actual_field], actual_field)
        values[f"__actual_{item}"] = actual_count

    if not (row.get("verified_by") or "").strip():
        raise ValueError(f"inspection {inspection_id}: verified_by is blank")
    if not (row.get("actual_unexpected_classes") or "").strip():
        raise ValueError(f"inspection {inspection_id}: actual_unexpected_classes is blank; enter 'none' if none")
    if not (row.get("package_correct_actual") or "").strip():
        raise ValueError(f"inspection {inspection_id}: package_correct_actual is blank")

    unexpected = has_unexpected(row.get("actual_unexpected_classes", ""))
    derived_correct = all(
        values[item] == values[f"__actual_{item}"] for item in values if not item.startswith("__")
    ) and not unexpected
    recorded_correct = parse_truth(row["package_correct_actual"], "package_correct_actual")
    if recorded_correct != derived_correct:
        raise ValueError(
            f"inspection {inspection_id}: package_correct_actual conflicts with the "
            "expected/actual counts or unexpected-class field"
        )
    return recorded_correct


def preflight(truth_path: Path, image_root: Path) -> int:
    headers, rows = read_csv(truth_path)
    expected_fields = [field for field in headers if field.startswith("expected_")]
    required = {"inspection_id", "image_filename", "verified_by", "package_correct_actual",
                "actual_unexpected_classes"}
    missing_columns = sorted(required - set(headers))
    if not expected_fields:
        missing_columns.append("expected_<item> columns")
    if missing_columns:
        raise ValueError("Ground-truth CSV missing required columns: " + ", ".join(missing_columns))

    incomplete: list[str] = []
    missing_images: list[str] = []
    for index, row in enumerate(rows, start=2):
        identity = (row.get("inspection_id") or "").strip() or f"CSV row {index}"
        missing = []
        for expected_field in expected_fields:
            item = expected_field.removeprefix("expected_")
            if not (row.get(expected_field) or "").strip():
                missing.append(expected_field)
            if not (row.get(f"actual_{item}") or "").strip():
                missing.append(f"actual_{item}")
        for field in ("actual_unexpected_classes", "package_correct_actual", "verified_by"):
            if not (row.get(field) or "").strip():
                missing.append(field)
        if missing:
            incomplete.append(f"{identity}: {', '.join(missing)}")
        filename = (row.get("image_filename") or "").strip()
        if not filename or not (image_root / filename).is_file():
            missing_images.append(f"{identity}: {filename or '<blank filename>'}")

    print(f"Ground-truth rows: {len(rows)}")
    print(f"Rows with complete manual labels: {len(rows) - len(incomplete)}")
    print(f"Rows with missing image files: {len(missing_images)}")
    if incomplete:
        print("Incomplete labels:")
        for line in incomplete:
            print(f"  - {line}")
    if missing_images:
        print("Missing image files:")
        for line in missing_images:
            print(f"  - {line}")
    return 1 if incomplete or missing_images else 0


def evaluate(truth_path: Path, predictions_path: Path, report_path: Path) -> None:
    truth_headers, truth_rows = read_csv(truth_path)
    expected_fields = [field for field in truth_headers if field.startswith("expected_")]
    if not expected_fields:
        raise ValueError("Ground-truth CSV needs expected_<item> columns")
    pred_headers, pred_rows = read_csv(predictions_path)
    if "id" not in pred_headers:
        raise ValueError("Inspection export needs an id column")
    predictions = {row["id"].strip(): row for row in pred_rows if row.get("id", "").strip()}

    labeled: list[tuple[bool, bool, float]] = []
    errors: list[str] = []
    for row in truth_rows:
        inspection_id = (row.get("inspection_id") or "").strip()
        try:
            actual_pass = label_row(row, expected_fields)
            if not inspection_id:
                raise ValueError("inspection_id is blank")
            prediction = predictions.get(inspection_id)
            if prediction is None:
                raise ValueError(f"inspection {inspection_id}: no matching API export row")
            if prediction.get("checklist_id", "") != row.get("checklist_id", ""):
                raise ValueError(f"inspection {inspection_id}: checklist_id mismatch")
            if prediction.get("filename", "") != row.get("image_filename", ""):
                raise ValueError(f"inspection {inspection_id}: filename mismatch")
            status = prediction.get("status", "")
            if status not in {"Pass", "Needs Review"}:
                raise ValueError(f"inspection {inspection_id}: unknown prediction status {status!r}")
            duration = float(prediction["processing_ms"])
            if not math.isfinite(duration) or duration < 0:
                raise ValueError(f"inspection {inspection_id}: invalid processing_ms")
            labeled.append((actual_pass, status == "Pass", duration))
        except (ValueError, KeyError) as exc:
            errors.append(str(exc))

    if errors:
        raise ValueError("Evaluation stopped; no metrics written:\n- " + "\n- ".join(errors))
    if not labeled:
        raise ValueError("No complete labeled inspections found")

    true_pass = sum(actual and predicted for actual, predicted, _ in labeled)
    false_pass = sum((not actual) and predicted for actual, predicted, _ in labeled)
    false_flag = sum(actual and (not predicted) for actual, predicted, _ in labeled)
    true_review = sum((not actual) and (not predicted) for actual, predicted, _ in labeled)
    n = len(labeled)
    accuracy = (true_pass + true_review) / n
    false_pass_rate = false_pass / (false_pass + true_review) if false_pass + true_review else None
    false_flag_rate = false_flag / (true_pass + false_flag) if true_pass + false_flag else None
    average_ms = sum(duration for _, _, duration in labeled) / n

    def percent(value: float | None) -> str:
        return "not defined (no examples in denominator)" if value is None else f"{value:.1%}"

    report = [
        "# Package-level evaluation",
        "",
        f"Evaluated {n} manually labeled inspections from `{truth_path.name}` joined to `{predictions_path.name}` by inspection ID.",
        "",
        "| Metric | Result |",
        "|---|---:|",
        f"| Package decision accuracy | {accuracy:.1%} |",
        f"| False-pass rate (incorrect packages predicted Pass) | {percent(false_pass_rate)} |",
        f"| False-flag rate (correct packages predicted Needs Review) | {percent(false_flag_rate)} |",
        f"| Mean processing time | {average_ms:.2f} ms |",
        "",
        "| Confusion count | Count |",
        "|---|---:|",
        f"| Correct package predicted Pass | {true_pass} |",
        f"| Incorrect package predicted Pass | {false_pass} |",
        f"| Correct package predicted Needs Review | {false_flag} |",
        f"| Incorrect package predicted Needs Review | {true_review} |",
        "",
        "This report measures package decisions only. It does not calculate bounding-box precision, recall, or mAP; use an independently labeled YOLO-format box dataset for those metrics.",
        "",
    ]
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(report), encoding="utf-8")
    print("\n".join(report))
    print(f"\nSaved: {report_path}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ground-truth", type=Path, default=DEFAULT_TRUTH)
    parser.add_argument("--inspections", type=Path, default=DEFAULT_PREDICTIONS,
                        help="CSV downloaded from GET /inspections/export.csv")
    parser.add_argument("--output", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--image-root", type=Path, default=ROOT / "evaluation",
                        help="Directory used to check the image_filename values")
    parser.add_argument("--preflight", action="store_true",
                        help="List incomplete labels and missing images without calculating metrics")
    args = parser.parse_args()
    try:
        if args.preflight:
            return preflight(args.ground_truth, args.image_root)
        evaluate(args.ground_truth, args.inspections, args.output)
    except (OSError, ValueError) as exc:
        parser.exit(2, f"error: {exc}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
