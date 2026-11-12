import csv

import pytest

from tools.evaluate_packages import evaluate


def truth_row(inspection_id, actual_count, correct):
    return {
        "inspection_id": inspection_id,
        "image_filename": f"{inspection_id}.jpg",
        "checklist_id": "demo_kit",
        "expected_bottle": "1",
        "actual_bottle": str(actual_count),
        "actual_unexpected_classes": "none",
        "package_correct_actual": str(correct).lower(),
        "verified_by": "reviewer-1",
    }


def write_csv(path, fields, rows):
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def test_evaluation_reports_decision_rates_and_processing_time(tmp_path):
    truth = tmp_path / "truth.csv"
    predictions = tmp_path / "predictions.csv"
    report = tmp_path / "report.md"
    truth_rows = [
        truth_row("a", 1, True),
        truth_row("b", 0, False),
        truth_row("c", 1, True),
        truth_row("d", 0, False),
    ]
    prediction_rows = [
        {"id": "a", "filename": "a.jpg", "checklist_id": "demo_kit", "status": "Pass", "processing_ms": "10"},
        {"id": "b", "filename": "b.jpg", "checklist_id": "demo_kit", "status": "Pass", "processing_ms": "20"},
        {"id": "c", "filename": "c.jpg", "checklist_id": "demo_kit", "status": "Needs Review", "processing_ms": "30"},
        {"id": "d", "filename": "d.jpg", "checklist_id": "demo_kit", "status": "Needs Review", "processing_ms": "40"},
    ]
    write_csv(truth, list(truth_rows[0]), truth_rows)
    write_csv(predictions, list(prediction_rows[0]), prediction_rows)

    evaluate(truth, predictions, report)

    output = report.read_text(encoding="utf-8")
    assert "Package decision accuracy | 50.0%" in output
    assert "False-pass rate (incorrect packages predicted Pass) | 50.0%" in output
    assert "False-flag rate (correct packages predicted Needs Review) | 50.0%" in output
    assert "Mean processing time | 25.00 ms" in output


def test_evaluation_refuses_truth_that_conflicts_with_manual_counts(tmp_path):
    truth = tmp_path / "truth.csv"
    predictions = tmp_path / "predictions.csv"
    report = tmp_path / "report.md"
    row = truth_row("a", 0, True)
    write_csv(truth, list(row), [row])
    write_csv(predictions, ["id"], [{"id": "a"}])

    with pytest.raises(ValueError, match="conflicts with the expected/actual counts"):
        evaluate(truth, predictions, report)

    assert not report.exists()
