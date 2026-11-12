"""Pure formatters for the Streamlit dashboard (also unit-testable)."""
from __future__ import annotations

from collections import Counter
from datetime import datetime


def item_rows(expected: dict[str, int], detected: dict[str, int]) -> list[dict]:
    output = []
    for label in sorted(set(expected) | set(detected)):
        exp = int(expected.get(label, 0))
        obs = int(detected.get(label, 0))
        if exp == 0:
            status = "Unexpected"
        elif obs < exp:
            status = "Missing"
        elif obs > exp:
            status = "Excess"
        else:
            status = "Matched"
        output.append({"Item": label.title(), "Expected": exp, "Detected": obs, "Result": status})
    return output


def detection_rows(detections: list[dict], confident_threshold: float = 0.5) -> list[dict]:
    rows = []
    for det in detections:
        confidence = float(det.get("confidence", 0))
        bbox = det.get("bbox", [])
        rows.append({
            "Object": det.get("label", "Unknown"),
            "Confidence": f"{confidence:.1%}",
            "Threshold": "Counted" if confidence >= confident_threshold else "Review only",
            "Box [x1, y1, x2, y2]": str(bbox),
        })
    return rows


def summary_stats(summary: dict) -> dict:
    inspected = int(summary.get("inspected", 0))
    passed = int(summary.get("passed", 0))
    review = int(summary.get("needs_review", 0))
    return {"inspected": inspected, "passed": passed, "needs_review": review,
            "pass_rate": 100 * passed / inspected if inspected else 0.0}


def review_reason_summary(records: list[dict], count: int = 5) -> list[tuple[str, int]]:
    tally = Counter()
    for r in records:
        for reason in r.get("reasons", []):
            head = str(reason).split(":", 1)[0].strip()
            tally[head] += 1
    return tally.most_common(count)


def display_timestamp(value: str) -> str:
    try:
        stamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return stamp.strftime("%Y-%m-%d %H:%M UTC")
    except (TypeError, ValueError, AttributeError):
        return value or "Unknown"
