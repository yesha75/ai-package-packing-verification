"""Conservative, explainable package-level verification logic."""
from collections import Counter
from backend import config
from backend.schemas import Detection, VerificationResult


def box_iou(a: tuple[int, int, int, int], b: tuple[int, int, int, int]) -> float:
    x1, y1 = max(a[0], b[0]), max(a[1], b[1])
    x2, y2 = min(a[2], b[2]), min(a[3], b[3])
    intersection = max(0, x2 - x1) * max(0, y2 - y1)
    area_a = max(0, a[2] - a[0]) * max(0, a[3] - a[1])
    area_b = max(0, b[2] - b[0]) * max(0, b[3] - b[1])
    union = area_a + area_b - intersection
    return intersection / union if union else 0.0


def verify_package(
    detections: list[Detection],
    expected: dict[str, int],
    confidence_threshold: float = config.CONFIDENCE_THRESHOLD,
    low_confidence_threshold: float = config.LOW_CONFIDENCE_THRESHOLD,
    overlap_iou_threshold: float = config.OVERLAP_IOU_THRESHOLD,
) -> VerificationResult:
    confident = [d for d in detections if d.confidence >= confidence_threshold]
    low_confidence = [d for d in detections
                      if low_confidence_threshold <= d.confidence < confidence_threshold]
    counts = Counter(d.label for d in confident)
    missing = {label: quantity - counts[label] for label, quantity in expected.items()
               if counts[label] < quantity}
    unexpected = {label: quantity for label, quantity in counts.items()
                  if label not in expected}
    excess = {label: counts[label] - quantity for label, quantity in expected.items()
              if counts[label] > quantity}
    # Significant box overlap is a proxy for ambiguity, not proof of true occlusion.
    overlaps = any(box_iou(a.bbox, b.bbox) >= overlap_iou_threshold
                   for i, a in enumerate(confident) for b in confident[i + 1:])
    uncertain = bool(low_confidence) or overlaps
    reasons = []
    if missing:
        reasons.append("Missing required items: " + ", ".join(f"{k} x{v}" for k, v in missing.items()))
    if unexpected:
        reasons.append("Unexpected item classes: " + ", ".join(f"{k} x{v}" for k, v in unexpected.items()))
    if excess:
        reasons.append("Excess item quantities: " + ", ".join(f"{k} +{v}" for k, v in excess.items()))
    if low_confidence:
        names = ", ".join(sorted(set(d.label for d in low_confidence)))
        reasons.append(f"Low-confidence detections require manual review: {names}")
    if overlaps:
        reasons.append("High bounding-box overlap; possible ambiguity or occlusion")
    return VerificationResult(
        status="Needs Review" if reasons else "Pass",
        reasons=reasons,
        detected_counts=dict(counts),
        missing=missing, unexpected=unexpected, excess=excess,
        uncertain=uncertain,
    )
