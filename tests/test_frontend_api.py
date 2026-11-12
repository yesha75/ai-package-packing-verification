"""Tests for the Streamlit HTTP adapter, with no running server or YOLO required."""
import pytest
import requests

from frontend.api import APIError, PackageAPI, normalize_api_url
from frontend.presentation import detection_rows, item_rows, review_reason_summary, summary_stats


class FakeResponse:
    def __init__(self, payload=None, *, status_code=200, body=b"sample"):
        self.payload = {} if payload is None else payload
        self.status_code = status_code
        self.ok = 200 <= status_code < 300
        self.text = str(self.payload)
        self.content = body

    def json(self):
        return self.payload


def test_normalize_api_url():
    assert normalize_api_url(" http://127.0.0.1:8000/ ") == "http://127.0.0.1:8000"
    for invalid in ["", "file:///etc/passwd", "localhost:8000", "https://host/path", "http://example.com?token=secret", "http://u:p@host"]:
        with pytest.raises(APIError):
            normalize_api_url(invalid)


def test_get_checklists_and_summary(monkeypatch):
    calls = []
    def fake_request(method, url, **kwargs):
        calls.append((method, url, kwargs))
        if url.endswith("/checklists"):
            return FakeResponse([{"id": "demo_kit", "name": "Demo", "items": {"book": 1}}])
        return FakeResponse({"inspected": 2, "passed": 1, "needs_review": 1})
    monkeypatch.setattr(requests, "request", fake_request)
    api = PackageAPI("http://localhost:8000")
    assert api.checklists()[0]["id"] == "demo_kit"
    assert api.summary()["inspected"] == 2
    assert all(k[2]["timeout"] for k in calls)


def test_single_upload_multipart(monkeypatch):
    calls = []
    def fake_request(method, url, **kwargs):
        calls.append((method, url, kwargs))
        return FakeResponse({"status": "Pass", "id": "123"})
    monkeypatch.setattr(requests, "request", fake_request)
    result = PackageAPI("http://localhost:8000").inspect_one("images\\test.png", b"png", "demo_kit")
    assert result["status"] == "Pass"
    method, url, kwargs = calls[0]
    assert (method, url) == ("POST", "http://localhost:8000/inspect")
    assert kwargs["data"]["checklist_id"] == "demo_kit"
    assert kwargs["files"]["file"] == ("test.png", b"png", "image/png")


def test_batch_upload_multipart(monkeypatch):
    call = {}
    def fake_request(method, url, **kwargs):
        call.update(method=method, url=url, kwargs=kwargs)
        return FakeResponse([{"id": "1"}, {"id": "2"}])
    monkeypatch.setattr(requests, "request", fake_request)
    api = PackageAPI("http://localhost:8000")
    results = api.inspect_batch([("a.jpg", b"a"), ("b.png", b"b")], "demo_kit")
    assert len(results) == 2
    assert call["url"].endswith("/inspect/batch")
    assert len(call["kwargs"]["files"]) == 2
    assert all(k == "files" for k, _ in call["kwargs"]["files"])
    with pytest.raises(ValueError):
        api.inspect_batch([], "demo_kit")
    with pytest.raises(ValueError):
        api.inspect_batch([("a.jpg", b"")] * 11, "demo_kit")


def test_annotated_image_restricts_path(monkeypatch):
    urls = []
    def fake_request(method, url, **kwargs):
        urls.append(url)
        return FakeResponse(body=b"jpeg-binary")
    monkeypatch.setattr(requests, "request", fake_request)
    api = PackageAPI("http://localhost:8000")
    assert api.annotated_image("/inspections/abc/image") == b"jpeg-binary"
    assert urls == ["http://localhost:8000/inspections/abc/image"]
    for path in ["https://evil.tld/file", "//evil.tld/file", "/inspections/../image", "/other/data"]:
        with pytest.raises(APIError):
            api.annotated_image(path)


def test_http_error_human_message(monkeypatch):
    monkeypatch.setattr(requests, "request", lambda *args, **kwargs: FakeResponse({"detail": "Unknown checklist ID"}, status_code=404))
    with pytest.raises(APIError, match="Unknown checklist ID"):
        PackageAPI("http://localhost:8000").checklists()


def test_backend_unreachable(monkeypatch):
    def disconnected(*args, **kwargs):
        raise requests.ConnectionError("connection refused")
    monkeypatch.setattr(requests, "request", disconnected)
    with pytest.raises(APIError, match="Cannot contact the FastAPI backend"):
        PackageAPI("http://localhost:8000").health()


def test_presentation_helpers():
    assert item_rows({"book": 1, "cup": 2}, {"book": 1, "cup": 1, "laptop": 1}) == [
        {"Item": "Book", "Expected": 1, "Detected": 1, "Result": "Matched"},
        {"Item": "Cup", "Expected": 2, "Detected": 1, "Result": "Missing"},
        {"Item": "Laptop", "Expected": 0, "Detected": 1, "Result": "Unexpected"},
    ]
    assert detection_rows([{"label": "book", "confidence": 0.876, "bbox": [1, 2, 3, 4]}])[0]["Confidence"] == "87.6%"
    assert summary_stats({"inspected": 4, "passed": 3, "needs_review": 1})["pass_rate"] == 75
    assert summary_stats({"inspected": 0})["pass_rate"] == 0


def test_review_reason_summary():
    reasons = review_reason_summary([
        {"reasons": ["Missing required items: book x1", "Low-confidence detections require manual review: vase"]},
        {"reasons": ["Missing required items: cup x1"]},
    ])
    assert reasons[0] == ("Missing required items", 2)
