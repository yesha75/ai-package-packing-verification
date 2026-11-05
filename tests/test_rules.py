from backend.rules import verify_package, box_iou
from backend.schemas import Detection


def det(label, confidence=0.95, box=(0, 0, 20, 20)):
    return Detection(label=label, confidence=confidence, bbox=box)


def test_pass_exact_quantities():
    result = verify_package([det("bottle"), det("cup", box=(40, 40, 60, 60))],
                            {"bottle": 1, "cup": 1})
    assert result.status == "Pass"
    assert result.reasons == []


def test_missing_and_unexpected():
    result = verify_package([det("bottle"), det("book", box=(30, 30, 50, 50))],
                            {"bottle": 2})
    assert result.status == "Needs Review"
    assert result.missing == {"bottle": 1}
    assert result.unexpected == {"book": 1}


def test_low_confidence_causes_manual_review():
    result = verify_package([det("bottle"), det("cup", 0.3, (40, 40, 60, 60))],
                            {"bottle": 1})
    assert result.uncertain is True
    assert result.status == "Needs Review"


def test_excess_quantity():
    result = verify_package([det("bottle"), det("bottle", box=(40, 40, 60, 60))],
                            {"bottle": 1})
    assert result.excess == {"bottle": 1}
    assert result.status == "Needs Review"


def test_overlapping_boxes_uncertain():
    result = verify_package([det("bottle"), det("cup", box=(1, 1, 20, 20))],
                            {"bottle": 1, "cup": 1})
    assert result.uncertain is True
    assert result.status == "Needs Review"


def test_iou_empty_boxes():
    assert box_iou((0, 0, 0, 0), (0, 0, 0, 0)) == 0.0
